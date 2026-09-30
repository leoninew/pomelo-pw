"""Wait step."""

from __future__ import annotations

import asyncio
import math
import re
from typing import Any

from pomelo_pw.conditions import validate_condition, wait_for_condition
from pomelo_pw.steps.base import BaseStep, StepContext, StepResult, StepSpec, register_step
from pomelo_pw.substitution import REFERENCE, validate_reference

WAIT_MODES = (
    "condition",
    "delay",
    "selector",
    "url",
    "url_contains",
    "url_pattern",
    "for",
    "network_idle",
    "animation_stable",
    "route_stable",
)


def _has_reference(value: Any) -> bool:
    return isinstance(value, str) and any(match.group(1) is not None for match in REFERENCE.finditer(value))


@register_step
class WaitStep(BaseStep):
    """Wait for various conditions or fixed delay."""

    spec = StepSpec(
        name="wait",
        description="Wait for conditions: selector, URL pattern, network idle, animations, or fixed delay",
        required_params=[],
        optional_params={
            "condition": None,
            "interval": 100,
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
        literal_params=("condition",),
    )

    @classmethod
    def validate_params(cls, params: dict[str, Any]) -> list[str]:
        errors = super().validate_params(params)
        modes = [key for key in WAIT_MODES if key in params]
        if len(modes) != 1:
            errors.append("Wait requires exactly one mode: " + ", ".join(WAIT_MODES))
        for key, mode in (("state", "selector"), ("route_stable_duration", "route_stable"), ("interval", "condition")):
            if key in params and mode not in params:
                errors.append(f"{key} is only allowed with {mode}")
        if "condition" in params:
            errors.extend(validate_condition(params["condition"]))
        for key in ("selector", "url", "url_contains", "url_pattern"):
            if key in params and (not isinstance(params[key], str) or not params[key].strip()):
                errors.append(f"{key} must be a non-empty string")
        for key, choices in (
            ("state", {"visible", "attached", "detached", "hidden"}),
            ("for", {"load", "domcontentloaded", "networkidle"}),
        ):
            if key in params and (
                not isinstance(params[key], str) or (not _has_reference(params[key]) and params[key] not in choices)
            ):
                errors.append(f"{key} must be one of: {', '.join(sorted(choices))}")
        for key in ("network_idle", "animation_stable", "route_stable"):
            if key in params and params[key] is not True and not _has_reference(params[key]):
                errors.append(f"{key} must be true")
        for key in ("delay", "timeout", "interval", "route_stable_duration"):
            if key not in params:
                continue
            value = params[key]
            if _has_reference(value):
                try:
                    validate_reference(value)
                    continue
                except ValueError:
                    pass
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not math.isfinite(value)
                or (value < 0 if key == "delay" else value <= 0)
            ):
                errors.append(
                    f"{key} must be a finite {'nonnegative' if key == 'delay' else 'positive'} number or a complete reference"
                )
        if (
            "url_pattern" in params
            and isinstance(params["url_pattern"], str)
            and not _has_reference(params["url_pattern"])
        ):
            try:
                re.compile(params["url_pattern"])
            except re.error as error:
                errors.append(f"url_pattern: invalid regular expression: {error}")
        return errors

    @classmethod
    def validate_resolved_params(cls, params: dict[str, Any]) -> list[str]:
        errors = super().validate_resolved_params(params)
        for key in ("delay", "timeout", "interval", "route_stable_duration"):
            if key in params:
                value = params[key]
                if (
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not math.isfinite(value)
                    or (value < 0 if key == "delay" else value <= 0)
                ):
                    errors.append(
                        f"{key} must resolve to a finite {'nonnegative' if key == 'delay' else 'positive'} number"
                    )
        for key, choices in (
            ("state", {"visible", "attached", "detached", "hidden"}),
            ("for", {"load", "domcontentloaded", "networkidle"}),
        ):
            if key in params and (not isinstance(params[key], str) or params[key] not in choices):
                errors.append(f"{key} must resolve to one of: {', '.join(sorted(choices))}")
        for key in ("network_idle", "animation_stable", "route_stable"):
            if key in params and params[key] is not True:
                errors.append(f"{key} must resolve to true")
        return errors

    async def execute(self, context: StepContext, params: dict[str, Any]) -> StepResult:
        """Execute wait step."""
        errors = self.validate_resolved_params(params)
        if errors:
            return StepResult(success=False, message="; ".join(errors))
        timeout = params.get("timeout", self.spec.optional_params["timeout"])
        delay_ms = params.get("delay")

        if "condition" in params:
            await wait_for_condition(
                context, params["condition"], timeout=timeout, interval=params.get("interval", 100)
            )
            return StepResult(success=True, message=f"Wait condition satisfied: {params['condition']!r}")

        # Modes have already been validated as mutually exclusive.
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
            await context.page.wait_for_url(lambda url: url_contains in url, timeout=timeout)
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

        # Load state wait
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

    async def _wait_for_animation_stable(self, context: StepContext, timeout: float) -> None:
        """Wait for all CSS animations and transitions to complete."""
        handle = await context.page.wait_for_function(
            """
            () => document.getAnimations().every(animation =>
                !animation.pending && animation.playState !== 'running')
            """,
            timeout=timeout,
        )
        await handle.dispose()

    async def _wait_for_route_stable(self, context: StepContext, duration_ms: float, timeout: float) -> None:
        """Wait for URL to remain stable for a specified duration."""
        start_time = asyncio.get_event_loop().time()
        last_url = context.page.url
        stable_since = start_time

        while True:
            current_time = asyncio.get_event_loop().time()

            # Check timeout
            if (current_time - start_time) * 1000 >= timeout:
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
            remaining = timeout / 1000 - (current_time - start_time)
            await asyncio.sleep(min(0.1, remaining))
