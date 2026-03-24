"""Uncheck step."""

from __future__ import annotations

from typing import Any

from pomelo_pw.steps.base import BaseStep, StepContext, StepResult, StepSpec, register_step


@register_step
class UncheckStep(BaseStep):
    """Uncheck a checkbox."""

    spec = StepSpec(
        name="uncheck",
        description="Uncheck a checkbox",
        required_params=["selector"],
        optional_params={"timeout": 30000},
    )

    async def execute(self, context: StepContext, params: dict[str, Any]) -> StepResult:
        """Execute uncheck step."""
        selector = params["selector"]
        timeout = params.get("timeout", self.spec.optional_params["timeout"])

        await context.page.uncheck(selector, timeout=timeout)
        return StepResult(success=True, message=f"Unchecked {selector}")
