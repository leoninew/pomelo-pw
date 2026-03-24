"""Navigate step."""

from __future__ import annotations

from typing import Any, Literal

from pomelo_pw.steps.base import BaseStep, StepContext, StepResult, StepSpec, register_step

WaitUntil = Literal["load", "domcontentloaded", "networkidle", "commit"]


@register_step
class NavigateStep(BaseStep):
    """Navigate to URL."""

    spec = StepSpec(
        name="navigate",
        description="Navigate to a URL",
        required_params=["url"],
        optional_params={
            "timeout": 30000,
            "wait_until": "load",
            "wait_for_selector": None,
        },
    )

    async def execute(self, context: StepContext, params: dict[str, Any]) -> StepResult:
        """Execute navigate step."""
        url = params["url"]
        timeout = params.get("timeout", self.spec.optional_params["timeout"])
        wait_until: WaitUntil = params.get("wait_until", self.spec.optional_params["wait_until"])
        wait_for_selector = params.get("wait_for_selector", self.spec.optional_params["wait_for_selector"])

        if not url.startswith(("http://", "https://")):
            return StepResult(
                success=False,
                message=f"Invalid URL: {url}. Must start with http:// or https://",
            )

        await context.page.goto(url, timeout=timeout, wait_until=wait_until)

        # Wait for specific selector if provided
        if wait_for_selector:
            await context.page.wait_for_selector(wait_for_selector, timeout=timeout)

        return StepResult(success=True, message=f"Navigated to {url}")
