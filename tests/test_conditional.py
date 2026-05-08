"""Tests for conditional step."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from pomelo_pw.steps import get_step
from pomelo_pw.steps.conditional import ConditionalStep


class TestConditionalStepRegistration:
    def test_registered_as_if(self) -> None:
        assert get_step("if") is ConditionalStep

    def test_registered_alias(self) -> None:
        assert get_step("conditional") is ConditionalStep

    def test_required_params(self) -> None:
        errors = ConditionalStep.validate_params({"type": "if"})
        assert any("condition" in e for e in errors)
        assert any("then" in e for e in errors)

    def test_valid_params(self) -> None:
        errors = ConditionalStep.validate_params({"type": "if", "condition": "element_exists: h1", "then": []})
        assert len(errors) == 0


class TestConditionalStepEvaluate:
    """Tests for _evaluate_condition using a mock page."""

    def _make_page(self, **kwargs: Any) -> MagicMock:
        page = MagicMock()
        page.url = kwargs.get("url", "https://example.com/path")
        page.query_selector = AsyncMock(return_value=kwargs.get("element"))
        page.content = AsyncMock(return_value=kwargs.get("content", "<html><body>hello</body></html>"))
        page.evaluate = AsyncMock(return_value=kwargs.get("js_result", True))
        return page

    @pytest.mark.asyncio
    async def test_element_exists_found(self) -> None:
        element = MagicMock()
        page = self._make_page(element=element)
        step = ConditionalStep()
        assert await step._evaluate_condition(page, "element_exists: h1") is True

    @pytest.mark.asyncio
    async def test_element_exists_not_found(self) -> None:
        page = self._make_page(element=None)
        step = ConditionalStep()
        assert await step._evaluate_condition(page, "element_exists: .missing") is False

    @pytest.mark.asyncio
    async def test_element_visible_true(self) -> None:
        element = MagicMock()
        element.is_visible = AsyncMock(return_value=True)
        page = self._make_page(element=element)
        step = ConditionalStep()
        assert await step._evaluate_condition(page, "element_visible: .btn") is True

    @pytest.mark.asyncio
    async def test_element_visible_false(self) -> None:
        element = MagicMock()
        element.is_visible = AsyncMock(return_value=False)
        page = self._make_page(element=element)
        step = ConditionalStep()
        assert await step._evaluate_condition(page, "element_visible: .hidden") is False

    @pytest.mark.asyncio
    async def test_element_visible_no_element(self) -> None:
        page = self._make_page(element=None)
        step = ConditionalStep()
        assert await step._evaluate_condition(page, "element_visible: .missing") is False

    @pytest.mark.asyncio
    async def test_element_hidden_no_element(self) -> None:
        page = self._make_page(element=None)
        step = ConditionalStep()
        assert await step._evaluate_condition(page, "element_hidden: .missing") is True

    @pytest.mark.asyncio
    async def test_element_hidden_visible_element(self) -> None:
        element = MagicMock()
        element.is_visible = AsyncMock(return_value=True)
        page = self._make_page(element=element)
        step = ConditionalStep()
        assert await step._evaluate_condition(page, "element_hidden: .visible") is False

    @pytest.mark.asyncio
    async def test_url_contains_match(self) -> None:
        page = self._make_page(url="https://example.com/dashboard")
        step = ConditionalStep()
        assert await step._evaluate_condition(page, "url_contains: dashboard") is True

    @pytest.mark.asyncio
    async def test_url_contains_no_match(self) -> None:
        page = self._make_page(url="https://example.com/login")
        step = ConditionalStep()
        assert await step._evaluate_condition(page, "url_contains: dashboard") is False

    @pytest.mark.asyncio
    async def test_url_matches_pattern(self) -> None:
        page = self._make_page(url="https://example.com/user/42")
        step = ConditionalStep()
        assert await step._evaluate_condition(page, r"url_matches: /user/\d+") is True

    @pytest.mark.asyncio
    async def test_url_matches_no_match(self) -> None:
        page = self._make_page(url="https://example.com/login")
        step = ConditionalStep()
        assert await step._evaluate_condition(page, r"url_matches: /user/\d+") is False

    @pytest.mark.asyncio
    async def test_text_contains_match(self) -> None:
        page = self._make_page(content="<html><body>Welcome back!</body></html>")
        step = ConditionalStep()
        assert await step._evaluate_condition(page, "text_contains: Welcome") is True

    @pytest.mark.asyncio
    async def test_text_contains_no_match(self) -> None:
        page = self._make_page(content="<html><body>Login</body></html>")
        step = ConditionalStep()
        assert await step._evaluate_condition(page, "text_contains: Welcome") is False

    @pytest.mark.asyncio
    async def test_unknown_condition_type_raises(self) -> None:
        page = self._make_page()
        step = ConditionalStep()
        with pytest.raises(ValueError, match="Unknown condition type"):
            await step._evaluate_condition(page, "invalid_type: value")

    @pytest.mark.asyncio
    async def test_javascript_expression_true(self) -> None:
        page = self._make_page(js_result=True)
        step = ConditionalStep()
        assert await step._evaluate_condition(page, "1 === 1") is True

    @pytest.mark.asyncio
    async def test_javascript_expression_false(self) -> None:
        page = self._make_page(js_result=False)
        step = ConditionalStep()
        assert await step._evaluate_condition(page, "1 === 2") is False


class TestConditionalStepExecute:
    """Tests for execute() branching logic."""

    def _make_context(self, url: str = "https://example.com") -> MagicMock:
        ctx = MagicMock()
        ctx.page = MagicMock()
        ctx.page.url = url
        ctx.page.query_selector = AsyncMock(return_value=MagicMock())
        ctx.page.content = AsyncMock(return_value="<html></html>")
        ctx.page.evaluate = AsyncMock(return_value=True)
        return ctx

    @pytest.mark.asyncio
    async def test_then_branch_taken(self) -> None:
        ctx = self._make_context()
        step = ConditionalStep()
        then_steps = [{"type": "screenshot", "file": "a.png"}]
        result = await step.execute(
            ctx,
            {
                "type": "if",
                "condition": "url_contains: example.com",
                "then": then_steps,
            },
        )
        assert result.success is True
        assert result.data is not None
        assert result.data["branch"] == "then"
        assert result.data["steps"] == then_steps

    @pytest.mark.asyncio
    async def test_else_branch_taken(self) -> None:
        ctx = self._make_context(url="https://other.com")
        step = ConditionalStep()
        else_steps = [{"type": "screenshot", "file": "b.png"}]
        result = await step.execute(
            ctx,
            {
                "type": "if",
                "condition": "url_contains: example.com",
                "then": [],
                "else": else_steps,
            },
        )
        assert result.success is True
        assert result.data is not None
        assert result.data["branch"] == "else"
        assert result.data["steps"] == else_steps

    @pytest.mark.asyncio
    async def test_skip_when_false_no_else(self) -> None:
        ctx = self._make_context(url="https://other.com")
        step = ConditionalStep()
        result = await step.execute(
            ctx,
            {
                "type": "if",
                "condition": "url_contains: example.com",
                "then": [],
            },
        )
        assert result.success is True
        assert result.data is not None
        assert result.data["branch"] == "skip"

    @pytest.mark.asyncio
    async def test_condition_error_returns_failure(self) -> None:
        ctx = self._make_context()
        ctx.page.query_selector = AsyncMock(side_effect=RuntimeError("page crashed"))
        step = ConditionalStep()
        result = await step.execute(
            ctx,
            {
                "type": "if",
                "condition": "element_exists: h1",
                "then": [],
            },
        )
        assert result.success is False
        assert "Failed to evaluate condition" in result.message
