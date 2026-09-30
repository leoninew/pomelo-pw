"""Tests for conditional-step registration, validation and branch selection."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from pomelo_pw.runtime import RuntimeContext
from pomelo_pw.steps import get_step
from pomelo_pw.steps.base import StepContext
from pomelo_pw.steps.conditional import ConditionalStep


def _context(url: str = "https://example.com") -> StepContext:
    page = MagicMock()
    page.url = url
    page.locator.return_value.count = AsyncMock(return_value=1)
    return StepContext(page, RuntimeContext(), Path("/tmp/out"), [])


def test_registration_and_required_parameters() -> None:
    assert get_step("if") is ConditionalStep
    assert get_step("conditional") is ConditionalStep
    errors = ConditionalStep.validate_params({"type": "if"})
    assert any("condition" in error for error in errors)
    assert any("then" in error for error in errors)


def test_structured_condition_validation() -> None:
    assert (
        ConditionalStep.validate_params({"type": "if", "condition": {"page": {"element_exists": "h1"}}, "then": []})
        == []
    )
    assert ConditionalStep.validate_params({"condition": "element_exists: h1", "then": []})


@pytest.mark.parametrize(
    ("url", "else_steps", "branch"),
    [
        ("https://example.com", None, "then"),
        ("https://other.com", [{"type": "screenshot", "file": "b.png"}], "else"),
        ("https://other.com", None, "skip"),
    ],
)
async def test_branch_selection(url: str, else_steps: Any, branch: str) -> None:
    then_steps = [{"type": "screenshot", "file": "a.png"}]
    params = {"condition": {"page": {"url_contains": "example.com"}}, "then": then_steps}
    if else_steps is not None:
        params["else"] = else_steps
    result = await ConditionalStep().execute(_context(url), params)
    assert result.success
    assert result.control["branch"] == branch
    if branch != "skip":
        assert result.control["steps"] == (then_steps if branch == "then" else else_steps)


async def test_condition_error_returns_failure_with_node_path() -> None:
    context = _context()
    cast(MagicMock, context.page).locator.return_value.count = AsyncMock(side_effect=RuntimeError("page crashed"))
    result = await ConditionalStep().execute(context, {"condition": {"page": {"element_exists": "h1"}}, "then": []})
    assert not result.success
    assert "condition.page" in result.message
    assert "page crashed" in result.message
