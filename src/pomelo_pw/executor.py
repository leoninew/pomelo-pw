"""Flow executor module."""

from __future__ import annotations

import asyncio
import math
import time
from functools import partial
from pathlib import Path
from typing import Any

import click
import yaml
from playwright.async_api import async_playwright

from pomelo_pw.browser import BrowserLifecycle
from pomelo_pw.conditions import evaluate_condition
from pomelo_pw.config import load_app_config
from pomelo_pw.error_context import ErrorContextCollector
from pomelo_pw.polling import (
    PollAttemptsExhausted,
    PollDeadlineExceeded,
    PollError,
    PollProgress,
    PollTimeoutError,
    await_poll_operation,
    check_poll_deadline,
)
from pomelo_pw.runtime import NO_OUTPUT, RuntimeContext, snapshot_json, validate_inputs
from pomelo_pw.steps import get_step
from pomelo_pw.steps.base import BaseStep, StepContext, StepResult
from pomelo_pw.substitution import UndefinedVariableError, substitute_vars


class FlowExecutor:
    """Flow executor."""

    def __init__(self, work_dir: Path | None = None, verbose: bool = False) -> None:
        self.work_dir = work_dir or Path.cwd()
        self.verbose = verbose
        self.config = load_app_config()
        self.browser_lifecycle = BrowserLifecycle(self.config.playwright)

    def _log(self, msg: str) -> None:
        """Output progress message."""
        if self.verbose:
            click.echo(msg)

    def _normalize_retry_params(self, params: dict[str, Any]) -> dict[str, Any]:
        """Normalize retry parameters for consistent handling."""
        retry_on = params.get("retry_on", [])
        if isinstance(retry_on, str):
            params = {**params, "retry_on": [retry_on]}
        return params

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
        params = self._normalize_retry_params(params)
        max_retries = params.get("retry", 0)
        retry_delay = params.get("retry_delay", 1000)
        retry_on = params.get("retry_on", [])

        last_error: Exception | None = None

        for attempt in range(max_retries + 1):
            check_poll_deadline(step_context.polls)
            operation_params = params
            if (
                step_context.polls
                and step_instance.spec.name != "poll"
                and "timeout" in step_instance.spec.optional_params
            ):
                remaining_ms = (
                    min(poll.deadline for poll in step_context.polls) - asyncio.get_running_loop().time()
                ) * 1000
                timeout = params.get("timeout", step_instance.spec.optional_params["timeout"])
                if isinstance(timeout, (int, float)) and not isinstance(timeout, bool) and math.isfinite(timeout):
                    operation_params = {
                        **params,
                        "timeout": min(timeout, remaining_ms) if timeout > 0 else remaining_ms,
                    }
            try:
                for poll in step_context.polls:
                    poll.phase = "body"
                result = await await_poll_operation(
                    partial(step_instance.execute, step_context, operation_params), step_context.polls
                )

                if result.success:
                    if attempt > 0:
                        self._log(f"[{step_num}/{total_steps}] Succeeded on attempt {attempt + 1}")

                    return result

                # Step returned failure
                if attempt < max_retries:
                    self._log(f"[{step_num}/{total_steps}] Attempt {attempt + 1} failed: {result.message}, retrying...")
                    for poll in step_context.polls:
                        poll.phase = "retry_delay"
                    await asyncio.sleep(retry_delay / 1000)
                    continue

                return result

            except PollDeadlineExceeded:
                raise
            except Exception as e:
                last_error = e
                error_type = type(e).__name__.lower()

                # Check if we should retry this error type
                should_retry = not retry_on or any(err_type.lower() in error_type for err_type in retry_on)

                if attempt < max_retries and should_retry:
                    self._log(f"[{step_num}/{total_steps}] Attempt {attempt + 1} failed: {e}, retrying...")
                    for poll in step_context.polls:
                        poll.phase = "retry_delay"
                    await asyncio.sleep(retry_delay / 1000)
                    continue

                # No more retries or error type not in retry_on list
                raise

        # Should not reach here, but just in case
        if last_error:
            raise last_error

        return StepResult(success=False, message="Unknown error in retry logic")

    async def _execute_step(
        self,
        step: dict[str, Any],
        context: StepContext,
        step_num: str,
        total_steps: int,
    ) -> StepResult:
        """Prepare one lexical scope, execute, and publish only successful output."""
        check_poll_deadline(context.polls)
        for poll in context.polls:
            poll.step_path = step_num
        results = context.runtime.snapshot_results()
        save_as = step.get("save_as")
        if isinstance(save_as, str):
            context.runtime.invalidate(save_as)

        step_class = get_step(step["type"])
        if step_class is None:
            raise ValueError(f"Unknown step type: {step['type']}")
        errors = step_class.validate_params(step)
        if errors:
            raise ValueError("; ".join(errors))

        step_context = StepContext(
            page=context.page,
            runtime=context.runtime,
            output_dir=context.output_dir,
            screenshots=context.screenshots,
            scopes=(*context.scopes, step.get("variables", {})),
            bindings=context.bindings,
            polls=context.polls,
        )
        raw_fields = {
            "type",
            "variables",
            "save_as",
            *step_class.spec.child_step_params,
            *step_class.spec.literal_params,
        }
        params = substitute_vars(
            {key: value for key, value in step.items() if key not in raw_fields},
            step_context.inputs,
            results,
            step_context.bindings,
        )
        params.update({key: value for key, value in step.items() if key in raw_fields})
        errors = step_class.validate_resolved_params(params)
        if errors:
            raise ValueError("; ".join(errors))

        result = await self._execute_with_retry(step_class(), step_context, params, step_num, total_steps)
        if result.success:
            # Dispatch bodies outside retries to avoid replaying successful writes.
            if result.control.get("branch") in ("then", "else"):
                await self._execute_steps(result.control["steps"], step_context, prefix=f"{step_num}.")
            elif result.control.get("type") in ("times", "while"):
                await self._execute_loop(result.control, step_context, prefix=f"{step_num}.")
            elif result.control.get("type") == "foreach":
                await self._execute_foreach(result.control, step_context, prefix=f"{step_num}.")
            elif result.control.get("type") == "poll":
                result = await self._execute_poll(result.control, step_context, prefix=f"{step_num}.")
            check_poll_deadline(context.polls)
            if result.output is not NO_OUTPUT:
                result.output = snapshot_json(result.output)
            if save_as is not None:
                if result.output is NO_OUTPUT:
                    raise ValueError(f"Step '{step['type']}' produced no output for save_as '{save_as}'")
                context.runtime.publish(save_as, result.output)
                for poll in context.polls:
                    poll.results[save_as] = snapshot_json(result.output)
        return result

    async def _execute_steps(
        self,
        steps: list[dict[str, Any]],
        context: StepContext,
        prefix: str = "",
    ) -> None:
        """Execute a list of steps (used for conditional and loop bodies)."""
        for idx, step in enumerate(steps):
            step_type = step.get("type", "unknown")
            step_num = f"{prefix}{idx + 1}"

            self._log(f"[{step_num}] {step_type} begin")

            try:
                result = await self._execute_step(step, context, step_num, len(steps))
                if not result.success:
                    raise RuntimeError(result.message)
            except PollDeadlineExceeded:
                raise
            except Exception as error:
                if prefix:
                    if isinstance(error, PollError):
                        raise type(error)(f"Step {step_num} ({step_type}): {error}", error.diagnostics) from error
                    raise RuntimeError(f"Step {step_num} ({step_type}): {error}") from error
                raise

            self._log(f"[{step_num}] {result.message} end")

    async def _execute_foreach(
        self,
        loop_data: dict[str, Any],
        context: StepContext,
        prefix: str = "",
    ) -> None:
        """Run a stable collection snapshot with isolated, opaque bindings."""
        for index, item in enumerate(loop_data["items"]):
            check_poll_deadline(context.polls)
            self._log(f"[{prefix}index-{index}] Foreach index {index}")
            iteration_context = StepContext(
                page=context.page,
                runtime=context.runtime,
                output_dir=context.output_dir,
                screenshots=context.screenshots,
                scopes=context.scopes,
                bindings={
                    **context.bindings,
                    loop_data["as"]: snapshot_json(item),
                    loop_data["index_as"]: index,
                },
                polls=context.polls,
            )
            await self._execute_steps(loop_data["steps"], iteration_context, prefix=f"{prefix}index-{index}.")

    async def _execute_loop(
        self,
        loop_data: dict[str, Any],
        context: StepContext,
        prefix: str = "",
    ) -> None:
        """Execute loop iterations."""
        loop_type = loop_data["type"]
        steps = loop_data["steps"]

        if loop_type == "times":
            iterations = loop_data["iterations"]
            for i in range(iterations):
                check_poll_deadline(context.polls)
                self._log(f"[{prefix}iter-{i + 1}] Loop iteration {i + 1}/{iterations}")
                await self._execute_steps(
                    steps=steps,
                    context=context,
                    prefix=f"{prefix}iter-{i + 1}.",
                )

        elif loop_type == "while":
            condition = loop_data["condition"]
            max_iterations = loop_data["max_iterations"]

            iteration = 0

            while True:
                # Evaluate condition
                result = await await_poll_operation(
                    lambda: evaluate_condition(context, condition, "while"), context.polls
                )

                if not result:
                    self._log(f"[{prefix}while] Condition '{condition}' is false, exiting loop")
                    break

                if iteration >= max_iterations:
                    raise RuntimeError(
                        f"While loop exhausted max_iterations={max_iterations}; condition={condition!r}; "
                        f"last_results={context.runtime.snapshot_results()!r}"
                    )

                iteration += 1
                self._log(f"[{prefix}iter-{iteration}] Loop iteration {iteration} (while '{condition}')")

                await self._execute_steps(
                    steps=steps,
                    context=context,
                    prefix=f"{prefix}iter-{iteration}.",
                )

    async def _execute_poll(self, poll_data: dict[str, Any], context: StepContext, prefix: str) -> StepResult:
        check_poll_deadline(context.polls)
        started = asyncio.get_running_loop().time()
        deadline = min([started + poll_data["timeout"] / 1000, *(poll.deadline for poll in context.polls)])
        progress = PollProgress(
            path=prefix.rstrip("."),
            until=poll_data["until"],
            timeout=poll_data["timeout"],
            max_attempts=poll_data["max_attempts"],
            started=started,
            deadline=deadline,
        )
        polling_context = StepContext(
            page=context.page,
            runtime=context.runtime,
            output_dir=context.output_dir,
            screenshots=context.screenshots,
            scopes=context.scopes,
            bindings=context.bindings,
            polls=(*context.polls, progress),
        )

        def failure(error_class: type[PollError], reason: str) -> PollError:
            detail = progress.diagnostics()
            return error_class(
                f"Poll {reason} at {progress.step_path}, attempt {progress.attempts}, phase {progress.phase}; "
                f"timeout={progress.timeout:g}ms; until={progress.until!r}; last_results={progress.results!r}",
                {"polls": [detail]},
            )

        timer = asyncio.timeout_at(deadline)
        try:
            async with timer:
                while True:
                    check_poll_deadline(polling_context.polls)
                    progress.attempts += 1
                    self._log(f"[{prefix}attempt-{progress.attempts}] Poll attempt {progress.attempts}")
                    await self._execute_steps(
                        poll_data["steps"], polling_context, prefix=f"{prefix}attempt-{progress.attempts}."
                    )
                    for poll in polling_context.polls:
                        poll.phase = "until"
                        poll.step_path = f"{prefix}attempt-{progress.attempts}.until"
                    if await await_poll_operation(
                        lambda: evaluate_condition(polling_context, progress.until, "until"), polling_context.polls
                    ):
                        return StepResult(
                            success=True,
                            message=f"Poll satisfied after {progress.attempts} attempts",
                            output=snapshot_json(progress.output()),
                            diagnostics={"polls": [progress.diagnostics()]},
                        )
                    if progress.max_attempts is not None and progress.attempts >= progress.max_attempts:
                        raise failure(PollAttemptsExhausted, f"exhausted max_attempts={progress.max_attempts}")
                    for poll in polling_context.polls:
                        poll.phase = "interval"
                    await asyncio.sleep(poll_data["interval"] / 1000)
        except PollDeadlineExceeded as error:
            raise failure(PollTimeoutError, "timed out") from error
        except asyncio.CancelledError as error:
            if asyncio.get_running_loop().time() >= deadline:
                raise failure(PollTimeoutError, "timed out") from error
            raise
        except PollError as error:
            if error.diagnostics["polls"][0]["path"] == progress.path:
                raise
            raise type(error)(str(error), {"polls": [progress.diagnostics(), *error.diagnostics["polls"]]}) from error
        except Exception as error:
            if timer.expired():
                raise failure(PollTimeoutError, "timed out") from error
            raise failure(PollError, f"failed: {error}") from error

    def load_flow(self, flow_path: Path) -> dict[str, Any]:
        """Load flow file."""
        with open(flow_path, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}

    def validate_flow_file(self, flow_path: Path) -> list[str]:
        """Validate flow file."""
        flow = self.load_flow(flow_path)
        return self.validate_flow(flow)

    def validate_flow(self, flow: Any) -> list[str]:
        """Validate flow structure."""
        errors: list[str] = []

        if not isinstance(flow, dict):
            return ["Flow must be an object"]
        try:
            validate_inputs(flow.get("variables", {}))
        except ValueError as error:
            errors.append(f"Flow: {error}")
        rows = flow.get("data", [])
        if not isinstance(rows, list):
            errors.append("Flow field 'data' must be a list")
        else:
            for index, row in enumerate(rows):
                try:
                    validate_inputs(row)
                except ValueError as error:
                    errors.append(f"data[{index}]: {error}")

        if "output_dir" in flow:
            output_dir = flow["output_dir"]
            if not isinstance(output_dir, str) or not output_dir.strip():
                errors.append("Flow field 'output_dir' must be a non-empty string")

        if "headless" in flow and not isinstance(flow["headless"], bool):
            errors.append("Flow field 'headless' must be a boolean")

        errors.extend(self._validate_steps(flow.get("steps", []), "steps"))
        return errors

    def _validate_steps(self, steps: Any, path: str) -> list[str]:
        if not isinstance(steps, list):
            return [f"{path}: must be a list of steps"]
        errors: list[str] = []
        for index, step in enumerate(steps):
            location = f"{path}[{index}]"
            if not isinstance(step, dict):
                errors.append(f"{location}: step must be an object")
                continue
            step_type = step.get("type")
            if not step_type:
                errors.append(f"{location}: Missing 'type' field")
                continue
            step_class = get_step(step_type) if isinstance(step_type, str) else None
            if step_class is None:
                errors.append(f"{location}: Unknown step type '{step_type}'")
                continue
            errors.extend(f"{location} ({step_type}): {error}" for error in step_class.validate_params(step))
            for field in step_class.spec.child_step_params:
                if field in step:
                    errors.extend(self._validate_steps(step[field], f"{location}.{field}"))
        return errors

    def _resolve_output_dir(
        self,
        flow: dict[str, Any],
        flow_path: Path,
        variables: dict[str, Any],
        cli_output_dir: Path | None,
    ) -> Path:
        """Resolve the output root, with CLI settings taking precedence."""
        if cli_output_dir is not None:
            output_dir = cli_output_dir
        else:
            flow_output_dir = flow.get("output_dir")
            if isinstance(flow_output_dir, str):
                try:
                    resolved = substitute_vars({"output_dir": flow_output_dir}, variables)["output_dir"]
                except UndefinedVariableError as error:
                    if error.var_name == "results" or error.var_name.startswith(("results.", "results[")):
                        raise ValueError("output_dir cannot reference results before execution") from error
                    raise
                if not isinstance(resolved, str) or not resolved.strip():
                    raise ValueError("output_dir must resolve to a non-empty string")
                output_dir = Path(resolved)
            else:
                output_dir = Path(flow_path.stem)

        return output_dir if output_dir.is_absolute() else self.work_dir / output_dir

    def _resolve_headless(self, flow: dict[str, Any], cli_headless: bool | None) -> bool:
        """Resolve browser mode, with CLI settings taking precedence."""
        if cli_headless is not None:
            return cli_headless

        flow_headless = flow.get("headless", False)
        return flow_headless if isinstance(flow_headless, bool) else False

    async def run_flow(
        self,
        flow_path: Path,
        variables: dict[str, Any] | None = None,
        output_dir: Path | None = None,
        headless: bool | None = None,
    ) -> dict[str, Any]:
        """Execute flow, with data-driven expansion if 'data' field is present."""
        start_time = time.time()

        click.echo(f"Loading flow: {flow_path}")
        flow = self.load_flow(flow_path)

        # Validate flow
        click.echo("Validating flow...")
        errors = self.validate_flow(flow)
        if errors:
            raise ValueError("Flow validation failed:\n" + "\n".join(errors))
        steps = flow.get("steps", [])

        overrides = variables if variables is not None else {}
        base_inputs = RuntimeContext(flow_inputs=flow.get("variables", {}), overrides=overrides).effective_inputs()

        # Output directory
        output = self._resolve_output_dir(flow, flow_path, base_inputs, output_dir)
        output.mkdir(parents=True, exist_ok=True)

        resolved_headless = self._resolve_headless(flow, headless)

        # Data-driven: expand over each row
        data_rows: list[dict[str, Any]] = flow.get("data", [])

        if data_rows:
            click.echo(f"Data-driven mode: {len(data_rows)} rows × {len(steps)} steps")
            return await self._run_data_driven(
                flow=flow,
                flow_path=flow_path,
                steps=steps,
                overrides=overrides,
                output=output,
                headless=resolved_headless,
                data_rows=data_rows,
                start_time=start_time,
            )

        click.echo(f"Validation passed, {len(steps)} steps to execute")
        click.echo(f"Output directory: {output}")

        pw_config = self.config.playwright
        if pw_config.executable_path:
            click.echo(f"Using system Chrome: {pw_config.executable_path}")

        click.echo(f"Launching browser (headless={resolved_headless})...")
        async with async_playwright() as p:
            browser = await self._launch_browser(p, resolved_headless)
            try:
                result = await self._run_once(
                    browser=browser,
                    flow=flow,
                    flow_path=flow_path,
                    steps=steps,
                    overrides=overrides,
                    output=output,
                    start_time=start_time,
                )
            finally:
                await browser.close()

        return result

    async def _run_data_driven(
        self,
        flow: dict[str, Any],
        flow_path: Path,
        steps: list[dict[str, Any]],
        overrides: dict[str, Any],
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
            try:
                for row_idx, row in enumerate(data_rows):
                    row_num = str(row_idx + 1).zfill(row_width)
                    row_label = row.get("_label", f"row-{row_num}")
                    row_output = output / row_label
                    row_output.mkdir(parents=True, exist_ok=True)

                    click.echo(f"\n[{row_num}/{len(data_rows)}] Running with data: {row_label}")

                    row_start = time.time()
                    result = await self._run_once(
                        browser=browser,
                        flow=flow,
                        flow_path=flow_path,
                        steps=steps,
                        overrides=overrides,
                        row_inputs=row,
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
            finally:
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
        return await self.browser_lifecycle.launch(p, headless=headless)

    async def _run_once(
        self,
        browser: Any,
        flow: dict[str, Any],
        flow_path: Path,
        steps: list[dict[str, Any]],
        overrides: dict[str, Any],
        output: Path,
        start_time: float,
        row_inputs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute all steps once with the given variables."""
        flow_name = flow.get("name", flow_path.stem)
        total_steps = len(steps)
        step_width = len(str(total_steps))
        runtime = RuntimeContext(flow.get("variables", {}), overrides, row_inputs or {})

        context = await self.browser_lifecycle.new_context(browser)
        try:
            page = await context.new_page()

            error_collector = ErrorContextCollector()
            error_collector.setup_listeners(page)

            click.echo("Browser ready, starting execution...")

            screenshots: list[str] = []
            failed_step: dict[str, Any] | None = None
            step_context = StepContext(page=page, runtime=runtime, output_dir=output, screenshots=screenshots)

            for idx, step in enumerate(steps):
                step_type = step.get("type", "unknown")
                step_start = time.time()
                step_num = str(idx + 1).zfill(step_width)
                self._log(f"[{step_num}/{total_steps}] {step_type} begin")

                try:
                    result = await self._execute_step(step, step_context, step_num, total_steps)

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
                    if isinstance(e, PollError):
                        failed_step["diagnostics"] = e.diagnostics

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
                        return {
                            "success": False,
                            "flow": flow_name,
                            "duration_ms": int((time.time() - start_time) * 1000),
                            "screenshots": screenshots,
                            "steps_executed": idx,
                            "steps_total": total_steps,
                            "failed_step": failed_step,
                        }

            click.echo(
                "All steps completed successfully" if failed_step is None else "Execution completed with failures"
            )

            return {
                "success": failed_step is None,
                "flow": flow_name,
                "duration_ms": int((time.time() - start_time) * 1000),
                "screenshots": screenshots,
                "steps_executed": total_steps,
                "steps_total": total_steps,
                **({"failed_step": failed_step} if failed_step is not None else {}),
            }
        finally:
            await context.close()
