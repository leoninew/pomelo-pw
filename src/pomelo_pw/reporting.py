"""Bounded execution details and the public run-report contract."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from pomelo_pw.runtime import NO_OUTPUT, JsonValue, NoOutput, snapshot_json

REPORT_DEFAULTS: dict[str, Any] = {
    "steps": False,
    "max_steps": 1000,
    "include_outputs": False,
    "max_value_bytes": 16384,
    "max_errors": 100,
}


class ExecutionStepError(RuntimeError):
    def __init__(self, message: str, path: str, step_type: str) -> None:
        super().__init__(message)
        self.path = path
        self.step_type = step_type


class CollectionLimitError(RuntimeError):
    """Explicit iteration collection exceeded a declared bound."""


def validate_report_options(options: Any) -> list[str]:
    if not isinstance(options, dict):
        return ["report must be an object"]
    errors = [f"report.{key}: unknown option" for key in options.keys() - REPORT_DEFAULTS.keys()]
    for key in ("steps", "include_outputs"):
        if key in options and type(options[key]) is not bool:
            errors.append(f"report.{key} must be a boolean")
    for key in ("max_steps", "max_value_bytes", "max_errors"):
        if key in options and (type(options[key]) is not int or options[key] <= 0):
            errors.append(f"report.{key} must be a positive integer")
    if options.get("include_outputs") and options.get("steps") is not True:
        errors.append("report.include_outputs requires report.steps: true")
    return errors


@dataclass
class ExecutionReport:
    options: dict[str, Any] = field(default_factory=dict)
    entries: list[dict[str, Any]] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    trace_dropped: int = 0
    error_count: int = 0

    def __post_init__(self) -> None:
        errors = validate_report_options(self.options)
        if errors:
            raise ValueError("; ".join(errors))
        self.options = {**REPORT_DEFAULTS, **self.options}

    def bounded_value(self, value: Any) -> JsonValue:
        snapshot = snapshot_json(value)
        size = len(json.dumps(snapshot, ensure_ascii=False, allow_nan=False).encode("utf-8"))
        if size > self.options["max_value_bytes"]:
            return {"omitted": True, "bytes": size}
        return snapshot

    def start_step(self, path: str, step_type: str) -> dict[str, Any] | None:
        if not self.options["steps"]:
            return None
        if len(self.entries) >= self.options["max_steps"]:
            self.trace_dropped += 1
            return None
        entry = {"path": path, "type": step_type, "status": "running", "duration_ms": 0}
        self.entries.append(entry)
        return entry

    def finish_step(
        self, entry: dict[str, Any] | None, status: str, duration_ms: int, output: JsonValue | NoOutput = NO_OUTPUT
    ) -> None:
        if entry is None:
            return
        entry.update(status=status, duration_ms=duration_ms)
        if self.options["include_outputs"] and output is not NO_OUTPUT:
            entry["output"] = self.bounded_value(output)

    def add_error(
        self,
        error: BaseException,
        path: str,
        step_type: str,
        *,
        evidence: dict[str, Any] | None = None,
        kind: str | None = None,
    ) -> None:
        self.error_count += 1
        if len(self.errors) >= self.options["max_errors"]:
            return
        diagnostics: dict[str, Any] = {}
        selected_error: BaseException | None = None
        kinds = {
            "AssertionFailed": "assertion",
            "PollTimeoutError": "timeout",
            "PollAttemptsExhausted": "exhausted",
            "PollError": "poll_failure",
            "CollectionLimitError": "collection_limit",
            "ConditionEvaluationError": "condition",
            "ConditionWaitTimeout": "timeout",
            "RequestTimeoutError": "timeout",
        }
        observed_kind = "step"
        has_step_path = False
        cause: BaseException | None = error
        seen: set[int] = set()
        while cause is not None and id(cause) not in seen:
            seen.add(id(cause))
            if isinstance(cause, ExecutionStepError):
                path, step_type = cause.path, cause.step_type
                has_step_path = True
            else:
                cause_type = type(cause).__name__
                if selected_error is None or type(selected_error).__name__ == "PollError":
                    selected_error = cause
                    observed_kind = kinds.get(cause_type, observed_kind)
            details = getattr(cause, "diagnostics", {})
            if isinstance(details, dict):
                for key, value in details.items():
                    diagnostics.setdefault(key, value)
                if not has_step_path and details.get("polls"):
                    path = details["polls"][0]["step_path"] or details["polls"][0]["path"]
                    step_type = "poll"
            cause = cause.__cause__
        message_bytes = str(error).encode("utf-8")
        limit = self.options["max_value_bytes"]
        message = message_bytes[:limit].decode("utf-8", errors="ignore")
        if len(message_bytes) > limit:
            message += " [truncated]"
        self.errors.append(
            {
                "path": path,
                "type": step_type,
                "kind": kind or observed_kind,
                "error_type": type(selected_error or error).__name__,
                "message": message,
                "diagnostics": self.bounded_value(diagnostics),
                "evidence": {
                    key: self.bounded_value(value)
                    for key, value in (evidence or {}).items()
                    if key not in {"step_index", "step_type"}
                },
            }
        )

    def merge_row(self, result: dict[str, Any], index: int, label: str) -> None:
        row = {"index": index, "label": label}
        self.error_count += len(result["errors"]) + result["errors_dropped"]
        remaining = self.options["max_errors"] - len(self.errors)
        self.errors.extend({**error, "row": row} for error in result["errors"][:remaining])
        if self.options["steps"]:
            trace = result["trace"]
            remaining = self.options["max_steps"] - len(self.entries)
            self.entries.extend({**entry, "row": row} for entry in trace["entries"][:remaining])
            self.trace_dropped += trace["dropped"] + max(0, len(trace["entries"]) - remaining)

    def result(
        self,
        flow: str,
        duration_ms: int,
        *,
        outputs: dict[str, JsonValue] | None = None,
        screenshots: list[str] | None = None,
        total: int = 0,
        executed: int = 0,
        completed: int = 0,
    ) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "status": "failed" if self.error_count else "passed",
            "flow": flow,
            "duration_ms": duration_ms,
            "outputs": snapshot_json(outputs or {}),
            "steps": {"total": total, "executed": executed, "completed": completed},
            "trace": {
                "enabled": self.options["steps"],
                "entries": snapshot_json(self.entries),
                "dropped": self.trace_dropped,
            },
            "errors": snapshot_json(self.errors),
            "errors_dropped": self.error_count - len(self.errors),
            "artifacts": {"screenshots": list(screenshots or [])},
            "rows": [],
            "row_summary": None,
        }
