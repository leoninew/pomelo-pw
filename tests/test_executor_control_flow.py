"""Tests for executor control flow: _execute_steps and _execute_loop."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pomelo_pw.executor import FlowExecutor
from pomelo_pw.steps.base import StepContext, StepResult


def _make_context(url: str = "https://example.com") -> StepContext:
    page = MagicMock()
    page.url = url
    page.query_selector = AsyncMock(return_value=MagicMock())
    page.content = AsyncMock(return_value="<html></html>")
    page.evaluate = AsyncMock(return_value=True)
    return StepContext(
        page=page,
        variables={},
        output_dir=Path("/tmp/out"),
        screenshots=[],
    )


class TestExecuteSteps:
    """Tests for FlowExecutor._execute_steps."""

    @pytest.mark.asyncio
    async def test_executes_all_steps_in_order(self) -> None:
        executor = FlowExecutor()
        executed: list[str] = []

        async def fake_execute(context: StepContext, params: dict[str, Any]) -> StepResult:
            executed.append(params["type"])
            return StepResult(success=True, message="ok")

        with patch("pomelo_pw.executor.get_step") as mock_get_step:
            mock_step_class = MagicMock()
            mock_step_class.return_value.execute = fake_execute
            mock_get_step.return_value = mock_step_class

            ctx = _make_context()
            steps = [
                {"type": "navigate", "url": "https://example.com"},
                {"type": "screenshot", "file": "a.png"},
            ]
            await executor._execute_steps(steps, ctx, {})

        assert executed == ["navigate", "screenshot"]

    @pytest.mark.asyncio
    async def test_raises_on_step_failure(self) -> None:
        executor = FlowExecutor()

        async def failing_execute(context: StepContext, params: dict[str, Any]) -> StepResult:
            return StepResult(success=False, message="element not found")

        with patch("pomelo_pw.executor.get_step") as mock_get_step:
            mock_step_class = MagicMock()
            mock_step_class.return_value.execute = failing_execute
            mock_get_step.return_value = mock_step_class

            ctx = _make_context()
            with pytest.raises(RuntimeError, match="element not found"):
                await executor._execute_steps(
                    [{"type": "click", "selector": ".btn"}], ctx, {}
                )

    @pytest.mark.asyncio
    async def test_raises_on_unknown_step_type(self) -> None:
        executor = FlowExecutor()

        with patch("pomelo_pw.executor.get_step", return_value=None):
            ctx = _make_context()
            with pytest.raises(ValueError, match="Unknown step type"):
                await executor._execute_steps(
                    [{"type": "nonexistent"}], ctx, {}
                )

    @pytest.mark.asyncio
    async def test_step_level_variables_merged(self) -> None:
        executor = FlowExecutor()
        received_vars: list[dict[str, Any]] = []

        async def capture_execute(context: StepContext, params: dict[str, Any]) -> StepResult:
            received_vars.append(dict(context.variables))
            return StepResult(success=True, message="ok")

        with patch("pomelo_pw.executor.get_step") as mock_get_step:
            mock_step_class = MagicMock()
            mock_step_class.return_value.execute = capture_execute
            mock_get_step.return_value = mock_step_class

            ctx = _make_context()
            steps = [{
                "type": "navigate",
                "url": "https://example.com",
                "variables": {"step_var": "step_value"},
            }]
            await executor._execute_steps(steps, ctx, {"global_var": "global_value"})

        assert received_vars[0]["global_var"] == "global_value"
        assert received_vars[0]["step_var"] == "step_value"

    @pytest.mark.asyncio
    async def test_empty_steps_list_succeeds(self) -> None:
        executor = FlowExecutor()
        ctx = _make_context()
        # Should not raise
        await executor._execute_steps([], ctx, {})


class TestExecuteLoop:
    """Tests for FlowExecutor._execute_loop."""

    @pytest.mark.asyncio
    async def test_times_loop_runs_correct_count(self) -> None:
        executor = FlowExecutor()
        call_count = 0

        async def fake_execute_steps(
            steps: list[dict[str, Any]],
            context: StepContext,
            global_vars: dict[str, Any],
            prefix: str = "",
        ) -> None:
            nonlocal call_count
            call_count += 1

        executor._execute_steps = fake_execute_steps  # type: ignore[method-assign]

        ctx = _make_context()
        await executor._execute_loop(
            loop_data={"type": "times", "iterations": 4, "steps": [{"type": "scroll"}]},
            context=ctx,
            global_vars={},
        )

        assert call_count == 4

    @pytest.mark.asyncio
    async def test_while_loop_stops_when_condition_false(self) -> None:
        executor = FlowExecutor()
        call_count = 0

        async def fake_execute_steps(
            steps: list[dict[str, Any]],
            context: StepContext,
            global_vars: dict[str, Any],
            prefix: str = "",
        ) -> None:
            nonlocal call_count
            call_count += 1

        executor._execute_steps = fake_execute_steps  # type: ignore[method-assign]

        # Condition is false from the start
        ctx = _make_context(url="https://other.com")
        await executor._execute_loop(
            loop_data={
                "type": "while",
                "condition": "url_contains: example.com",
                "max_iterations": 10,
                "steps": [],
            },
            context=ctx,
            global_vars={},
        )

        assert call_count == 0

    @pytest.mark.asyncio
    async def test_while_loop_respects_max_iterations(self) -> None:
        executor = FlowExecutor()
        call_count = 0

        async def fake_execute_steps(
            steps: list[dict[str, Any]],
            context: StepContext,
            global_vars: dict[str, Any],
            prefix: str = "",
        ) -> None:
            nonlocal call_count
            call_count += 1

        executor._execute_steps = fake_execute_steps  # type: ignore[method-assign]

        # Condition always true → should stop at max_iterations
        ctx = _make_context(url="https://example.com")
        await executor._execute_loop(
            loop_data={
                "type": "while",
                "condition": "url_contains: example.com",
                "max_iterations": 3,
                "steps": [],
            },
            context=ctx,
            global_vars={},
        )

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_times_zero_iterations(self) -> None:
        executor = FlowExecutor()
        call_count = 0

        async def fake_execute_steps(
            steps: list[dict[str, Any]],
            context: StepContext,
            global_vars: dict[str, Any],
            prefix: str = "",
        ) -> None:
            nonlocal call_count
            call_count += 1

        executor._execute_steps = fake_execute_steps  # type: ignore[method-assign]

        ctx = _make_context()
        await executor._execute_loop(
            loop_data={"type": "times", "iterations": 0, "steps": []},
            context=ctx,
            global_vars={},
        )

        assert call_count == 0
