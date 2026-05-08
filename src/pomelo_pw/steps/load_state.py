"""Load state step."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from pomelo_pw.steps.base import BaseStep, StepContext, StepResult, StepSpec, register_step


@register_step
class LoadStateStep(BaseStep):
    """Load browser state (cookies, localStorage, sessionStorage).

    Note: This step loads state into the current browser context.
    For best results, use this step early in the flow, ideally right after navigation.
    """

    spec = StepSpec(
        name="load-state",
        description="Load browser state from a file into current context",
        required_params=["file"],
        optional_params={},
        aliases=["load-storage", "load-session"],
    )

    async def execute(self, context: StepContext, params: dict[str, Any]) -> StepResult:
        """Execute load-state step."""
        file_path_str = params["file"]

        # Resolve file path relative to output directory
        if not file_path_str.startswith("/") and not (len(file_path_str) > 1 and file_path_str[1] == ":"):
            file_path = context.output_dir / file_path_str
        else:
            file_path = Path(file_path_str)

        # Check if file exists
        if not file_path.exists():
            return StepResult(
                success=False,
                message=f"State file not found: {file_path}",
            )

        # Read storage state from file
        import json

        with open(file_path, encoding="utf-8") as f:
            storage_state = json.load(f)

        # Add cookies to current context
        cookies = storage_state.get("cookies", [])
        if cookies:
            await context.page.context.add_cookies(cookies)

        # Inject localStorage and sessionStorage via JavaScript
        origins = storage_state.get("origins", [])
        for origin_data in origins:
            origin = origin_data.get("origin")
            local_storage = origin_data.get("localStorage", [])

            if local_storage:
                # Navigate to origin first if needed
                current_url = context.page.url
                if not current_url.startswith(origin):
                    click.echo(f"  Note: Navigating to {origin} to inject localStorage", err=True)
                    await context.page.goto(origin)

                # Inject localStorage
                for item in local_storage:
                    await context.page.evaluate(f"localStorage.setItem({item['name']!r}, {item['value']!r})")

        cookies_count = len(cookies)
        storage_count = sum(len(o.get("localStorage", [])) for o in origins)

        return StepResult(
            success=True,
            message=f"Browser state loaded: {cookies_count} cookies, {storage_count} localStorage items",
            data={"file": str(file_path), "cookies_count": cookies_count, "storage_count": storage_count},
        )
