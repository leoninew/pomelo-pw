"""Explicit business expectations using the shared condition contract."""

from __future__ import annotations

import json
from typing import Any

from pomelo_pw.conditions import evaluate_condition, validate_condition
from pomelo_pw.steps.base import BaseStep, StepContext, StepResult, StepSpec, register_step


class AssertionFailed(RuntimeError):
    def __init__(self, message: str, condition: Any, observed: list[dict[str, Any]]) -> None:
        self.diagnostics = {"assertion": {"condition": condition, "observed": observed}}
        values = json.dumps(observed, ensure_ascii=False, allow_nan=False)
        super().__init__(f"{message}; observed={values[:2000]}")


@register_step
class AssertStep(BaseStep):
    spec = StepSpec(
        name="assert",
        description="Require a structured condition and report observed values on failure",
        required_params=["condition"],
        optional_params={"message": "Assertion failed"},
        literal_params=("condition",),
    )

    @classmethod
    def validate_params(cls, params: dict[str, Any]) -> list[str]:
        errors = super().validate_params(params)
        if "condition" in params:
            errors.extend(validate_condition(params["condition"]))
        if "message" in params and (not isinstance(params["message"], str) or not params["message"].strip()):
            errors.append("message must be a non-empty string")
        return errors

    async def execute(self, context: StepContext, params: dict[str, Any]) -> StepResult:
        observed: list[dict[str, Any]] = []
        if not await evaluate_condition(context, params["condition"], observations=observed):
            raise AssertionFailed(params.get("message", "Assertion failed"), params["condition"], observed)
        return StepResult(success=True, message="Assertion passed")
