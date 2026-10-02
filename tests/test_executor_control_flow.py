"""Tests for executor control flow: _execute_steps and _execute_loop."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pomelo_pw.executor import FlowExecutor
from pomelo_pw.runtime import RuntimeContext
from pomelo_pw.steps.base import StepContext, StepResult, StepSpec
from pomelo_pw.steps.evaluate import EvaluateStep


def _make_context(url: str = "https://example.com") -> StepContext:
    page = MagicMock()
    page.url = url
    page.query_selector = AsyncMock(return_value=MagicMock())
    page.content = AsyncMock(return_value="<html></html>")
    page.evaluate = AsyncMock(return_value=True)
    return StepContext(
        page=page,
        runtime=RuntimeContext(),
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
            mock_step_class.spec = StepSpec(name="mock")
            mock_step_class.validate_params.return_value = []
            mock_step_class.validate_resolved_params.return_value = []
            mock_step_class.return_value.execute = fake_execute
            mock_get_step.return_value = mock_step_class

            ctx = _make_context()
            steps = [
                {"type": "navigate", "url": "https://example.com"},
                {"type": "screenshot", "file": "a.png"},
            ]
            await executor._execute_steps(steps, ctx)

        assert executed == ["navigate", "screenshot"]

    @pytest.mark.asyncio
    async def test_raises_on_step_failure(self) -> None:
        executor = FlowExecutor()

        async def failing_execute(context: StepContext, params: dict[str, Any]) -> StepResult:
            return StepResult(success=False, message="element not found")

        with patch("pomelo_pw.executor.get_step") as mock_get_step:
            mock_step_class = MagicMock()
            mock_step_class.spec = StepSpec(name="mock")
            mock_step_class.validate_params.return_value = []
            mock_step_class.validate_resolved_params.return_value = []
            mock_step_class.return_value.execute = failing_execute
            mock_get_step.return_value = mock_step_class

            ctx = _make_context()
            with pytest.raises(RuntimeError, match="element not found"):
                await executor._execute_steps([{"type": "click", "selector": ".btn"}], ctx)

    @pytest.mark.asyncio
    async def test_raises_on_unknown_step_type(self) -> None:
        executor = FlowExecutor()

        with patch("pomelo_pw.executor.get_step", return_value=None):
            ctx = _make_context()
            with pytest.raises(ValueError, match="Unknown step type"):
                await executor._execute_steps([{"type": "nonexistent"}], ctx)

    @pytest.mark.asyncio
    async def test_step_level_variables_merged(self) -> None:
        executor = FlowExecutor()
        received_vars: list[dict[str, Any]] = []

        async def capture_execute(context: StepContext, params: dict[str, Any]) -> StepResult:
            received_vars.append(dict(context.inputs))
            return StepResult(success=True, message="ok")

        with patch("pomelo_pw.executor.get_step") as mock_get_step:
            mock_step_class = MagicMock()
            mock_step_class.spec = StepSpec(name="mock")
            mock_step_class.validate_params.return_value = []
            mock_step_class.validate_resolved_params.return_value = []
            mock_step_class.return_value.execute = capture_execute
            mock_get_step.return_value = mock_step_class

            ctx = _make_context()
            steps = [
                {
                    "type": "navigate",
                    "url": "https://example.com",
                    "variables": {"step_var": "step_value"},
                }
            ]
            ctx.runtime.flow_inputs = {"global_var": "global_value"}
            await executor._execute_steps(steps, ctx)

        assert received_vars[0]["global_var"] == "global_value"
        assert received_vars[0]["step_var"] == "step_value"

    @pytest.mark.asyncio
    async def test_empty_steps_list_succeeds(self) -> None:
        executor = FlowExecutor()
        ctx = _make_context()
        # Should not raise
        await executor._execute_steps([], ctx)


class TestExecuteLoop:
    """Tests for FlowExecutor._execute_loop."""

    @pytest.mark.asyncio
    async def test_times_loop_runs_correct_count(self) -> None:
        executor = FlowExecutor()
        call_count = 0

        async def fake_execute_steps(
            steps: list[dict[str, Any]],
            context: StepContext,
            prefix: str = "",
        ) -> None:
            nonlocal call_count
            call_count += 1

        executor._execute_steps = fake_execute_steps  # type: ignore[method-assign]

        ctx = _make_context()
        await executor._execute_loop(
            loop_data={"type": "times", "iterations": 4, "steps": [{"type": "scroll"}]},
            context=ctx,
        )

        assert call_count == 4

    @pytest.mark.asyncio
    async def test_while_loop_stops_when_condition_false(self) -> None:
        executor = FlowExecutor()
        call_count = 0

        async def fake_execute_steps(
            steps: list[dict[str, Any]],
            context: StepContext,
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
                "condition": {"page": {"url_contains": "example.com"}},
                "max_iterations": 10,
                "steps": [],
            },
            context=ctx,
        )

        assert call_count == 0

    @pytest.mark.asyncio
    async def test_while_loop_respects_max_iterations(self) -> None:
        executor = FlowExecutor()
        call_count = 0

        async def fake_execute_steps(
            steps: list[dict[str, Any]],
            context: StepContext,
            prefix: str = "",
        ) -> None:
            nonlocal call_count
            call_count += 1

        executor._execute_steps = fake_execute_steps  # type: ignore[method-assign]

        # A true condition at the safety limit must fail.
        ctx = _make_context(url="https://example.com")
        with pytest.raises(RuntimeError, match="exhausted max_iterations=3"):
            await executor._execute_loop(
                loop_data={
                    "type": "while",
                    "condition": {"page": {"url_contains": "example.com"}},
                    "max_iterations": 3,
                    "steps": [],
                },
                context=ctx,
            )

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_times_zero_iterations(self) -> None:
        executor = FlowExecutor()
        call_count = 0

        async def fake_execute_steps(
            steps: list[dict[str, Any]],
            context: StepContext,
            prefix: str = "",
        ) -> None:
            nonlocal call_count
            call_count += 1

        executor._execute_steps = fake_execute_steps  # type: ignore[method-assign]

        ctx = _make_context()
        await executor._execute_loop(
            loop_data={"type": "times", "iterations": 0, "steps": []},
            context=ctx,
        )

        assert call_count == 0


class TestRuntimeExecution:
    async def test_while_reloads_results_with_local_scope_and_nested_if(self) -> None:
        executor = FlowExecutor()
        ctx = _make_context()
        ctx.runtime = RuntimeContext({"limit": 1})
        ctx.runtime.publish("count", 0)
        page = cast(MagicMock, ctx.page)
        page.evaluate = AsyncMock(side_effect=[1, 2, True, 3])
        await executor._execute_steps(
            [
                {
                    "type": "loop",
                    "variables": {"limit": 3},
                    "while": {"not": {"eq": ["{{results.count}}", "{{limit}}"]}},
                    "max_iterations": 5,
                    "steps": [
                        {"type": "evaluate", "script": "n => n + 1", "args": "{{results.count}}", "save_as": "count"},
                        {
                            "type": "if",
                            "condition": {"eq": ["{{results.count}}", 2]},
                            "then": [{"type": "evaluate", "script": "() => true", "save_as": "matched"}],
                        },
                    ],
                }
            ],
            ctx,
        )
        assert ctx.runtime.snapshot_results() == {"count": 3, "matched": True}
        assert [call.args[1]["args"] for call in page.evaluate.await_args_list] == [0, 1, None, 2]
        assert ctx.inputs["limit"] == 1

    async def test_if_short_circuit_is_not_resolved_during_step_preparation(self) -> None:
        ctx = _make_context()
        await FlowExecutor()._execute_steps(
            [
                {
                    "type": "if",
                    "condition": {
                        "all": [
                            {"exists": "{{results.missing}}"},
                            {"eq": ["{{results.missing.enabled}}", True]},
                        ]
                    },
                    "then": [{"type": "evaluate", "script": "() => true"}],
                }
            ],
            ctx,
        )
        cast(MagicMock, ctx.page).evaluate.assert_not_awaited()

    async def test_nested_results_are_resolved_when_children_execute(self) -> None:
        executor = FlowExecutor()
        ctx = _make_context()
        page = cast(MagicMock, ctx.page)
        page.evaluate = AsyncMock(side_effect=[[{"id": 7}], {"id": 7}, "{{literal}}"])
        steps: list[dict[str, Any]] = [
            {
                "type": "if",
                "condition": {"page": {"url_contains": "example.com"}},
                "then": [
                    {"type": "evaluate", "script": "() => [{id: 7}]", "save_as": "records"},
                    {
                        "type": "evaluate",
                        "script": "record => record",
                        "args": "{{results.records[0]}}",
                        "save_as": "selected",
                    },
                ],
                "else": [{"type": "evaluate", "script": "x => x", "args": "{{results.never}}"}],
            },
            {"type": "evaluate", "script": "() => '{{literal}}'", "args": "{{results.selected.id}}"},
        ]
        await executor._execute_steps(steps, ctx)
        payloads = [call.args[1] for call in page.evaluate.await_args_list]
        assert payloads[1]["args"] == {"id": 7}
        assert payloads[2]["args"] == 7
        assert payloads[2]["script"] == "() => '{{literal}}'"
        assert ctx.runtime.snapshot_results() == {"records": [{"id": 7}], "selected": {"id": 7}}

    async def test_loop_reads_previous_binding_and_replaces_it(self) -> None:
        executor = FlowExecutor()
        ctx = _make_context()
        page = cast(MagicMock, ctx.page)
        ctx.runtime.publish("count", 0)
        page.evaluate = AsyncMock(side_effect=[1, 2, 3])
        await executor._execute_steps(
            [
                {
                    "type": "loop",
                    "times": 3,
                    "steps": [
                        {
                            "type": "evaluate",
                            "script": "count => count + 1",
                            "args": "{{results.count}}",
                            "save_as": "count",
                        }
                    ],
                }
            ],
            ctx,
        )
        assert [call.args[1]["args"] for call in page.evaluate.await_args_list] == [0, 1, 2]
        assert ctx.runtime.snapshot_results() == {"count": 3}

    async def test_lexical_scopes_and_cli_precedence(self) -> None:
        executor = FlowExecutor()
        ctx = _make_context()
        page = cast(MagicMock, ctx.page)
        ctx.runtime = RuntimeContext({"key": "flow", "flow": 0}, {"cli": "override"}, {"key": "row"})
        page.evaluate = AsyncMock(return_value=None)
        steps: list[dict[str, Any]] = [
            {
                "type": "if",
                "condition": {"page": {"url_contains": "example.com"}},
                "variables": {"key": "parent"},
                "then": [
                    {"type": "evaluate", "script": "x => x", "args": "{{key}}", "variables": {"key": "child"}},
                    {"type": "evaluate", "script": "x => x", "args": "{{key}}"},
                    {"type": "evaluate", "script": "x => x", "args": "{{cli}}", "variables": {"cli": "local"}},
                ],
            },
            {"type": "evaluate", "script": "x => x", "args": "{{key}}"},
        ]
        await executor._execute_steps(steps, ctx)
        assert [call.args[1]["args"] for call in page.evaluate.await_args_list] == [
            "child",
            "parent",
            "override",
            "row",
        ]
        assert ctx.inputs == {"key": "row", "flow": 0, "cli": "override"}

    @pytest.mark.parametrize("failure", ["params", "exception", "output", "failure"])
    async def test_failure_invalidates_old_result(self, failure: str) -> None:
        executor = FlowExecutor()
        ctx = _make_context()
        page = cast(MagicMock, ctx.page)
        ctx.runtime.publish("record", {"old": True})
        step: dict[str, Any] = {"type": "evaluate", "script": "() => null", "save_as": "record"}
        if failure == "params":
            step["args"] = "{{missing}}"
        elif failure == "exception":
            page.evaluate = AsyncMock(side_effect=RuntimeError("JS failure"))
        elif failure == "output":
            page.evaluate = AsyncMock(return_value=float("nan"))
        else:
            with patch.object(EvaluateStep, "execute", new=AsyncMock(return_value=StepResult(success=False))):
                result = await executor._execute_step(step, ctx, "1", 1)
            assert not result.success
            assert ctx.runtime.snapshot_results() == {}
            return
        with pytest.raises((ValueError, RuntimeError)):
            await executor._execute_step(step, ctx, "1", 1)
        assert ctx.runtime.snapshot_results() == {}

    async def test_retry_publishes_only_final_success(self) -> None:
        executor = FlowExecutor()
        ctx = _make_context()
        page = cast(MagicMock, ctx.page)
        ctx.runtime.publish("record", 1)
        page.evaluate = AsyncMock(side_effect=[RuntimeError("transient"), 2])
        with patch.object(ctx.runtime, "publish", wraps=ctx.runtime.publish) as publish:
            await executor._execute_step(
                {
                    "type": "evaluate",
                    "script": "x => x + 1",
                    "args": "{{results.record}}",
                    "save_as": "record",
                    "retry": 1,
                    "retry_delay": 0,
                },
                ctx,
                "1",
                1,
            )
            publish.assert_called_once_with("record", 2)
        assert [call.args[1]["args"] for call in page.evaluate.await_args_list] == [1, 1]

    async def test_parameter_mutation_does_not_change_stored_result(self) -> None:
        executor = FlowExecutor()
        ctx = _make_context()
        ctx.runtime.publish("record", {"id": 1})

        async def mutate(self: EvaluateStep, context: StepContext, params: dict[str, Any]) -> StepResult:
            params["args"]["id"] = 2
            return StepResult(success=True, output=params["args"])

        with patch.object(EvaluateStep, "execute", new=mutate):
            await executor._execute_step(
                {"type": "evaluate", "script": "x => x", "args": "{{results.record}}", "save_as": "new"}, ctx, "1", 1
            )
        assert ctx.runtime.snapshot_results() == {"record": {"id": 1}, "new": {"id": 2}}
