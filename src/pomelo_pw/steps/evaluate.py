"""Evaluate step."""

from __future__ import annotations

from typing import Any

from pomelo_pw.steps.base import BaseStep, StepContext, StepResult, StepSpec, register_step


@register_step
class EvaluateStep(BaseStep):
    """Execute JavaScript."""

    spec = StepSpec(
        name="evaluate",
        description="Execute JavaScript in the browser",
        required_params=["script"],
        optional_params={},
    )

    async def execute(self, context: StepContext, params: dict[str, Any]) -> StepResult:
        """Execute evaluate step."""
        script = params["script"].strip()

        # Auto-wrap if not already a function expression
        if not (script.startswith("(") or script.startswith("function")):
            script = f"(() => {{ {script} }})()"

        result = await context.page.evaluate(script)
        return StepResult(
            success=True,
            message=f"Executed script: {script[:50]}...",
            data={"result": result},
        )
