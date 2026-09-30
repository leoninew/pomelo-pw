"""Tests for loop step."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pomelo_pw.steps import get_step
from pomelo_pw.steps.loop import LoopStep


class TestLoopStepRegistration:
    def test_registered_as_loop(self) -> None:
        assert get_step("loop") is LoopStep

    def test_registered_aliases(self) -> None:
        assert get_step("repeat") is LoopStep
        assert get_step("foreach") is not LoopStep

    def test_missing_steps_param(self) -> None:
        errors = LoopStep.validate_params({"type": "loop"})
        assert any("steps" in e for e in errors)

    def test_valid_with_steps(self) -> None:
        errors = LoopStep.validate_params({"type": "loop", "times": 0, "steps": []})
        assert len(errors) == 0


class TestLoopStepExecute:
    def _make_context(self) -> MagicMock:
        ctx = MagicMock()
        ctx.page = MagicMock()
        return ctx

    @pytest.mark.asyncio
    async def test_times_loop_returns_correct_data(self) -> None:
        ctx = self._make_context()
        step = LoopStep()
        inner = [{"type": "scroll", "direction": "down", "distance": 100}]
        result = await step.execute(ctx, {"type": "loop", "steps": inner, "times": 3})
        assert result.success is True
        assert result.control is not None
        assert result.control["type"] == "times"
        assert result.control["iterations"] == 3
        assert result.control["steps"] == inner

    @pytest.mark.asyncio
    async def test_while_loop_returns_correct_data(self) -> None:
        ctx = self._make_context()
        step = LoopStep()
        inner = [{"type": "scroll", "direction": "down", "distance": 100}]
        result = await step.execute(
            ctx,
            {
                "type": "loop",
                "steps": inner,
                "while": {"page": {"element_visible": ".load-more"}},
                "max_iterations": 5,
            },
        )
        assert result.success is True
        assert result.control is not None
        assert result.control["type"] == "while"
        assert result.control["condition"] == {"page": {"element_visible": ".load-more"}}
        assert result.control["max_iterations"] == 5

    @pytest.mark.asyncio
    async def test_both_times_and_while_fails(self) -> None:
        ctx = self._make_context()
        step = LoopStep()
        result = await step.execute(
            ctx,
            {
                "type": "loop",
                "steps": [],
                "times": 3,
                "while": {"page": {"element_exists": "h1"}},
            },
        )
        assert result.success is False
        assert "exactly one" in result.message

    @pytest.mark.asyncio
    async def test_neither_times_nor_while_fails(self) -> None:
        ctx = self._make_context()
        step = LoopStep()
        result = await step.execute(ctx, {"type": "loop", "steps": []})
        assert result.success is False
        assert "exactly one" in result.message

    @pytest.mark.asyncio
    async def test_default_max_iterations(self) -> None:
        ctx = self._make_context()
        result = await LoopStep().execute(
            ctx, {"type": "loop", "steps": [], "while": {"page": {"element_exists": "h1"}}}
        )
        assert result.success is True
        assert result.control["max_iterations"] == 100


@pytest.mark.parametrize(
    "field, value",
    [
        ("times", -1),
        ("times", True),
        ("times", 1.0),
        ("times", "3"),
        ("times", None),
        ("max_iterations", 0),
        ("max_iterations", False),
        ("max_iterations", "3"),
    ],
)
def test_invalid_counts(field: str, value: object) -> None:
    params = {"steps": [], "times": value} if field == "times" else {"steps": [], "while": {"eq": [1, 1]}, field: value}
    assert any(field in error for error in LoopStep.validate_params(params))


def test_count_and_condition_modes_reject_collection_parameters() -> None:
    assert LoopStep.validate_params({"steps": [], "times": 1, "items": []})
    assert LoopStep.validate_params({"steps": [], "times": 1, "max_iterations": 2})
    assert not LoopStep.validate_params({"steps": [], "times": "{{results.count}}"})
    assert LoopStep.validate_resolved_params({"steps": [], "times": "{{results.count}}"})
