"""Bounded serial polling with refreshed runtime results."""

from __future__ import annotations

import math
from typing import Any

from pomelo_pw.conditions import validate_condition
from pomelo_pw.steps.base import BaseStep, StepContext, StepResult, StepSpec, register_step
from pomelo_pw.substitution import validate_reference


@register_step
class PollStep(BaseStep):
    spec = StepSpec(
        name="poll",
        description="Execute query steps until a condition is true within one deadline",
        required_params=["until", "steps"],
        optional_params={"timeout": 30000, "interval": 1000, "max_attempts": None},
        produces_output=True,
        child_step_params=("steps",),
        literal_params=("until",),
    )

    @classmethod
    def _validate_bounds(cls, params: dict[str, Any], *, resolved: bool) -> list[str]:
        errors = []
        for key in ("timeout", "interval", "max_attempts"):
            if key not in params:
                continue
            value = params[key]
            if not resolved and isinstance(value, str):
                try:
                    validate_reference(value)
                    continue
                except ValueError:
                    pass
            valid = (
                type(value) is int and value > 0
                if key == "max_attempts"
                else isinstance(value, (int, float))
                and not isinstance(value, bool)
                and math.isfinite(value)
                and value > 0
            )
            if not valid:
                kind = "positive integer" if key == "max_attempts" else "finite positive number"
                suffix = "" if resolved else " or a complete reference"
                errors.append(f"{key} must {'resolve to' if resolved else 'be'} a {kind}{suffix}")
        return errors

    @classmethod
    def validate_params(cls, params: dict[str, Any]) -> list[str]:
        errors = super().validate_params(params)
        if "until" in params:
            errors.extend(validate_condition(params["until"], "until"))
        if "steps" in params and (not isinstance(params["steps"], list) or not params["steps"]):
            errors.append("steps must be a non-empty list of steps")
        for key in ("retry", "retry_delay", "retry_on"):
            if key in params:
                errors.append(f"poll does not allow {key}; declare retries on individual query steps")
        errors.extend(cls._validate_bounds(params, resolved=False))
        return errors

    @classmethod
    def validate_resolved_params(cls, params: dict[str, Any]) -> list[str]:
        return [*super().validate_resolved_params(params), *cls._validate_bounds(params, resolved=True)]

    async def execute(self, context: StepContext, params: dict[str, Any]) -> StepResult:
        errors = self.validate_resolved_params(params)
        if errors:
            return StepResult(success=False, message="; ".join(errors))
        return StepResult(
            success=True,
            message="Poll prepared",
            control={
                "type": "poll",
                "until": params["until"],
                "steps": params["steps"],
                "timeout": params.get("timeout", 30000),
                "interval": params.get("interval", 1000),
                "max_attempts": params.get("max_attempts"),
            },
        )
