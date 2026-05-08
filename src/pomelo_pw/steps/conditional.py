"""Conditional execution step."""

from __future__ import annotations

from typing import Any

import click
from playwright.async_api import Page

from pomelo_pw.steps.base import BaseStep, StepContext, StepResult, StepSpec, register_step


@register_step
class ConditionalStep(BaseStep):
    """Execute steps conditionally based on expression evaluation."""

    spec = StepSpec(
        name="if",
        description="Execute steps conditionally",
        required_params=["condition", "then"],
        optional_params={
            "else": None,
        },
        aliases=["conditional"],
    )

    async def execute(self, context: StepContext, params: dict[str, Any]) -> StepResult:
        """Execute conditional logic."""
        condition = params["condition"]
        then_steps = params["then"]
        else_steps = params.get("else")

        # Evaluate condition
        try:
            result = await self._evaluate_condition(context.page, condition)
        except Exception as e:
            return StepResult(
                success=False,
                message=f"Failed to evaluate condition: {e}",
            )

        if result:
            click.echo(f"Condition '{condition}' is true, executing 'then' branch")
            return StepResult(
                success=True,
                message=f"Condition true: {condition}",
                data={"branch": "then", "steps": then_steps},
            )
        else:
            if else_steps:
                click.echo(f"Condition '{condition}' is false, executing 'else' branch")
                return StepResult(
                    success=True,
                    message=f"Condition false: {condition}",
                    data={"branch": "else", "steps": else_steps},
                )
            else:
                click.echo(f"Condition '{condition}' is false, skipping")
                return StepResult(
                    success=True,
                    message=f"Condition false, no else branch: {condition}",
                    data={"branch": "skip"},
                )

    async def _evaluate_condition(self, page: Page, condition: str) -> bool:
        """Evaluate condition expression.
        
        Supports:
        - element_exists: selector
        - element_visible: selector
        - element_hidden: selector
        - url_contains: text
        - url_matches: pattern
        - text_contains: text
        - JavaScript expressions
        """
        # Parse condition type
        if ":" in condition:
            cond_type, cond_value = condition.split(":", 1)
            cond_type = cond_type.strip()
            cond_value = cond_value.strip()

            if cond_type == "element_exists":
                element = await page.query_selector(cond_value)
                return element is not None

            elif cond_type == "element_visible":
                element = await page.query_selector(cond_value)
                if element is None:
                    return False
                return await element.is_visible()

            elif cond_type == "element_hidden":
                element = await page.query_selector(cond_value)
                if element is None:
                    return True
                return not await element.is_visible()

            elif cond_type == "url_contains":
                return cond_value in page.url

            elif cond_type == "url_matches":
                import re
                return bool(re.search(cond_value, page.url))

            elif cond_type == "text_contains":
                content = await page.content()
                return cond_value in content

            else:
                raise ValueError(f"Unknown condition type: {cond_type}")

        # Fallback: evaluate as JavaScript expression
        result = await page.evaluate(f"() => {{ return Boolean({condition}); }}")
        return bool(result)
