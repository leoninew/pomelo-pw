"""Select step."""

from __future__ import annotations

from typing import Any

from pomelo_pw.steps.base import BaseStep, StepContext, StepResult, StepSpec, register_step


@register_step
class SelectStep(BaseStep):
    """Select option in dropdown."""

    spec = StepSpec(
        name="select",
        description="Select a dropdown option by value or visible label (choose one)",
        required_params=["selector"],
        optional_params={"value": None, "label": None, "timeout": 30000},
    )

    @classmethod
    def validate_params(cls, params: dict[str, Any]) -> list[str]:
        """Require exactly one supported option selector."""
        errors = super().validate_params(params)
        has_value = params.get("value") is not None
        has_label = params.get("label") is not None
        if has_value == has_label:
            errors.append("Provide exactly one of: value, label")
        return errors

    async def execute(self, context: StepContext, params: dict[str, Any]) -> StepResult:
        """Execute select step."""
        selector = params["selector"]
        timeout = params.get("timeout", self.spec.optional_params["timeout"])
        value = params.get("value")
        label = params.get("label")

        if value is not None:
            await context.page.select_option(selector, value, timeout=timeout)
            selected = value
        else:
            await context.page.select_option(selector, label=label, timeout=timeout)
            selected = label
        return StepResult(success=True, message=f"Selected '{selected}' in {selector}")
