"""Set viewport step."""

from __future__ import annotations

from typing import Any

from pomelo_pw.steps.base import BaseStep, StepContext, StepResult, StepSpec, register_step


@register_step
class SetViewportStep(BaseStep):
    """Set viewport size."""

    spec = StepSpec(
        name="set-viewport",
        description="Set the viewport size",
        required_params=[],
        optional_params={
            "width": 1280,
            "height": 720,
        },
    )

    async def execute(self, context: StepContext, params: dict[str, Any]) -> StepResult:
        """Execute set-viewport step."""
        width = params.get("width", self.spec.optional_params["width"])
        height = params.get("height", self.spec.optional_params["height"])

        await context.page.set_viewport_size({"width": width, "height": height})
        return StepResult(success=True, message=f"Viewport set to {width}x{height}")
