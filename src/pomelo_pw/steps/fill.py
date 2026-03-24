"""Fill step."""

from __future__ import annotations

from typing import Any

from pomelo_pw.steps.base import BaseStep, StepContext, StepResult, StepSpec, register_step


@register_step
class FillStep(BaseStep):
    """Fill a form field."""

    spec = StepSpec(
        name="fill",
        description="Fill a form field with a value",
        required_params=["selector", "value"],
        optional_params={"timeout": 30000},
    )

    async def execute(self, context: StepContext, params: dict[str, Any]) -> StepResult:
        """Execute fill step."""
        selector = params["selector"]
        value = params["value"]
        timeout = params.get("timeout", self.spec.optional_params["timeout"])

        await context.page.fill(selector, value, timeout=timeout)
        return StepResult(success=True, message=f"Filled {selector} with '{value}'")
