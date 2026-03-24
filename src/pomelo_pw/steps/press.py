"""Press step."""

from __future__ import annotations

from typing import Any

from pomelo_pw.steps.base import BaseStep, StepContext, StepResult, StepSpec, register_step


@register_step
class PressStep(BaseStep):
    """Press a keyboard key."""

    spec = StepSpec(
        name="press",
        description="Press a keyboard key",
        required_params=["key"],
        optional_params={},
    )

    async def execute(self, context: StepContext, params: dict[str, Any]) -> StepResult:
        """Execute press step."""
        key = params["key"]
        await context.page.keyboard.press(key)
        return StepResult(success=True, message=f"Pressed key: {key}")
