"""Execute a browser function with a structured argument payload."""

from __future__ import annotations

import json
from typing import Any

from playwright.async_api import ConsoleMessage

from pomelo_pw.runtime import snapshot_json, validate_json
from pomelo_pw.steps.base import BaseStep, StepContext, StepResult, StepSpec, register_step

CALL_FUNCTION = """async ({script, hasArgs, args}) => {
    const fn = (0, eval)('(' + script + '\\n)');
    if (typeof fn !== 'function') {
        throw new Error('evaluate.script must be a function expression');
    }
    const result = hasArgs ? await fn(args) : await fn();
    const ancestors = new Set();
    const validate = (value, path) => {
        if (value === null || typeof value === 'string' || typeof value === 'boolean') return;
        if (typeof value === 'number' && Number.isFinite(value)) return;
        if (typeof value !== 'object') throw new Error(path + ': unsupported JSON value');
        if (!Array.isArray(value) && Object.getPrototypeOf(value) !== Object.prototype
            && Object.getPrototypeOf(value) !== null) throw new Error(path + ': expected a JSON object');
        if (ancestors.has(value)) throw new Error(path + ': circular data is not supported');
        if (Object.getOwnPropertySymbols(value).length) throw new Error(path + ': symbol keys are not supported');
        ancestors.add(value);
        if (Array.isArray(value)) {
            for (let i = 0; i < value.length; i++) validate(value[i], path + '[' + i + ']');
        } else {
            for (const key of Object.keys(value)) validate(value[key], path + '.' + key);
        }
        ancestors.delete(value);
    };
    validate(result, 'output');
    return result;
}"""


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

        payload = {
            "script": script,
            "hasArgs": "args" in params,
            "args": snapshot_json(params.get("args")),
        }
        context.page.on("console", collect_console)
        try:
            result = snapshot_json(await context.page.evaluate(CALL_FUNCTION, payload))
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
