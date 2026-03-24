"""Hover step."""

from __future__ import annotations

from typing import Any

from pomelo_pw.steps.base import BaseStep, StepContext, StepResult, StepSpec, register_step


@register_step
class HoverStep(BaseStep):
    """Hover over an element."""

    spec = StepSpec(
        name="hover",
        description="Hover over an element",
        required_params=["selector"],
        optional_params={"timeout": 30000},
    )

    async def execute(self, context: StepContext, params: dict[str, Any]) -> StepResult:
        """Execute hover step."""
        selector = params["selector"]
        timeout = params.get("timeout", self.spec.optional_params["timeout"])

        await context.page.hover(selector, timeout=timeout)
        return StepResult(success=True, message=f"Hovered over {selector}")
