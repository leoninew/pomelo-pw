"""Click step."""

from __future__ import annotations

from typing import Any

from pomelo_pw.steps.base import BaseStep, StepContext, StepResult, StepSpec, register_step


@register_step
class ClickStep(BaseStep):
    """Click on an element."""

    spec = StepSpec(
        name="click",
        description="Click on an element",
        required_params=["selector"],
        optional_params={
            "button": "left",
            "click_count": 1,
            "timeout": 30000,
            "force": False,
        },
    )

    async def execute(self, context: StepContext, params: dict[str, Any]) -> StepResult:
        """Execute click step."""
        selector = params["selector"]
        button = params.get("button", self.spec.optional_params["button"])
        click_count = params.get("click_count", self.spec.optional_params["click_count"])
        timeout = params.get("timeout", self.spec.optional_params["timeout"])
        force = params.get("force", self.spec.optional_params["force"])

        await context.page.click(
            selector,
            button=button,
            click_count=click_count,
            timeout=timeout,
            force=force,
        )
        return StepResult(success=True, message=f"Clicked: {selector}")
