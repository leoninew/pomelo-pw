"""Check step."""

from __future__ import annotations

from typing import Any

from pomelo_pw.steps.base import BaseStep, StepContext, StepResult, StepSpec, register_step


@register_step
class CheckStep(BaseStep):
    """Check a checkbox."""

    spec = StepSpec(
        name="check",
        description="Check a checkbox",
        required_params=["selector"],
        optional_params={"timeout": 30000},
    )

    async def execute(self, context: StepContext, params: dict[str, Any]) -> StepResult:
        """Execute check step."""
        selector = params["selector"]
        timeout = params.get("timeout", self.spec.optional_params["timeout"])

        await context.page.check(selector, timeout=timeout)
        return StepResult(success=True, message=f"Checked {selector}")
