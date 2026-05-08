"""Tests for loop step."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from pomelo_pw.steps.loop import LoopStep
from pomelo_pw.steps import get_step


class TestLoopStepRegistration:
    def test_registered_as_loop(self) -> None:
        assert get_step("loop") is LoopStep

    def test_registered_aliases(self) -> None:
        assert get_step("repeat") is LoopStep
        assert get_step("foreach") is LoopStep

    def test_missing_steps_param(self) -> None:
        errors = LoopStep.validate_params({"type": "loop"})
        assert any("steps" in e for e in errors)

    def test_valid_with_steps(self) -> None:
        errors = LoopStep.validate_params({"type": "loop", "steps": []})
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
        assert result.data is not None
        assert result.data["type"] == "times"
        assert result.data["iterations"] == 3
        assert result.data["steps"] == inner

    @pytest.mark.asyncio
    async def test_while_loop_returns_correct_data(self) -> None:
        ctx = self._make_context()
        step = LoopStep()
        inner = [{"type": "scroll", "direction": "down", "distance": 100}]
        result = await step.execute(ctx, {
            "type": "loop",
            "steps": inner,
            "while": "element_visible: .load-more",
            "max_iterations": 5,
        })
        assert result.success is True
        assert result.data is not None
        assert result.data["type"] == "while"
        assert result.data["condition"] == "element_visible: .load-more"
        assert result.data["max_iterations"] == 5

    @pytest.mark.asyncio
    async def test_both_times_and_while_fails(self) -> None:
        ctx = self._make_context()
        step = LoopStep()
        result = await step.execute(ctx, {
            "type": "loop",
            "steps": [],
            "times": 3,
            "while": "element_exists: h1",
        })
        assert result.success is False
        assert "Cannot specify both" in result.message

    @pytest.mark.asyncio
    async def test_neither_times_nor_while_fails(self) -> None:
        ctx = self._make_context()
        step = LoopStep()
        result = await step.execute(ctx, {"type": "loop", "steps": []})
        assert result.success is False
        assert "Must specify either" in result.message

    @pytest.mark.asyncio
    async def test_default_max_iterations(self) -> None:
        ctx = self._make_context()
        step = LoopStep()
        result = await step.execute(ctx, {
            "type": "loop",
            "steps": [],
            "while": "element_exists: h1",
        })
        assert result.success is True
        assert result.data is not None
        assert result.data["max_iterations"] == 100
