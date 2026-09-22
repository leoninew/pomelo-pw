"""Select step."""

from __future__ import annotations

from typing import Any

from pomelo_pw.steps.base import BaseStep, StepContext, StepResult, StepSpec, register_step


@register_step
class SelectStep(BaseStep):
    """Select option in dropdown."""

    spec = StepSpec(
        name="select",
        description="Select a dropdown option by value, visible label, or zero-based index (choose one)",
        required_params=["selector"],
        optional_params={"value": None, "label": None, "index": None, "timeout": 30000},
    )

    @classmethod
    def validate_params(cls, params: dict[str, Any]) -> list[str]:
        """Require exactly one supported option selector."""
        errors = super().validate_params(params)
        has_value = params.get("value") is not None
        has_label = params.get("label") is not None
        has_index = params.get("index") is not None
        if sum((has_value, has_label, has_index)) != 1:
            errors.append("Provide exactly one of: value, label, index")
        elif has_index and (
            not isinstance(params["index"], int) or isinstance(params["index"], bool) or params["index"] < 0
        ):
            errors.append("Parameter 'index' must be a non-negative integer")
        return errors

    async def execute(self, context: StepContext, params: dict[str, Any]) -> StepResult:
        """Execute select step."""
        selector = params["selector"]
        timeout = params.get("timeout", self.spec.optional_params["timeout"])
        value = params.get("value")
        label = params.get("label")
        index = params.get("index")

        if value is not None:
            await context.page.select_option(selector, value, timeout=timeout)
            selected = value
        elif label is not None:
            await context.page.select_option(selector, label=label, timeout=timeout)
            selected = label
        else:
            await context.page.select_option(selector, index=index, timeout=timeout)
            selected = f"index {index}"
        return StepResult(success=True, message=f"Selected '{selected}' in {selector}")
