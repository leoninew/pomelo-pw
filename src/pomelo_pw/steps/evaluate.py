"""Evaluate step."""

from __future__ import annotations

import json
import re
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

        context.page.on("console", collect_console)
        try:
            if self._is_function_expression(script):
                result = await context.page.evaluate(script)
            else:
                result = await self._evaluate_module(context, script)
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

    def _is_function_expression(self, script: str) -> bool:
        """Return True when Playwright can evaluate script directly."""
        return script.startswith("(") or bool(re.match(r"^(async\s+)?function\b", script))

    async def _evaluate_module(self, context: StepContext, script: str) -> Any:
        """Evaluate script as a browser module so top-level await is supported."""
        return await context.page.evaluate(
            """async (script) => {
                const moduleScript = document.createElement('script');
                const doneName = `__pomeloEvaluateDone_${Date.now()}_${Math.random().toString(16).slice(2)}`;

                return await new Promise((resolve, reject) => {
                    const cleanup = () => {
                        delete globalThis[doneName];
                        moduleScript.remove();
                    };
                    globalThis[doneName] = ({result, error}) => {
                        cleanup();
                        if (error) {
                            reject(error);
                            return;
                        }
                        resolve(result);
                    };
                    moduleScript.onerror = (event) => {
                        cleanup();
                        reject(new Error(event.message || 'Failed to evaluate module script'));
                    };
                    moduleScript.type = 'module';
                    moduleScript.textContent = `
                        try {
                            let __pomeloEvaluateResult;
                            ${script}
                            globalThis[${JSON.stringify(doneName)}]({result: __pomeloEvaluateResult});
                        } catch (error) {
                            globalThis[${JSON.stringify(doneName)}]({error});
                        }
                    `;
                    document.head.appendChild(moduleScript);
                });
            }""",
            self._prepare_module_script(script),
        )

    def _prepare_module_script(self, script: str) -> str:
        """Convert the legacy trailing return form into a module result assignment."""
        match = re.search(r"return(?:\s+([\s\S]*?))?;?\s*$", script.rstrip())
        if match is None:
            return script
        expression = match.group(1) or "undefined"
        return f"{script[: match.start()]}__pomeloEvaluateResult = {expression};"

    def _format_value(self, value: Any) -> str:
        """Format values for concise CLI output."""
        try:
            formatted = json.dumps(value, ensure_ascii=False)
        except TypeError:
            formatted = repr(value)
        if len(formatted) > 500:
            return formatted[:497] + "..."
        return formatted
