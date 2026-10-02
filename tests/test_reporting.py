"""Execution report boundaries, exports and nested failure facts."""

import asyncio
import time
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pomelo_pw.executor import FlowExecutor
from pomelo_pw.polling import PollError, PollTimeoutError
from pomelo_pw.reporting import ExecutionReport
from pomelo_pw.runtime import RuntimeContext
from pomelo_pw.steps.base import StepContext, StepResult
from pomelo_pw.steps.evaluate import EvaluateStep
from pomelo_pw.steps.request import RequestNetworkError


def _browser() -> MagicMock:
    page = MagicMock(url="about:blank")
    page.screenshot = AsyncMock()
    page.content = AsyncMock(return_value="<html></html>")
    page.evaluate = AsyncMock(return_value="")
    context = MagicMock()
    context.new_page = AsyncMock(return_value=page)
    context.close = AsyncMock()
    browser = MagicMock()
    browser.new_context = AsyncMock(return_value=context)
    return browser


async def _run(tmp_path: Path, flow: dict[str, Any]) -> dict[str, Any]:
    return await FlowExecutor()._run_once(
        browser=_browser(),
        flow=flow,
        flow_path=Path("report.yaml"),
        steps=flow.get("steps", []),
        overrides={},
        output=tmp_path,
        start_time=time.time(),
    )


async def test_continue_retains_errors_exports_and_nested_paths(tmp_path: Path) -> None:
    result = await _run(
        tmp_path,
        {
            "on_error": "continue",
            "report": {"steps": True},
            "variables": {"expected": 1},
            "outputs": {"known": "{{expected}}", "missing": "{{results.unpublished}}", "last": "{{results.records}}"},
            "steps": [
                {
                    "type": "foreach",
                    "items": [0],
                    "steps": [
                        {"type": "assert", "condition": {"eq": ["{{item}}", "{{expected}}"]}},
                    ],
                },
                {"type": "assert", "condition": {"eq": [True, 1]}},
                {"type": "foreach", "items": [1, 2], "steps": [], "collect": "{{item}}", "save_as": "records"},
            ],
        },
    )
    assert result["status"] == "failed"
    assert result["steps"] == {"total": 3, "executed": 3, "completed": 1}
    assert result["outputs"] == {"known": 1, "last": {"iterations": 2, "items": [1, 2]}}
    assert [(e["path"], e["type"], e["kind"]) for e in result["errors"]] == [
        ("1.index-0.1", "assert", "assertion"),
        ("2", "assert", "assertion"),
        ("outputs.missing", "output", "output"),
    ]
    assert result["errors"][0]["diagnostics"]["assertion"]["observed"][0]["value"] == 0
    assert result["errors"][0]["evidence"]["html_snapshot"]
    assert result["artifacts"]["screenshots"]
    assert [(entry["path"], entry["status"]) for entry in result["trace"]["entries"]] == [
        ("1", "failed"),
        ("1.index-0.1", "failed"),
        ("2", "failed"),
        ("3", "passed"),
    ]
    assert not any("output" in entry for entry in result["trace"]["entries"])
    assert not {"success", "failed_step", "steps_executed"}.intersection(result)


async def test_business_failed_classification_requires_explicit_assertion(tmp_path: Path) -> None:
    result = await _run(tmp_path, {"outputs": {"summary": {"failed": 5}}})
    assert result["status"] == "passed"
    assert result["outputs"] == {"summary": {"failed": 5}}
    assert result["trace"] == {"enabled": False, "entries": [], "dropped": 0}


async def test_trace_and_errors_are_bounded_without_losing_failed_status(tmp_path: Path) -> None:
    result = await _run(
        tmp_path,
        {
            "on_error": "continue",
            "report": {"steps": True, "max_steps": 1, "max_errors": 1, "max_value_bytes": 30},
            "steps": [{"type": "assert", "condition": {"eq": [1, 2]}}] * 2,
        },
    )
    assert result["status"] == "failed"
    assert result["steps"]["executed"] == 2
    assert len(result["trace"]["entries"]) == 1
    assert result["trace"]["dropped"] == 1
    assert len(result["errors"]) == 1 and result["errors_dropped"] == 1
    assert result["errors"][0]["diagnostics"]["omitted"] is True
    assert result["errors"][0]["message"].endswith("[truncated]")


