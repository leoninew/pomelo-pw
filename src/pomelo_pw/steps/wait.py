"""Wait step."""

from __future__ import annotations

import asyncio
import re
from typing import Any

from pomelo_pw.steps.base import BaseStep, StepContext, StepResult, StepSpec, register_step


@register_step
class WaitStep(BaseStep):
    """Wait for various conditions or fixed delay."""

    spec = StepSpec(
        name="wait",
        description="Wait for conditions: selector, URL pattern, network idle, animations, or fixed delay",
        required_params=[],
        optional_params={
            # Selector-based wait
            "selector": None,
            "state": "visible",  # visible, attached, detached, hidden
            # URL-based wait
            "url": None,
            "url_contains": None,
            "url_pattern": None,
            # Load state wait
            "for": None,  # load, domcontentloaded, networkidle
            # Advanced wait conditions
            "network_idle": None,
            "animation_stable": None,
            "route_stable": None,
            "route_stable_duration": 500,  # ms
            # Fixed delay
            "delay": None,
            # Timeout
            "timeout": 30000,
        },
        aliases=["wait-for"],
    )

    async def execute(self, context: StepContext, params: dict[str, Any]) -> StepResult:
        """Execute wait step."""
        timeout = params.get("timeout", self.spec.optional_params["timeout"])
        delay_ms = params.get("delay")

        # Fixed delay (highest priority)
        if delay_ms is not None:
            await asyncio.sleep(delay_ms / 1000)
            return StepResult(success=True, message=f"Waited for {delay_ms}ms")

        # Selector wait
        selector = params.get("selector")
        if selector:
            state = params.get("state", self.spec.optional_params["state"])
            await context.page.wait_for_selector(selector, state=state, timeout=timeout)
            return StepResult(success=True, message=f"Waited for selector '{selector}' (state: {state})")

        # URL exact match
        url = params.get("url")
        if url:
            await context.page.wait_for_url(url, timeout=timeout)
            return StepResult(success=True, message=f"Waited for URL: {url}")

        # URL contains
        url_contains = params.get("url_contains")
        if url_contains:
            await self._wait_for_url_contains(context, url_contains, timeout)
            return StepResult(success=True, message=f"Waited for URL containing: {url_contains}")

        # URL pattern (regex)
        url_pattern = params.get("url_pattern")
        if url_pattern:
            pattern = re.compile(url_pattern)
            await context.page.wait_for_url(pattern, timeout=timeout)
            return StepResult(success=True, message=f"Waited for URL pattern: {url_pattern}")

        # Network idle
        network_idle = params.get("network_idle")
        if network_idle:
            await context.page.wait_for_load_state("networkidle", timeout=timeout)
            return StepResult(success=True, message="Waited for network idle")

        # Animation stable
        animation_stable = params.get("animation_stable")
        if animation_stable:
            await self._wait_for_animation_stable(context, timeout)
            return StepResult(success=True, message="Waited for animations to stabilize")

        # Route stable (URL doesn't change)
        route_stable = params.get("route_stable")
        if route_stable:
            duration = params.get("route_stable_duration", self.spec.optional_params["route_stable_duration"])
            await self._wait_for_route_stable(context, duration, timeout)
            return StepResult(success=True, message=f"Waited for route to stabilize ({duration}ms)")

        # Load state wait (for backward compatibility)
        wait_for = params.get("for")
        if wait_for:
            if wait_for in ("load", "domcontentloaded", "networkidle"):
                await context.page.wait_for_load_state(wait_for, timeout=timeout)
                return StepResult(success=True, message=f"Waited for load state: {wait_for}")
            return StepResult(success=False, message=f"Invalid 'for' value: {wait_for}")

        return StepResult(
            success=False,
            message=(
                "No wait condition specified. Use selector, url, url_contains,"
                " url_pattern, network_idle, animation_stable, route_stable, or delay"
            ),
        )

    async def _wait_for_url_contains(self, context: StepContext, substring: str, timeout: int) -> None:
        """Wait for URL to contain a substring."""

        async def check_url() -> bool:
            return substring in context.page.url

        await self._wait_for_condition(check_url, timeout, f"URL to contain '{substring}'")

    async def _wait_for_animation_stable(self, context: StepContext, timeout: int) -> None:
        """Wait for all CSS animations and transitions to complete."""
        await context.page.wait_for_function(
            """
            () => {
                const elements = document.querySelectorAll('*');
                return Array.from(elements).every(el => {
                    const style = getComputedStyle(el);
                    const hasAnimation = style.animationName !== 'none' && style.animationPlayState === 'running';
                    const hasTransition = style.transitionProperty !== 'none' && style.transitionDuration !== '0s';
                    return !hasAnimation && !hasTransition;
                });
            }
            """,
            timeout=timeout,
        )

    async def _wait_for_route_stable(self, context: StepContext, duration_ms: int, timeout: int) -> None:
        """Wait for URL to remain stable for a specified duration."""
        start_time = asyncio.get_event_loop().time()
        last_url = context.page.url
        stable_since = start_time

        while True:
            current_time = asyncio.get_event_loop().time()

            # Check timeout
            if (current_time - start_time) * 1000 > timeout:
                raise TimeoutError(f"Route did not stabilize within {timeout}ms")

            current_url = context.page.url

            # URL changed, reset stability timer
            if current_url != last_url:
                last_url = current_url
                stable_since = current_time

            # URL has been stable for required duration
            if (current_time - stable_since) * 1000 >= duration_ms:
                return

            # Check every 100ms
            await asyncio.sleep(0.1)

    async def _wait_for_condition(
        self,
        condition: Any,
        timeout: int,
        description: str,
    ) -> None:
        """Wait for a custom condition to be true."""
        start_time = asyncio.get_event_loop().time()

        while True:
            if await condition():
                return

            current_time = asyncio.get_event_loop().time()
            if (current_time - start_time) * 1000 > timeout:
                raise TimeoutError(f"Timeout waiting for {description}")

            await asyncio.sleep(0.1)
