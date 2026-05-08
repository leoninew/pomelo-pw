"""Flow executor module."""

from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

import click
import yaml
from playwright.async_api import async_playwright

from pomelo_pw.config import load_app_config
from pomelo_pw.error_context import ErrorContextCollector
from pomelo_pw.steps import get_step
from pomelo_pw.steps.base import BaseStep, StepContext, StepResult
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

    async def _execute_with_retry(
        self,
        step_instance: BaseStep,
        step_context: StepContext,
        params: dict[str, Any],
        step_num: str,
        total_steps: int,
    ) -> StepResult:
        """Execute step with retry support.
        
        Retry parameters:
        - retry: number of retry attempts (default: 0, no retry)
        - retry_delay: delay between retries in milliseconds (default: 1000)
        - retry_on: list of error types to retry on (default: all errors)
        """
        max_retries = params.get("retry", 0)
        retry_delay = params.get("retry_delay", 1000)
        retry_on = params.get("retry_on", [])  # Empty list means retry on all errors
        
        last_error: Exception | None = None
        
        for attempt in range(max_retries + 1):
            try:
                result = await step_instance.execute(step_context, params)
                
                if result.success:
                    if attempt > 0:
                        self._log(f"[{step_num}/{total_steps}] Succeeded on attempt {attempt + 1}")
                    
                    # Handle conditional and loop steps
                    if result.data:
                        # Conditional step
                        if "branch" in result.data:
                            branch = result.data["branch"]
                            if branch in ("then", "else"):
                                nested_steps = result.data["steps"]
                                await self._execute_steps(
                                    steps=nested_steps,
                                    context=step_context,
                                    global_vars=step_context.variables,
                                    prefix=f"{step_num}.",
                                )
                        
                        # Loop step
                        elif "type" in result.data and result.data["type"] in ("times", "while"):
                            await self._execute_loop(
                                loop_data=result.data,
                                context=step_context,
                                global_vars=step_context.variables,
                                prefix=f"{step_num}.",
                            )
                    
                    return result
                
                # Step returned failure
                if attempt < max_retries:
                    self._log(f"[{step_num}/{total_steps}] Attempt {attempt + 1} failed: {result.message}, retrying...")
                    await asyncio.sleep(retry_delay / 1000)
                    continue
                
                return result
                
            except Exception as e:
                last_error = e
                error_type = type(e).__name__.lower()
                
                # Check if we should retry this error type
                should_retry = not retry_on or any(
                    err_type.lower() in error_type for err_type in retry_on
                )
                
                if attempt < max_retries and should_retry:
                    self._log(f"[{step_num}/{total_steps}] Attempt {attempt + 1} failed: {e}, retrying...")
                    await asyncio.sleep(retry_delay / 1000)
                    continue
                
                # No more retries or error type not in retry_on list
                raise
        
        # Should not reach here, but just in case
        if last_error:
            raise last_error
        
        return StepResult(success=False, message="Unknown error in retry logic")

    async def _execute_steps(
        self,
        steps: list[dict[str, Any]],
        context: StepContext,
        global_vars: dict[str, Any],
        prefix: str = "",
    ) -> None:
        """Execute a list of steps (used for conditional and loop bodies)."""
        for idx, step in enumerate(steps):
            step_type = step.get("type", "unknown")
            step_num = f"{prefix}{idx + 1}"
            
            self._log(f"[{step_num}] {step_type} begin")
            
            # Merge step-level variables
            step_vars = step.get("variables", {})
            merged_vars = {**global_vars, **step_vars}
            
            # Substitute variables in params
            params = substitute_vars(step, merged_vars)
            
            step_class = get_step(params["type"])
            if step_class is None:
                raise ValueError(f"Unknown step type: {params['type']}")
            
            step_instance = step_class()
            
            # Update context with merged variables
            nested_context = StepContext(
                page=context.page,
                variables=merged_vars,
                output_dir=context.output_dir,
                screenshots=context.screenshots,
            )
            
            # Execute step
            result = await self._execute_with_retry(
                step_instance=step_instance,
                step_context=nested_context,
                params=params,
                step_num=step_num,
                total_steps=len(steps),
            )
            
            if not result.success:
                raise RuntimeError(result.message)
            
            self._log(f"[{step_num}] {result.message} end")

    async def _execute_loop(
        self,
        loop_data: dict[str, Any],
        context: StepContext,
        global_vars: dict[str, Any],
        prefix: str = "",
    ) -> None:
        """Execute loop iterations."""
        loop_type = loop_data["type"]
        steps = loop_data["steps"]
        
        if loop_type == "times":
            iterations = loop_data["iterations"]
            for i in range(iterations):
                self._log(f"[{prefix}iter-{i + 1}] Loop iteration {i + 1}/{iterations}")
                await self._execute_steps(
                    steps=steps,
                    context=context,
                    global_vars=global_vars,
                    prefix=f"{prefix}iter-{i + 1}.",
                )
        
        elif loop_type == "while":
            condition = loop_data["condition"]
            max_iterations = loop_data["max_iterations"]
            
            # Import conditional step to reuse condition evaluation
            from pomelo_pw.steps.conditional import ConditionalStep
            
            conditional = ConditionalStep()
            iteration = 0
            
            while iteration < max_iterations:
                # Evaluate condition
                result = await conditional._evaluate_condition(context.page, condition)
                
                if not result:
                    self._log(f"[{prefix}while] Condition '{condition}' is false, exiting loop")
                    break
                
                iteration += 1
                self._log(f"[{prefix}iter-{iteration}] Loop iteration {iteration} (while '{condition}')")
                
                await self._execute_steps(
                    steps=steps,
                    context=context,
                    global_vars=global_vars,
                    prefix=f"{prefix}iter-{iteration}.",
                )
            
            if iteration >= max_iterations:
                self._log(f"[{prefix}while] Reached max iterations ({max_iterations}), exiting loop")


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
        """Execute flow, with data-driven expansion if 'data' field is present."""
        start_time = time.time()

        click.echo(f"Loading flow: {flow_path}")
        flow = self.load_flow(flow_path)
        steps = flow.get("steps", [])

        # Validate flow
        click.echo("Validating flow...")
        errors = self.validate_flow(flow)
        if errors:
            raise ValueError("Flow validation failed:\n" + "\n".join(errors))

        # Build base variables: flow level + CLI override
        flow_vars = flow.get("variables", {})
        base_vars = {**flow_vars, **(variables or {})}

        # Output directory
        output = output_dir or self.work_dir / "output"
        output.mkdir(parents=True, exist_ok=True)

        # Data-driven: expand over each row
        data_rows: list[dict[str, Any]] = flow.get("data", [])

        if data_rows:
            click.echo(f"Data-driven mode: {len(data_rows)} rows × {len(steps)} steps")
            return await self._run_data_driven(
                flow=flow,
                flow_path=flow_path,
                steps=steps,
                base_vars=base_vars,
                output=output,
                headless=headless,
                data_rows=data_rows,
                start_time=start_time,
            )

        click.echo(f"Validation passed, {len(steps)} steps to execute")
        click.echo(f"Output directory: {output}")

        pw_config = self.config.playwright
        if pw_config.executable_path:
            click.echo(f"Using system Chrome: {pw_config.executable_path}")

        click.echo(f"Launching browser (headless={headless})...")
        async with async_playwright() as p:
            browser = await self._launch_browser(p, headless)
            result = await self._run_once(
                browser=browser,
                flow=flow,
                flow_path=flow_path,
                steps=steps,
                global_vars=base_vars,
                output=output,
                start_time=start_time,
            )
            await browser.close()

        return result

    async def _run_data_driven(
        self,
        flow: dict[str, Any],
        flow_path: Path,
        steps: list[dict[str, Any]],
        base_vars: dict[str, Any],
        output: Path,
        headless: bool,
        data_rows: list[dict[str, Any]],
        start_time: float,
    ) -> dict[str, Any]:
        """Execute flow once per data row, each in its own output subdirectory."""
        flow_name = flow.get("name", flow_path.stem)
        on_error = flow.get("on_error", "stop")
        row_width = len(str(len(data_rows)))

        row_results: list[dict[str, Any]] = []
        all_screenshots: list[str] = []

        pw_config = self.config.playwright
        if pw_config.executable_path:
            click.echo(f"Using system Chrome: {pw_config.executable_path}")

        click.echo(f"Launching browser (headless={headless})...")
        async with async_playwright() as p:
            browser = await self._launch_browser(p, headless)

            for row_idx, row in enumerate(data_rows):
                row_num = str(row_idx + 1).zfill(row_width)
                row_label = row.get("_label", f"row-{row_num}")
                row_output = output / row_label
                row_output.mkdir(parents=True, exist_ok=True)

                # Merge base vars with row data (row takes precedence)
                row_vars = {**base_vars, **row}

                click.echo(f"\n[{row_num}/{len(data_rows)}] Running with data: {row_label}")

                row_start = time.time()
                result = await self._run_once(
                    browser=browser,
                    flow=flow,
                    flow_path=flow_path,
                    steps=steps,
                    global_vars=row_vars,
                    output=row_output,
                    start_time=row_start,
                )

                result["row"] = row_label
                result["row_data"] = row
                row_results.append(result)
                all_screenshots.extend(result.get("screenshots", []))

                if not result["success"] and on_error == "stop":
                    click.echo(f"Stopping data-driven run at row {row_num} due to error")
                    break

            await browser.close()

        total_ms = int((time.time() - start_time) * 1000)
        passed = sum(1 for r in row_results if r["success"])
        failed = len(row_results) - passed

        click.echo(f"\nData-driven complete: {passed} passed, {failed} failed ({total_ms} ms)")

        return {
            "success": failed == 0,
            "flow": flow_name,
            "duration_ms": total_ms,
            "screenshots": all_screenshots,
            "data_driven": True,
            "rows_total": len(data_rows),
            "rows_passed": passed,
            "rows_failed": failed,
            "row_results": row_results,
        }

    async def _launch_browser(self, p: Any, headless: bool) -> Any:
        """Launch browser with configured options."""
        pw_config = self.config.playwright
        launch_options: dict[str, Any] = {
            "headless": headless,
            "timeout": pw_config.timeout,
            "slow_mo": pw_config.slow_mo,
        }
        if pw_config.executable_path:
            launch_options["executable_path"] = pw_config.executable_path
        return await p.chromium.launch(**launch_options)

    async def _run_once(
        self,
        browser: Any,
        flow: dict[str, Any],
        flow_path: Path,
        steps: list[dict[str, Any]],
        global_vars: dict[str, Any],
        output: Path,
        start_time: float,
    ) -> dict[str, Any]:
        """Execute all steps once with the given variables."""
        pw_config = self.config.playwright
        flow_name = flow.get("name", flow_path.stem)
        total_steps = len(steps)
        step_width = len(str(total_steps))

        context = await browser.new_context(
            viewport={"width": pw_config.viewport.width, "height": pw_config.viewport.height},
        )
        page = await context.new_page()

        error_collector = ErrorContextCollector()
        error_collector.setup_listeners(page)

        click.echo("Browser ready, starting execution...")

        screenshots: list[str] = []
        failed_step: dict[str, Any] | None = None

        for idx, step in enumerate(steps):
            step_type = step.get("type", "unknown")
            step_start = time.time()
            step_num = str(idx + 1).zfill(step_width)
            self._log(f"[{step_num}/{total_steps}] {step_type} begin")

            try:
                step_vars = step.get("variables", {})
                merged_vars = {**global_vars, **step_vars}
                params = substitute_vars(step, merged_vars)

                step_class = get_step(params["type"])
                if step_class is None:
                    raise ValueError(f"Unknown step type: {params['type']}")

                step_instance = step_class()
                step_context = StepContext(
                    page=page,
                    variables=merged_vars,
                    output_dir=output,
                    screenshots=screenshots,
                )

                result = await self._execute_with_retry(
                    step_instance=step_instance,
                    step_context=step_context,
                    params=params,
                    step_num=step_num,
                    total_steps=total_steps,
                )

                if not result.success:
                    raise RuntimeError(result.message)

                elapsed_ms = int((time.time() - step_start) * 1000)
                self._log(f"[{step_num}/{total_steps}] {result.message} end, cost {elapsed_ms} ms")

            except Exception as e:
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

                if error_context.screenshot_path:
                    click.echo(f"  Screenshot saved: {error_context.screenshot_path}", err=True)
                if error_context.html_snapshot_path:
                    click.echo(f"  HTML snapshot saved: {error_context.html_snapshot_path}", err=True)
                if error_context.console_errors:
                    click.echo(f"  Console errors: {len(error_context.console_errors)}", err=True)
                if error_context.network_errors:
                    click.echo(f"  Network errors: {len(error_context.network_errors)}", err=True)
                click.echo(f"  Current URL: {error_context.url}", err=True)

                on_error = flow.get("on_error", "stop")
                if on_error == "stop":
                    click.echo("Stopping execution due to error")
                    await context.close()
                    return {
                        "success": False,
                        "flow": flow_name,
                        "duration_ms": int((time.time() - start_time) * 1000),
                        "screenshots": screenshots,
                        "steps_executed": idx,
                        "steps_total": total_steps,
                        "failed_step": failed_step,
                    }

        click.echo("All steps completed successfully")
        await context.close()

        return {
            "success": True,
            "flow": flow_name,
            "duration_ms": int((time.time() - start_time) * 1000),
            "screenshots": screenshots,
            "steps_executed": total_steps,
            "steps_total": total_steps,
        }
