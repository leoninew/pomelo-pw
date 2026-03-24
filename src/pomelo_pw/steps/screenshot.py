"""Screenshot step."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from pomelo_pw.steps.base import BaseStep, StepContext, StepResult, StepSpec, register_step


@register_step
class ScreenshotStep(BaseStep):
    """Capture screenshot."""

    spec = StepSpec(
        name="screenshot",
        description="Capture a screenshot of the current page",
        required_params=["file"],
        optional_params={
            "full_page": False,
            "selector": None,
        },
        aliases=["capture", "snap"],
    )

    async def execute(self, context: StepContext, params: dict[str, Any]) -> StepResult:
        """Execute screenshot step."""
        file_name = params["file"]
        full_page = params.get("full_page", self.spec.optional_params["full_page"])
        selector = params.get("selector", self.spec.optional_params["selector"])

        file_path = context.output_dir / file_name
        file_path.parent.mkdir(parents=True, exist_ok=True)

        if selector:
            element = await context.page.query_selector(selector)
            if element is None:
                return StepResult(
                    success=False,
                    message=f"Element not found: {selector}",
                )
            await element.screenshot(path=str(file_path))
        else:
            await context.page.screenshot(path=str(file_path), full_page=full_page)

        context.screenshots.append(str(file_path))
        try:
            rel_path = file_path.relative_to(Path.cwd())
        except ValueError:
            rel_path = file_path
        click.echo(f"Screenshot saved: {rel_path}")
        return StepResult(success=True, message=f"Screenshot saved: {rel_path}")
