"""Scroll step."""

from __future__ import annotations

from typing import Any

from pomelo_pw.steps.base import BaseStep, StepContext, StepResult, StepSpec, register_step


@register_step
class ScrollStep(BaseStep):
    """Scroll the page."""

    spec = StepSpec(
        name="scroll",
        description="Scroll the page in a direction",
        required_params=[],
        optional_params={
            "direction": "down",
            "distance": 300,
        },
    )

    async def execute(self, context: StepContext, params: dict[str, Any]) -> StepResult:
        """Execute scroll step."""
        direction = params.get("direction", self.spec.optional_params["direction"])
        distance = params.get("distance", self.spec.optional_params["distance"])

        if direction == "down":
            await context.page.mouse.wheel(0, distance)
        elif direction == "up":
            await context.page.mouse.wheel(0, -distance)
        elif direction == "right":
            await context.page.mouse.wheel(distance, 0)
        elif direction == "left":
            await context.page.mouse.wheel(-distance, 0)
        else:
            return StepResult(success=False, message=f"Unknown direction: {direction}")

        return StepResult(success=True, message=f"Scrolled {direction} by {distance}px")
