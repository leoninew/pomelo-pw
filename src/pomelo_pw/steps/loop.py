"""Loop execution step."""

from __future__ import annotations

from typing import Any

import click

from pomelo_pw.conditions import validate_condition
from pomelo_pw.steps.base import BaseStep, StepContext, StepResult, StepSpec, register_step
from pomelo_pw.substitution import validate_reference


@register_step
class LoopStep(BaseStep):
    """Execute steps in a loop."""

    spec = StepSpec(
        name="loop",
        description="Execute steps multiple times",
        required_params=["steps"],
        optional_params={
            "times": None,
            "while": None,
            "max_iterations": 100,  # Safety limit
        },
        aliases=["repeat"],
        child_step_params=("steps",),
        literal_params=("while",),
    )

    @classmethod
    def validate_params(cls, params: dict[str, Any]) -> list[str]:
        errors = super().validate_params(params)
        modes = [key for key in ("times", "while") if key in params]
        if len(modes) != 1:
            errors.append("Must specify exactly one of 'times' or 'while'")
        if "times" in params and "max_iterations" in params:
            errors.append("max_iterations is only allowed with 'while'")
        for key, minimum in (("times", 0), ("max_iterations", 1)):
            if key not in params:
                continue
            value = params[key]
            if isinstance(value, str):
                try:
                    validate_reference(value)
                    continue
                except ValueError:
                    pass
            if type(value) is not int or value < minimum:
                errors.append(f"{key} must be an integer >= {minimum} or a complete reference")
        if "while" in params:
            errors.extend(validate_condition(params["while"], "while"))
        if "steps" in params and not isinstance(params["steps"], list):
            errors.append("steps must be a list of steps")
        return errors

    @classmethod
    def validate_resolved_params(cls, params: dict[str, Any]) -> list[str]:
        errors = super().validate_resolved_params(params)
        for key, minimum in (("times", 0), ("max_iterations", 1)):
            if key in params and (type(params[key]) is not int or params[key] < minimum):
                errors.append(f"{key} must resolve to an integer >= {minimum}")
        return errors

    async def execute(self, context: StepContext, params: dict[str, Any]) -> StepResult:
        """Execute loop logic."""
        errors = self.validate_resolved_params(params)
        if errors:
            return StepResult(success=False, message="; ".join(errors))
        steps = params["steps"]
        times = params.get("times")
        while_condition = params.get("while")
        max_iterations = params.get("max_iterations", self.spec.optional_params["max_iterations"])

        if times is not None:
            # Fixed iteration count
            click.echo(f"Loop: executing {times} times")
            return StepResult(
                success=True,
                message=f"Loop: {times} iterations",
                control={"type": "times", "iterations": times, "steps": steps},
            )

        click.echo(f"Loop: while '{while_condition}' (max: {max_iterations})")
        return StepResult(
            success=True,
            message=f"Loop: while '{while_condition}'",
            control={
                "type": "while",
                "condition": while_condition,
                "max_iterations": max_iterations,
                "steps": steps,
            },
        )
