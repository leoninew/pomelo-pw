"""Evaluate step."""

from __future__ import annotations

import json
from typing import Any

from playwright.async_api import ConsoleMessage

from pomelo_pw.steps.base import BaseStep, StepContext, StepResult, StepSpec, register_step


@register_step
class EvaluateStep(BaseStep):
    """Execute JavaScript."""

    spec = StepSpec(
        name="evaluate",
        description="Execute JavaScript in the browser",
        required_params=["script"],
        optional_params={
            "print_result": True,
            "print_console": True,
        },
    )

    async def execute(self, context: StepContext, params: dict[str, Any]) -> StepResult:
        """Execute evaluate step."""
        script = params["script"].strip()
        console_messages: list[str] = []

        def collect_console(message: ConsoleMessage) -> None:
            console_messages.append(f"{message.type}: {message.text}")

        # Auto-wrap if not already a function expression
        if not (script.startswith("(") or script.startswith("function")):
            script = f"(() => {{ {script} }})()"

        context.page.on("console", collect_console)
        try:
            result = await context.page.evaluate(script)
        finally:
            context.page.remove_listener("console", collect_console)

        message_parts = [f"Executed script: {script[:50]}..."]
        if params.get("print_result", self.spec.optional_params["print_result"]):
            message_parts.append(f"result={self._format_value(result)}")
        if console_messages and params.get("print_console", self.spec.optional_params["print_console"]):
            message_parts.append(f"console={self._format_value(console_messages)}")

        return StepResult(
            success=True,
            message="; ".join(message_parts),
            data={"result": result, "console": console_messages},
        )

    def _format_value(self, value: Any) -> str:
        """Format values for concise CLI output."""
        try:
            formatted = json.dumps(value, ensure_ascii=False)
        except TypeError:
            formatted = repr(value)
        if len(formatted) > 500:
            return formatted[:497] + "..."
        return formatted
