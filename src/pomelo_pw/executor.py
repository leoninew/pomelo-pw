"""Flow executor module."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import click
import yaml
from playwright.async_api import async_playwright

from pomelo_pw.config import load_app_config
from pomelo_pw.error_context import ErrorContextCollector
from pomelo_pw.steps import get_step
from pomelo_pw.steps.base import StepContext
from pomelo_pw.substitution import substitute_vars


class FlowExecutor:
    """Flow executor."""

    def __init__(self, work_dir: Path | None = None, verbose: bool = False) -> None:
        self.work_dir = work_dir or Path.cwd()
        self.verbose = verbose
        self.config = load_app_config()

    def _log(self, msg: str) -> None:
        """Output progress message."""
        if self.verbose:
            click.echo(msg)

    def load_flow(self, flow_path: Path) -> dict[str, Any]:
        """Load flow file."""
        with open(flow_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def validate_flow_file(self, flow_path: Path) -> list[str]:
        """Validate flow file."""
        flow = self.load_flow(flow_path)
        return self.validate_flow(flow)

    def validate_flow(self, flow: dict[str, Any]) -> list[str]:
        """Validate flow structure."""
        errors: list[str] = []

        steps = flow.get("steps", [])
        for i, step in enumerate(steps):
            step_type = step.get("type")
            if not step_type:
                errors.append(f"Step {i}: Missing 'type' field")
                continue

            step_class = get_step(step_type)
            if not step_class:
                errors.append(f"Step {i}: Unknown step type '{step_type}'")
                continue

            step_errors = step_class.validate_params(step)
            for err in step_errors:
                errors.append(f"Step {i} ({step_type}): {err}")

        return errors

    async def run_flow(
        self,
        flow_path: Path,
        variables: dict[str, Any] | None = None,
        output_dir: Path | None = None,
        headless: bool = False,
    ) -> dict[str, Any]:
        """Execute flow."""
        start_time = time.time()

        click.echo(f"Loading flow: {flow_path}")
        flow = self.load_flow(flow_path)
        steps = flow.get("steps", [])

        # Validate flow
        click.echo("Validating flow...")
        errors = self.validate_flow(flow)
        if errors:
            raise ValueError("Flow validation failed:\n" + "\n".join(errors))
        click.echo(f"Validation passed, {len(steps)} steps to execute")

        # Build variables: flow level + CLI override
        flow_vars = flow.get("variables", {})
        global_vars = {**flow_vars, **(variables or {})}

        # Output directory
        output = output_dir or self.work_dir / "output"
        output.mkdir(parents=True, exist_ok=True)
        click.echo(f"Output directory: {output}")

        # Browser config (default: visible browser)
        pw_config = self.config.playwright

        if pw_config.executable_path:
            click.echo(f"Using system Chrome: {pw_config.executable_path}")

        screenshots: list[str] = []
        total_steps = len(steps)
        step_width = len(str(total_steps))  # Width for zero-padding

        click.echo(f"Launching browser (headless={headless})...")
        async with async_playwright() as p:
            launch_options: dict[str, Any] = {
                "headless": headless,
                "timeout": pw_config.timeout,
                "slow_mo": pw_config.slow_mo,
            }
            if pw_config.executable_path:
                launch_options["executable_path"] = pw_config.executable_path
            browser = await p.chromium.launch(**launch_options)
            context = await browser.new_context(
                viewport={"width": pw_config.viewport.width, "height": pw_config.viewport.height},
            )
            page = await context.new_page()
            
            # Setup error context collector
            error_collector = ErrorContextCollector()
            error_collector.setup_listeners(page)
            
            click.echo("Browser ready, starting execution...")

            failed_step: dict[str, Any] | None = None

            for idx, step in enumerate(steps):
                step_type = step.get("type", "unknown")
                step_start = time.time()
                step_num = str(idx + 1).zfill(step_width)
                self._log(f"[{step_num}/{total_steps}] {step_type} begin")

                try:
                    # Merge step-level variables
                    step_vars = step.get("variables", {})
                    merged_vars = {**global_vars, **step_vars}

                    # Substitute variables in params
                    params = substitute_vars(step, merged_vars)

                    step_class = get_step(params["type"])
                    if step_class is None:
                        raise ValueError(f"Unknown step type: {params['type']}")

                    step_instance = step_class()

                    # Create new context for each step
                    step_context = StepContext(
                        page=page,
                        variables=merged_vars,
                        output_dir=output,
                        screenshots=screenshots,
                    )

                    result = await step_instance.execute(step_context, params)

                    if not result.success:
                        raise RuntimeError(result.message)

                    elapsed_ms = int((time.time() - step_start) * 1000)
                    self._log(f"[{step_num}/{total_steps}] {result.message} end, cost {elapsed_ms} ms")

                except Exception as e:
                    # Collect error context
                    error_context = await error_collector.collect_error_context(
                        page=page,
                        output_dir=output,
                        step_index=idx,
                        step_type=step_type,
                    )
                    
                    failed_step = {
                        "index": idx,
                        "type": step_type,
                        "error": str(e),
                        "context": error_context.to_dict(),
                    }
                    
                    click.echo(f"[{step_num}/{total_steps}] {step_type} FAILED: {e}", err=True)
                    
                    # Show error context summary
                    if error_context.screenshot_path:
                        click.echo(f"  Screenshot saved: {error_context.screenshot_path}", err=True)
                    if error_context.html_snapshot_path:
                        click.echo(f"  HTML snapshot saved: {error_context.html_snapshot_path}", err=True)
                    if error_context.console_errors:
                        click.echo(f"  Console errors: {len(error_context.console_errors)}", err=True)
                    if error_context.network_errors:
                        click.echo(f"  Network errors: {len(error_context.network_errors)}", err=True)
                    click.echo(f"  Current URL: {error_context.url}", err=True)

                    # Error handling: stop by default
                    on_error = flow.get("on_error", "stop")
                    if on_error == "stop":
                        click.echo("Stopping execution due to error")
                        await browser.close()
                        return {
                            "success": False,
                            "flow": flow.get("name", flow_path.stem),
                            "duration_ms": int((time.time() - start_time) * 1000),
                            "screenshots": screenshots,
                            "steps_executed": idx,
                            "steps_total": total_steps,
                            "failed_step": failed_step,
                        }

            click.echo(f"All steps completed successfully, closing browser...")
            await browser.close()

        return {
            "success": True,
            "flow": flow.get("name", flow_path.stem),
            "duration_ms": int((time.time() - start_time) * 1000),
            "screenshots": screenshots,
            "steps_executed": total_steps,
            "steps_total": total_steps,
        }
