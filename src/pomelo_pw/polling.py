"""Polling progress, deadline checks and safe in-flight operation handling."""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from typing import Any

from pomelo_pw.runtime import JsonValue, snapshot_json


@dataclass
class PollProgress:
    path: str
    until: dict[str, Any]
    timeout: float
    max_attempts: int | None
    started: float
    deadline: float
    attempts: int = 0
    phase: str = "body"
    step_path: str = ""
    results: dict[str, JsonValue] = field(default_factory=dict)

    def output(self) -> dict[str, Any]:
        return {
            "attempts": self.attempts,
            "elapsed_ms": int((asyncio.get_running_loop().time() - self.started) * 1000),
            "results": snapshot_json(self.results),
        }

    def diagnostics(self) -> dict[str, Any]:
        return {
            **self.output(),
            "path": self.path,
            "until": snapshot_json(self.until),
            "timeout": self.timeout,
            "effective_timeout_ms": (self.deadline - self.started) * 1000,
            "max_attempts": self.max_attempts,
            "phase": self.phase,
            "step_path": self.step_path,
        }


class PollError(RuntimeError):
    def __init__(self, message: str, diagnostics: dict[str, Any]) -> None:
        super().__init__(message)
        self.diagnostics = diagnostics


class PollTimeoutError(PollError, TimeoutError):
    """The polling deadline expired, including its body and retries."""


class PollAttemptsExhausted(PollError):
    """All configured rounds finished without satisfying until."""


class PollDeadlineExceeded(TimeoutError):
    """Internal signal for a deadline reached between asynchronous operations."""


def check_poll_deadline(polls: tuple[PollProgress, ...]) -> None:
    if polls and asyncio.get_running_loop().time() >= min(poll.deadline for poll in polls):
        raise PollDeadlineExceeded("Polling deadline expired")


_pending_operations: set[asyncio.Task[Any]] = set()


def _finish_operation(task: asyncio.Task[Any]) -> None:
    _pending_operations.discard(task)
    if not task.cancelled():
        task.exception()


async def await_poll_operation[T](
    operation: Callable[[], Coroutine[Any, Any, T]], polls: tuple[PollProgress, ...]
) -> T:
    check_poll_deadline(polls)
    if not polls:
        return await operation()
    # Keep the protocol call alive; publication and further dispatch stay in the caller.
    task = asyncio.create_task(operation())
    _pending_operations.add(task)
    task.add_done_callback(_finish_operation)
    result = await asyncio.shield(task)
    check_poll_deadline(polls)
    return result
