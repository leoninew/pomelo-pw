"""Wait step."""

from __future__ import annotations

import asyncio
from typing import Any

from pomelo_pw.steps.base import BaseStep, StepContext, StepResult, StepSpec, register_step


@register_step
class WaitStep(BaseStep):
    """Wait for a condition."""

    spec = StepSpec(
        name="wait",
        description="Wait for a condition (selector, url) or fixed delay",
        required_params=[],
        optional_params={
            "for": None,
            "selector": None,
            "url": None,
            "value": None,
            "timeout": 30000,
            "delay": None,
        },
        aliases=["wait-for"],
    )

    async def execute(self, context: StepContext, params: dict[str, Any]) -> StepResult:
        """Execute wait step."""
        wait_for = params.get("for", self.spec.optional_params["for"])
        selector = params.get("selector", self.spec.optional_params["selector"])
        url = params.get("url", self.spec.optional_params["url"])
        value = params.get("value", self.spec.optional_params["value"])
        timeout = params.get("timeout", self.spec.optional_params["timeout"])
        delay_ms = params.get("delay", self.spec.optional_params["delay"])

        # Wait for fixed delay (in milliseconds)
        if delay_ms is not None:
            await asyncio.sleep(delay_ms / 1000)
            return StepResult(success=True, message=f"Waited for {delay_ms}ms")

        # Wait for selector
        if selector:
            await context.page.wait_for_selector(selector, timeout=timeout)
            return StepResult(success=True, message=f"Waited for selector: {selector}")

        # Wait for URL (direct url param or for='url' with value)
        url_pattern = url or (value if wait_for == "url" else None)
        if url_pattern:
            await context.page.wait_for_url(url_pattern, timeout=timeout)
            return StepResult(success=True, message=f"Waited for URL: {url_pattern}")

        # Wait for load state
        if wait_for == "load":
            await context.page.wait_for_load_state("load", timeout=timeout)
            return StepResult(success=True, message="Waited for page load")

        if wait_for == "networkidle":
            await context.page.wait_for_load_state("networkidle", timeout=timeout)
            return StepResult(success=True, message="Waited for network idle")

        return StepResult(
            success=False,
            message="Invalid wait. Use 'selector', 'url', 'delay', or 'for' with url/load/networkidle",
        )
