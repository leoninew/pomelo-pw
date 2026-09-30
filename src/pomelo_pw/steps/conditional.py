"""Conditional execution step."""

from __future__ import annotations

from typing import Any

import click

from pomelo_pw.conditions import evaluate_condition, validate_condition
from pomelo_pw.steps.base import BaseStep, StepContext, StepResult, StepSpec, register_step


@register_step
class ConditionalStep(BaseStep):
    """Execute steps conditionally based on expression evaluation."""

    spec = StepSpec(
        name="if",
        description="Execute steps conditionally",
        required_params=["condition", "then"],
        optional_params={
            "else": None,
        },
        aliases=["conditional"],
        child_step_params=("then", "else"),
        literal_params=("condition",),
    )

    @classmethod
    def validate_params(cls, params: dict[str, Any]) -> list[str]:
        errors = super().validate_params(params)
        if "condition" in params:
            errors.extend(validate_condition(params["condition"]))
        return errors

    async def execute(self, context: StepContext, params: dict[str, Any]) -> StepResult:
        """Execute conditional logic."""
        condition = params["condition"]
        then_steps = params["then"]
        else_steps = params.get("else")

        # Evaluate condition
        try:
            result = await evaluate_condition(context, condition)
        except Exception as e:
            return StepResult(
                success=False,
                message=f"Failed to evaluate condition: {e}",
            )

        if result:
            click.echo(f"Condition '{condition}' is true, executing 'then' branch")
            return StepResult(
                success=True,
                message=f"Condition true: {condition}",
                control={"branch": "then", "steps": then_steps},
            )
        else:
            if else_steps:
                click.echo(f"Condition '{condition}' is false, executing 'else' branch")
                return StepResult(
                    success=True,
                    message=f"Condition false: {condition}",
                    control={"branch": "else", "steps": else_steps},
                )
            else:
                click.echo(f"Condition '{condition}' is false, skipping")
                return StepResult(
                    success=True,
                    message=f"Condition false, no else branch: {condition}",
                    control={"branch": "skip"},
                )
