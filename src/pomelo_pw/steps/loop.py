"""Loop execution step."""

from __future__ import annotations

from typing import Any

import click

from pomelo_pw.steps.base import BaseStep, StepContext, StepResult, StepSpec, register_step


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
        aliases=["repeat", "foreach"],
    )

    async def execute(self, context: StepContext, params: dict[str, Any]) -> StepResult:
        """Execute loop logic."""
        steps = params["steps"]
        times = params.get("times")
        while_condition = params.get("while")
        max_iterations = params.get("max_iterations", self.spec.optional_params["max_iterations"])

        if times is not None and while_condition is not None:
            return StepResult(
                success=False,
                message="Cannot specify both 'times' and 'while' parameters",
            )

        if times is None and while_condition is None:
            return StepResult(
                success=False,
                message="Must specify either 'times' or 'while' parameter",
            )

        if times is not None:
            # Fixed iteration count
            click.echo(f"Loop: executing {times} times")
            return StepResult(
                success=True,
                message=f"Loop: {times} iterations",
                data={"type": "times", "iterations": times, "steps": steps},
            )

        elif while_condition is not None:
            # Conditional loop
            click.echo(f"Loop: while '{while_condition}' (max: {max_iterations})")
            return StepResult(
                success=True,
                message=f"Loop: while '{while_condition}'",
                data={
                    "type": "while",
                    "condition": while_condition,
                    "max_iterations": max_iterations,
                    "steps": steps,
                },
            )

        return StepResult(success=False, message="Invalid loop configuration")
