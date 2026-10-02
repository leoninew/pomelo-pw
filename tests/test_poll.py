"""Focused contracts and executor regressions for bounded polling."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pomelo_pw.executor import FlowExecutor
from pomelo_pw.polling import PollAttemptsExhausted, PollError, PollTimeoutError
from pomelo_pw.runtime import RuntimeContext
from pomelo_pw.steps import get_step
from pomelo_pw.steps.base import StepContext
from pomelo_pw.steps.poll import PollStep


@pytest.fixture
def context(tmp_path: Path) -> StepContext:
    page = MagicMock()
    page.evaluate = AsyncMock()
    return StepContext(page, RuntimeContext(), tmp_path, [])


def poll_step(**overrides: Any) -> dict[str, Any]:
    return {
        "type": "poll",
        "until": {"eq": ["{{results.task}}", "ready"]},
        "timeout": 1000,
        "interval": 1,
        "steps": [{"type": "evaluate", "script": "() => 'ready'", "save_as": "task"}],
        **overrides,
    }


def test_registration_and_recursive_validation() -> None:
    assert get_step("poll") is PollStep
    assert not PollStep.validate_params(poll_step())
    errors = FlowExecutor().validate_flow({"steps": [poll_step(steps=[{"type": "evaluate"}])]})
    assert any("steps[0].steps[0]" in error and "script" in error for error in errors)


@pytest.mark.parametrize(
    "overrides",
    [
        {"timeout": 0},
        {"timeout": float("inf")},
        {"interval": True},
        {"interval": "10"},
        {"max_attempts": None},
        {"max_attempts": 1.5},
        {"max_attempts": 0},
        {"steps": []},
        {"until": "true"},
        {"retry": 1},
    ],
)
def test_invalid_parameters(overrides: dict[str, Any]) -> None:
    assert PollStep.validate_params(poll_step(**overrides))


def test_typed_bounds_checked_after_resolution() -> None:
    assert not PollStep.validate_params(poll_step(timeout="{{duration}}", max_attempts="{{limit}}"))
    assert PollStep.validate_resolved_params(poll_step(timeout="1000"))


async def test_first_query_is_immediate_and_overwrites_old_result(context: StepContext) -> None:
    context.runtime.publish("task", "ready")
    page = cast(MagicMock, context.page)
    page.evaluate.return_value = "failed"
    result = await FlowExecutor()._execute_step(
        poll_step(until={"in": ["{{results.task}}", ["ready", "failed"]]}, save_as="polling"), context, "1", 1
    )
    assert result.success
    assert page.evaluate.await_count == 1
    output = context.runtime.snapshot_results()["polling"]
    assert isinstance(output, dict)
    assert output["attempts"] == 1
    assert output["results"] == {"task": "failed"}


async def test_multiple_steps_read_fresh_results_and_succeed_on_last_attempt(context: StepContext) -> None:
    page = cast(MagicMock, context.page)
    page.evaluate.side_effect = ["pending", False, "ready", True]
    await FlowExecutor()._execute_step(
        poll_step(
            until={"eq": ["{{results.done}}", True]},
            max_attempts=2,
            steps=[
                {"type": "evaluate", "script": "() => 'pending'", "save_as": "task"},
                {"type": "evaluate", "script": "x => x === 'ready'", "args": "{{results.task}}", "save_as": "done"},
            ],
            save_as="polling",
        ),
        context,
        "1",
        1,
    )
    assert [call.args[1]["args"] for call in page.evaluate.await_args_list] == [None, "pending", None, "ready"]
    output = context.runtime.snapshot_results()["polling"]
    assert isinstance(output, dict)
    assert output["attempts"] == 2
    assert output["results"] == {"task": "ready", "done": True}


async def test_attempt_exhaustion_preserves_last_result_and_nested_path(context: StepContext) -> None:
    page = cast(MagicMock, context.page)
    page.evaluate.return_value = "pending"
    with pytest.raises(PollAttemptsExhausted, match="max_attempts=2") as error:
        await FlowExecutor()._execute_steps(
            [{"type": "foreach", "items": ["item"], "steps": [poll_step(max_attempts=2, save_as="polling")]}], context
        )
    detail = error.value.diagnostics["polls"][0]
    assert detail["attempts"] == 2
    assert detail["results"] == {"task": "pending"}
    assert detail["step_path"] == "1.index-0.1.attempt-2.until"
    assert "polling" not in context.runtime.snapshot_results()


async def test_child_failure_does_not_replay_prior_submission(context: StepContext) -> None:
    page = cast(MagicMock, context.page)
    page.evaluate.side_effect = ["submitted", RuntimeError("read failed")]
    with pytest.raises(PollError, match="attempt-1.1.*read failed"):
        await FlowExecutor()._execute_steps(
            [
                {"type": "evaluate", "script": "() => 'submitted'", "save_as": "submitted"},
                poll_step(),
            ],
            context,
        )
    assert page.evaluate.await_count == 2
    assert context.runtime.snapshot_results() == {"submitted": "submitted"}


async def test_query_retry_stays_in_one_round(context: StepContext) -> None:
    page = cast(MagicMock, context.page)
    page.evaluate.side_effect = [RuntimeError("transient"), "ready"]
    result = await FlowExecutor()._execute_step(
        poll_step(
            steps=[{"type": "evaluate", "script": "() => 'ready'", "save_as": "task", "retry": 1, "retry_delay": 0}]
        ),
        context,
        "1",
        1,
    )
    assert isinstance(result.output, dict)
    assert result.output["attempts"] == 1
    assert page.evaluate.await_count == 2


@pytest.mark.parametrize("phase", ["interval", "retry_delay", "wait"])
async def test_waits_and_retry_delays_consume_total_budget(context: StepContext, phase: str) -> None:
    page = cast(MagicMock, context.page)
    page.evaluate.return_value = "pending"
    overrides: dict[str, Any] = {"timeout": 25, "interval": 1000}
    if phase == "retry_delay":
        page.evaluate.side_effect = RuntimeError("transient")
        overrides["steps"] = [
            {"type": "evaluate", "script": "() => null", "save_as": "task", "retry": 3, "retry_delay": 1000}
        ]
    elif phase == "wait":
        overrides["steps"] = [{"type": "wait", "condition": {"eq": [1, 2]}, "timeout": 1000}]
    with pytest.raises(PollTimeoutError) as error:
        await FlowExecutor()._execute_step(poll_step(**overrides), context, "1", 1)
    detail = error.value.diagnostics["polls"][0]
    assert detail["attempts"] == 1
    assert detail["elapsed_ms"] < 500
    assert page.evaluate.await_count == (0 if phase == "wait" else 1)
    # The shielded native wait finishes under its clamped timeout.
    await asyncio.sleep(0.03)


async def test_slow_query_cannot_publish_late_or_start_following_step(context: StepContext) -> None:
    page = cast(MagicMock, context.page)
    release = asyncio.Event()
    finished = asyncio.Event()

    async def slow_query(*args: Any) -> str:
        await release.wait()
        finished.set()
        return "ready"

    page.evaluate.side_effect = slow_query
    context.runtime.publish("task", "old")
    executor = FlowExecutor()
    with patch.object(context.runtime, "publish", wraps=context.runtime.publish) as publish:
        with pytest.raises(PollTimeoutError):
            await executor._execute_step(
                poll_step(
                    timeout=25,
                    steps=[
                        {"type": "evaluate", "script": "() => 'ready'", "save_as": "task"},
                        {"type": "evaluate", "script": "() => null"},
                    ],
                ),
                context,
                "1",
                1,
            )
        release.set()
        await asyncio.wait_for(finished.wait(), 1)
        await asyncio.sleep(0)
        publish.assert_not_called()
    assert page.evaluate.await_count == 1
    assert context.runtime.snapshot_results() == {}


async def test_failed_rebind_diagnostics_keep_previous_success(context: StepContext) -> None:
    page = cast(MagicMock, context.page)
    page.evaluate.side_effect = ["pending", RuntimeError("next query failed")]
    with pytest.raises(PollError, match="next query failed") as error:
        await FlowExecutor()._execute_step(poll_step(), context, "1", 1)
    assert error.value.diagnostics["polls"][0]["results"] == {"task": "pending"}
    assert "task" not in context.runtime.snapshot_results()


async def test_until_error_fails_without_retrying_round(context: StepContext) -> None:
    page = cast(MagicMock, context.page)
    page.evaluate.return_value = "pending"
    with pytest.raises(PollError, match="until.eq") as error:
        await FlowExecutor()._execute_step(poll_step(until={"eq": ["{{results.missing}}", True]}), context, "1", 1)
    assert error.value.diagnostics["polls"][0]["phase"] == "until"
    assert page.evaluate.await_count == 1


async def test_foreach_binding_and_poll_local_variables(context: StepContext) -> None:
    page = cast(MagicMock, context.page)
    page.evaluate.side_effect = ["a", "b"]
    await FlowExecutor()._execute_steps(
        [
            {
                "type": "foreach",
                "items": ["a", "b"],
                "steps": [
                    poll_step(
                        variables={"expected": "{{item}}"},
                        until={"eq": ["{{results.task}}", "{{expected}}"]},
                        steps=[{"type": "evaluate", "script": "x => x", "args": "{{item}}", "save_as": "task"}],
                    )
                ],
            }
        ],
        context,
    )
    assert [call.args[1]["args"] for call in page.evaluate.await_args_list] == ["a", "b"]
    assert context.inputs == {}


async def test_nested_poll_cannot_extend_parent_deadline(context: StepContext) -> None:
    page = cast(MagicMock, context.page)
    page.evaluate.return_value = "pending"
    inner = poll_step(timeout=1000, interval=1000)
    with pytest.raises(PollTimeoutError) as error:
        await FlowExecutor()._execute_step(poll_step(timeout=25, steps=[inner]), context, "1", 1)
    details = error.value.diagnostics["polls"]
    assert [detail["path"] for detail in details] == ["1", "1.attempt-1.1"]
    assert details[1]["effective_timeout_ms"] <= 25
    assert page.evaluate.await_count == 1


async def test_while_can_finish_on_exact_safety_limit(context: StepContext) -> None:
    context.runtime.publish("count", 0)
    page = cast(MagicMock, context.page)
    page.evaluate.side_effect = [1, 2]
    await FlowExecutor()._execute_steps(
        [
            {
                "type": "loop",
                "while": {"ne": ["{{results.count}}", 2]},
                "max_iterations": 2,
                "steps": [
                    {"type": "evaluate", "script": "n => n + 1", "args": "{{results.count}}", "save_as": "count"}
                ],
            }
        ],
        context,
    )
    assert context.runtime.snapshot_results()["count"] == 2


async def test_continue_after_poll_failure_keeps_failed_flow_and_diagnostics(context: StepContext) -> None:
    executor = FlowExecutor()
    browser_context = MagicMock()
    browser_context.new_page = AsyncMock(return_value=context.page)
    browser_context.close = AsyncMock()
    page = cast(MagicMock, context.page)
    page.evaluate.side_effect = ["pending", None]
    evidence = MagicMock(screenshot_path=None, html_snapshot_path=None, console_errors=[], network_errors=[])
    evidence.to_dict.return_value = {}
    with (
        patch.object(executor.browser_lifecycle, "new_context", new=AsyncMock(return_value=browser_context)),
        patch("pomelo_pw.executor.ErrorContextCollector") as collector,
    ):
        collector.return_value.collect_error_context = AsyncMock(return_value=evidence)
        result = await executor._run_once(
            browser=MagicMock(),
            flow={"on_error": "continue"},
            flow_path=Path("poll.yaml"),
            steps=[poll_step(max_attempts=1), {"type": "evaluate", "script": "() => null"}],
            overrides={},
            output=context.output_dir,
            start_time=time.time(),
        )
    assert result["status"] == "failed"
    assert result["steps"] == {"total": 2, "executed": 2, "completed": 1}
    assert result["errors"][0]["kind"] == "exhausted"
    assert result["errors"][0]["diagnostics"]["polls"][0]["results"] == {"task": "pending"}
    assert page.evaluate.await_count == 2
    browser_context.close.assert_awaited_once()
