"""Execute a browser function with a structured argument payload."""

from __future__ import annotations

import json
from typing import Any

from playwright.async_api import ConsoleMessage

from pomelo_pw.browser_functions import call_browser_function
from pomelo_pw.runtime import NO_OUTPUT, validate_json
from pomelo_pw.steps.base import BaseStep, StepContext, StepResult, StepSpec, register_step


@register_step
class EvaluateStep(BaseStep):
    spec = StepSpec(
        name="evaluate",
        description="Execute a browser function with structured args and optional save_as",
        required_params=["script"],
        optional_params={"args": None, "print_result": True, "print_console": True},
        produces_output=True,
        literal_params=("script",),
    )

    @classmethod
    def validate_params(cls, params: dict[str, Any]) -> list[str]:
        errors = super().validate_params(params)
        if "script" in params and (not isinstance(params["script"], str) or not params["script"].strip()):
            errors.append("script must be a non-empty function expression")
        if "args" in params:
            try:
                validate_json(params["args"], "args")
            except ValueError as error:
                errors.append(str(error))
        return errors

    async def execute(self, context: StepContext, params: dict[str, Any]) -> StepResult:
        script = params["script"].strip()
        console_messages: list[str] = []

        def collect_console(message: ConsoleMessage) -> None:
            console_messages.append(f"{message.type}: {message.text}")

        context.page.on("console", collect_console)
        try:
            result = await call_browser_function(context.page, script, params.get("args", NO_OUTPUT))
        finally:
            context.page.remove_listener("console", collect_console)

        message_parts = [f"Executed function: {script[:50]}..."]
        if params.get("print_result", self.spec.optional_params["print_result"]):
            message_parts.append(f"result={self._format_value(result)}")
        if console_messages and params.get("print_console", self.spec.optional_params["print_console"]):
            message_parts.append(f"console={self._format_value(console_messages)}")
        return StepResult(
            success=True,
            message="; ".join(message_parts),
            output=result,
            diagnostics={"console": console_messages},
        )

    def _format_value(self, value: Any) -> str:
        formatted = json.dumps(value, ensure_ascii=False)
        return formatted[:497] + "..." if len(formatted) > 500 else formatted
