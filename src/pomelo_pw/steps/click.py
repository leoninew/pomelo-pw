"""Click step."""

from __future__ import annotations

import asyncio
from typing import Any

from pomelo_pw.steps.base import BaseStep, StepContext, StepResult, StepSpec, register_step


@register_step
class ClickStep(BaseStep):
    """Click on an element."""

    spec = StepSpec(
        name="click",
        description="Click on an element",
        required_params=["selector"],
        optional_params={
            "button": "left",
            "click_count": 1,
            "timeout": 30000,
            "force": False,
            "wait_after": None,
            "wait_after_delay": 1000,  # Only used when wait_after="delay"
            "wait_after_timeout": 30000,
        },
    )

    @classmethod
    def validate_params(cls, params: dict[str, Any]) -> list[str]:
        """Validate parameters."""
        errors = super().validate_params(params)

        wait_after = params.get("wait_after")
        if wait_after is not None:
            valid_values = {"navigation", "reload", "network_idle", "load", "domcontentloaded", "delay"}
            if wait_after not in valid_values:
                errors.append(f"Invalid wait_after value: {wait_after}. Must be one of: {', '.join(valid_values)}")

        return errors

    async def execute(self, context: StepContext, params: dict[str, Any]) -> StepResult:
        """Execute click step."""
        selector = params["selector"]
        button = params.get("button", self.spec.optional_params["button"])
        click_count = params.get("click_count", self.spec.optional_params["click_count"])
        timeout = params.get("timeout", self.spec.optional_params["timeout"])
        force = params.get("force", self.spec.optional_params["force"])
        wait_after = params.get("wait_after", self.spec.optional_params["wait_after"])
        wait_after_timeout = params.get("wait_after_timeout", self.spec.optional_params["wait_after_timeout"])

        async def click_element() -> None:
            await context.page.click(
                selector,
                button=button,
                click_count=click_count,
                timeout=timeout,
                force=force,
            )

        if wait_after in ("navigation", "reload"):
            async with context.page.expect_navigation(timeout=wait_after_timeout):
                await click_element()
        else:
            await click_element()
            if wait_after == "network_idle":
                await context.page.wait_for_load_state("networkidle", timeout=wait_after_timeout)
            elif wait_after in ("load", "domcontentloaded"):
                await context.page.wait_for_load_state(wait_after, timeout=wait_after_timeout)
            elif wait_after == "delay":
                delay = params.get("wait_after_delay", self.spec.optional_params["wait_after_delay"])
                await asyncio.sleep(delay / 1000)

        message = f"Clicked: {selector}"
        if wait_after:
            message += f"; waited after click: {wait_after}"
        return StepResult(success=True, message=message)
