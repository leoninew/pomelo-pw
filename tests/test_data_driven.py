"""Tests for data-driven flow execution."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pomelo_pw.executor import FlowExecutor
from pomelo_pw.runtime import RuntimeContext
from pomelo_pw.steps.base import StepContext, StepResult
from pomelo_pw.steps.evaluate import EvaluateStep


def _make_browser() -> MagicMock:
    """Create a mock browser with a page."""
    page = MagicMock()
    page.url = "https://example.com"
    page.screenshot = AsyncMock()
    page.content = AsyncMock(return_value="<html></html>")
    page.evaluate = AsyncMock(return_value="")

    context = MagicMock()
    context.new_page = AsyncMock(return_value=page)
    context.close = AsyncMock()

    browser = MagicMock()
    browser.new_context = AsyncMock(return_value=context)
    browser.close = AsyncMock()
    return browser


def _ok_result(**extra: Any) -> dict[str, Any]:
    return {
        "success": True,
        "flow": "test",
        "duration_ms": 10,
        "screenshots": [],
        "steps_executed": 1,
        "steps_total": 1,
        **extra,
    }


def _fail_result(**extra: Any) -> dict[str, Any]:
    return {
        "success": False,
        "flow": "test",
        "duration_ms": 10,
        "screenshots": [],
        "steps_executed": 0,
        "steps_total": 1,
        **extra,
    }


class TestDataDrivenExpansion:
    """Tests for _run_data_driven."""

    @pytest.mark.asyncio
    async def test_row_output_subdirectory_uses_label(self, tmp_path: Path) -> None:
        """Each row with _label gets its own subdirectory."""
        executor = FlowExecutor()
        received_outputs: list[Path] = []

        async def fake_run_once(
            browser: Any,
            flow: Any,
            flow_path: Any,
            steps: Any,
            overrides: Any,
            output: Path,
            start_time: Any,
            row_inputs: dict[str, Any],
        ) -> dict[str, Any]:
            received_outputs.append(output)
            return _ok_result()

        data_rows = [
            {"_label": "user-alice", "username": "alice"},
            {"_label": "user-bob", "username": "bob"},
        ]

        with (
            patch.object(executor, "_launch_browser", new=AsyncMock(return_value=_make_browser())),
            patch.object(executor, "_run_once", side_effect=fake_run_once),
        ):
            await executor._run_data_driven(
                flow={"name": "test"},
                flow_path=Path("test.yaml"),
                steps=[],
                overrides={},
                output=tmp_path,
                headless=True,
                data_rows=data_rows,
                start_time=time.time(),
            )

        assert received_outputs[0] == tmp_path / "user-alice"
        assert received_outputs[1] == tmp_path / "user-bob"

    @pytest.mark.asyncio
    async def test_row_output_subdirectory_default_label(self, tmp_path: Path) -> None:
        """Rows without _label get row-N subdirectory."""
        executor = FlowExecutor()
        received_outputs: list[Path] = []

        async def fake_run_once(
            browser: Any,
            flow: Any,
            flow_path: Any,
            steps: Any,
            overrides: Any,
            output: Path,
            start_time: Any,
            row_inputs: dict[str, Any],
        ) -> dict[str, Any]:
            received_outputs.append(output)
            return _ok_result()

        data_rows = [{"username": "alice"}, {"username": "bob"}]

        with (
            patch.object(executor, "_launch_browser", new=AsyncMock(return_value=_make_browser())),
            patch.object(executor, "_run_once", side_effect=fake_run_once),
        ):
            await executor._run_data_driven(
                flow={"name": "test"},
                flow_path=Path("test.yaml"),
                steps=[],
                overrides={},
                output=tmp_path,
                headless=True,
                data_rows=data_rows,
                start_time=time.time(),
            )

        assert received_outputs[0] == tmp_path / "row-1"
        assert received_outputs[1] == tmp_path / "row-2"

    @pytest.mark.asyncio
    async def test_row_vars_merged_with_flow_inputs(self, tmp_path: Path) -> None:
        """Row data is merged with flow inputs; row takes precedence on conflict."""
        executor = FlowExecutor()
        received_vars: list[dict[str, Any]] = []

        async def fake_run_once(
            browser: Any,
            flow: Any,
            flow_path: Any,
            steps: Any,
            overrides: dict[str, Any],
            output: Any,
            start_time: Any,
            row_inputs: dict[str, Any],
        ) -> dict[str, Any]:
            received_vars.append(RuntimeContext(flow.get("variables", {}), overrides, row_inputs).effective_inputs())
            return _ok_result()

        data_rows = [{"username": "alice", "env": "staging"}]
        flow_inputs = {"env": "prod", "base_url": "https://example.com"}

        with (
            patch.object(executor, "_launch_browser", new=AsyncMock(return_value=_make_browser())),
            patch.object(executor, "_run_once", side_effect=fake_run_once),
        ):
            await executor._run_data_driven(
                flow={"name": "test", "variables": flow_inputs},
                flow_path=Path("test.yaml"),
                steps=[],
                overrides={},
                output=tmp_path,
                headless=True,
                data_rows=data_rows,
                start_time=time.time(),
            )

        assert received_vars[0]["username"] == "alice"
        assert received_vars[0]["base_url"] == "https://example.com"
        assert received_vars[0]["env"] == "staging"  # row overrides base

    @pytest.mark.asyncio
    async def test_result_aggregates_all_rows(self, tmp_path: Path) -> None:
        executor = FlowExecutor()
        call_idx = 0

        async def fake_run_once(
            browser: Any,
            flow: Any,
            flow_path: Any,
            steps: Any,
            overrides: Any,
            output: Any,
            start_time: Any,
            row_inputs: dict[str, Any],
        ) -> dict[str, Any]:
            nonlocal call_idx
            call_idx += 1
            return _ok_result(screenshots=[f"shot-{call_idx}.png"])

        data_rows = [{"username": "alice"}, {"username": "bob"}, {"username": "carol"}]

        with (
            patch.object(executor, "_launch_browser", new=AsyncMock(return_value=_make_browser())),
            patch.object(executor, "_run_once", side_effect=fake_run_once),
        ):
            result = await executor._run_data_driven(
                flow={"name": "test"},
                flow_path=Path("test.yaml"),
                steps=[],
                overrides={},
                output=tmp_path,
                headless=True,
                data_rows=data_rows,
                start_time=time.time(),
            )

        assert result["success"] is True
        assert result["data_driven"] is True
        assert result["rows_total"] == 3
        assert result["rows_passed"] == 3
        assert result["rows_failed"] == 0
        assert len(result["row_results"]) == 3
        assert len(result["screenshots"]) == 3

    @pytest.mark.asyncio
    async def test_stops_on_first_failure_when_on_error_stop(self, tmp_path: Path) -> None:
        executor = FlowExecutor()
        call_count = 0

        async def fake_run_once(
            browser: Any,
            flow: Any,
            flow_path: Any,
            steps: Any,
            overrides: Any,
            output: Any,
            start_time: Any,
            row_inputs: dict[str, Any],
        ) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            return _ok_result() if call_count != 2 else _fail_result()

        data_rows = [{"username": "alice"}, {"username": "bob"}, {"username": "carol"}]

        with (
            patch.object(executor, "_launch_browser", new=AsyncMock(return_value=_make_browser())),
            patch.object(executor, "_run_once", side_effect=fake_run_once),
        ):
            result = await executor._run_data_driven(
                flow={"name": "test", "on_error": "stop"},
                flow_path=Path("test.yaml"),
                steps=[],
                overrides={},
                output=tmp_path,
                headless=True,
                data_rows=data_rows,
                start_time=time.time(),
            )

        assert call_count == 2  # stopped after row 2 failed
        assert result["success"] is False
        assert result["rows_failed"] == 1

    @pytest.mark.asyncio
    async def test_continues_on_failure_when_on_error_continue(self, tmp_path: Path) -> None:
        executor = FlowExecutor()
        call_count = 0

        async def fake_run_once(
            browser: Any,
            flow: Any,
            flow_path: Any,
            steps: Any,
            overrides: Any,
            output: Any,
            start_time: Any,
            row_inputs: dict[str, Any],
        ) -> dict[str, Any]:
            nonlocal call_count
            call_count += 1
            return _ok_result() if call_count != 2 else _fail_result()

        data_rows = [{"username": "alice"}, {"username": "bob"}, {"username": "carol"}]

        with (
            patch.object(executor, "_launch_browser", new=AsyncMock(return_value=_make_browser())),
            patch.object(executor, "_run_once", side_effect=fake_run_once),
        ):
            result = await executor._run_data_driven(
                flow={"name": "test", "on_error": "continue"},
                flow_path=Path("test.yaml"),
                steps=[],
                overrides={},
                output=tmp_path,
                headless=True,
                data_rows=data_rows,
                start_time=time.time(),
            )

        assert call_count == 3  # all rows executed
        assert result["rows_passed"] == 2
        assert result["rows_failed"] == 1
        assert result["success"] is False


class TestRunFlowDataDrivenRouting:
    def test_validate_flow_allows_data_field(self) -> None:
        executor = FlowExecutor()
        flow = {
            "data": [{"username": "alice"}],
            "steps": [{"type": "navigate", "url": "https://example.com"}],
        }
        errors = executor.validate_flow(flow)
        assert len(errors) == 0

    async def test_each_row_has_isolated_results_and_cli_wins(self, tmp_path: Path) -> None:
        executor = FlowExecutor()
        seen: list[dict[str, Any]] = []
        runtimes: list[RuntimeContext] = []

        async def execute(self: EvaluateStep, context: StepContext, params: dict[str, Any]) -> StepResult:
            assert context.runtime.snapshot_results() == {}
            runtimes.append(context.runtime)
            seen.append(params["args"])
            return StepResult(success=True, output=params["args"])

        with (
            patch.object(executor, "_launch_browser", new=AsyncMock(return_value=_make_browser())),
            patch.object(EvaluateStep, "execute", new=execute),
        ):
            result = await executor._run_data_driven(
                flow={"variables": {"key": "flow"}},
                flow_path=Path("test.yaml"),
                steps=[
                    {
                        "type": "evaluate",
                        "script": "x => x",
                        "save_as": "record",
                        "args": {"key": "{{key}}", "row": "{{row}}"},
                        "variables": {"key": "step"},
                    }
                ],
                overrides={"key": "cli"},
                output=tmp_path,
                headless=True,
                data_rows=[{"key": "row", "row": 1}, {"key": "row", "row": 2}],
                start_time=time.time(),
            )
        assert result["success"]
        assert seen == [{"key": "cli", "row": 1}, {"key": "cli", "row": 2}]
        assert runtimes[0] is not runtimes[1]
        assert runtimes[0].snapshot_results() == {"record": seen[0]}
        assert runtimes[1].snapshot_results() == {"record": seen[1]}