async def test_optional_trace_outputs_are_bounded_but_exports_are_complete(tmp_path: Path) -> None:
    value = "a" * 200
    with patch.object(EvaluateStep, "execute", new=AsyncMock(return_value=StepResult(success=True, output=value))):
        result = await _run(
            tmp_path,
            {
                "report": {"steps": True, "include_outputs": True, "max_value_bytes": 20},
                "outputs": {"data": "{{results.data}}"},
                "steps": [{"type": "evaluate", "script": "() => null", "save_as": "data"}],
            },
        )
    assert result["trace"]["entries"][0]["output"] == {"omitted": True, "bytes": 202}
    assert result["outputs"] == {"data": value}


async def test_retry_has_one_final_trace_entry(tmp_path: Path) -> None:
    with patch.object(EvaluateStep, "execute", new=AsyncMock(side_effect=[ValueError("temporary"), StepResult(True)])):
        result = await _run(
            tmp_path,
            {
                "report": {"steps": True},
                "steps": [{"type": "evaluate", "script": "() => null", "retry": 1, "retry_delay": 0}],
            },
        )
    assert result["status"] == "passed" and result["errors"] == []
    assert len(result["trace"]["entries"]) == 1
    assert result["trace"]["entries"][0]["status"] == "passed"


async def test_poll_late_output_cannot_change_trace(tmp_path: Path) -> None:
    completed = asyncio.Event()

    async def execute(self: EvaluateStep, context: StepContext, params: dict[str, Any]) -> StepResult:
        await asyncio.sleep(0.03)
        completed.set()
        return StepResult(True, output="late")

    report = ExecutionReport({"steps": True, "include_outputs": True})
    context = StepContext(MagicMock(), RuntimeContext(), tmp_path, [], report=report)
    with patch.object(EvaluateStep, "execute", new=execute):
        with pytest.raises(PollTimeoutError):
            await FlowExecutor()._execute_step(
                {
                    "type": "poll",
                    "timeout": 10,
                    "interval": 1,
                    "until": {"eq": [1, 2]},
                    "steps": [{"type": "evaluate", "script": "() => null", "save_as": "late"}],
                },
                context,
                "1",
                1,
            )
        before = report.result("test", 10)
        await asyncio.wait_for(completed.wait(), 1)
        assert report.result("test", 10) == before
    assert context.runtime.snapshot_results() == {}
    assert all(entry["status"] == "failed" and "output" not in entry for entry in report.entries)


def test_row_merge_bounds_keep_row_identity() -> None:
    row = ExecutionReport({"steps": True})
    row.add_error(ValueError("failed"), "1", "assert")
    row.start_step("1", "assert")
    aggregate = ExecutionReport({"steps": True, "max_steps": 1, "max_errors": 1})
    aggregate.merge_row(row.result("row", 1), 0, "first")
    aggregate.merge_row(row.result("row", 1), 1, "second")
    assert aggregate.errors[0]["row"] == {"index": 0, "label": "first"}
    assert aggregate.trace_dropped == 1
    assert aggregate.result("flow", 2)["errors_dropped"] == 1


def test_poll_failure_keeps_operation_error_type_and_cause() -> None:
    try:
        try:
            raise RequestNetworkError("Query failed") from ValueError("Protocol error")
        except RequestNetworkError as cause:
            raise PollError("Poll failed", {}) from cause
    except PollError as error:
        report = ExecutionReport()
        report.add_error(error, "1", "poll")
    assert report.errors[0]["kind"] == "poll_failure"
    assert report.errors[0]["error_type"] == "RequestNetworkError"


async def test_startup_failure_uses_report_contract(tmp_path: Path) -> None:
    result = await FlowExecutor().run_flow(tmp_path / "missing.yaml")
    assert result["status"] == "failed"
    assert result["errors"][0]["kind"] == "startup"
    assert result["steps"] == {"total": 0, "executed": 0, "completed": 0}


@pytest.mark.parametrize(
    "fields",
    [
        {"outputs": []},
        {"outputs": {"a.b": 1}},
        {"outputs": {"valid": float("nan")}},
        {"report": {"steps": "true"}},
        {"report": {"max_steps": 0}},
        {"report": {"include_outputs": True}},
    ],
)
def test_invalid_report_and_export_declarations(fields: dict[str, Any]) -> None:
    assert FlowExecutor().validate_flow({"steps": [], **fields})
