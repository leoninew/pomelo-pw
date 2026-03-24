"""Select step."""

from __future__ import annotations

from typing import Any

from pomelo_pw.steps.base import BaseStep, StepContext, StepResult, StepSpec, register_step


@register_step
class SelectStep(BaseStep):
    """Select option in dropdown."""

    spec = StepSpec(
        name="select",
        description="Select an option in a dropdown",
        required_params=["selector", "value"],
        optional_params={"timeout": 30000},
    )

    async def execute(self, context: StepContext, params: dict[str, Any]) -> StepResult:
        """Execute select step."""
        selector = params["selector"]
        value = params["value"]
        timeout = params.get("timeout", self.spec.optional_params["timeout"])

        await context.page.select_option(selector, value, timeout=timeout)
        return StepResult(success=True, message=f"Selected '{value}' in {selector}")
