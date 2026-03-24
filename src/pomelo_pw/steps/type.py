"""Type step."""

from __future__ import annotations

from typing import Any

from pomelo_pw.steps.base import BaseStep, StepContext, StepResult, StepSpec, register_step


@register_step
class TypeStep(BaseStep):
    """Type text into an element."""

    spec = StepSpec(
        name="type",
        description="Type text into an element character by character",
        required_params=["selector", "value"],
        optional_params={"delay": 0, "timeout": 30000},
    )

    async def execute(self, context: StepContext, params: dict[str, Any]) -> StepResult:
        """Execute type step."""
        selector = params["selector"]
        value = params["value"]
        delay = params.get("delay", self.spec.optional_params["delay"])
        timeout = params.get("timeout", self.spec.optional_params["timeout"])

        await context.page.type(selector, value, delay=delay, timeout=timeout)
        return StepResult(success=True, message=f"Typed '{value}' into {selector}")
