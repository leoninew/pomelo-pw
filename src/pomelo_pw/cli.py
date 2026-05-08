"""CLI entry point."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import click

from pomelo_pw.executor import FlowExecutor
from pomelo_pw.steps import get_step, list_steps


@click.group()
def cli() -> None:
    """Pomelo PW - Flow-based UI Automation Tool."""


@cli.command()
@click.argument("flow", type=click.Path(exists=True))
@click.option("--base-url", help="Override base URL variable")
@click.option("--output", "-o", type=click.Path(), help="Output directory (default: ./<flow-name>, e.g., 'my-flow.yaml' → './my-flow/')")
@click.option("--headless", is_flag=True, help="Run in headless mode (default: visible browser)")
@click.option("--var", multiple=True, help="Override variable (format: key=value)")
@click.option("--verbose", "-v", is_flag=True, help="Show step-by-step progress")
@click.option("--json", "json_output", is_flag=True, help="Output result as JSON")
def run(
    flow: str,
    base_url: str | None,
    output: str | None,
    headless: bool,
    var: tuple[str, ...],
    verbose: bool,
    json_output: bool,
) -> None:
    """Execute a flow file."""
    flow_path = Path(flow)
    work_dir = Path.cwd()

    # Merge variables
    variables: dict[str, Any] = {}
    for v in var:
        if "=" in v:
            key, value = v.split("=", 1)
            variables[key] = value
    if base_url:
        variables["base_url"] = base_url

    output_dir = Path(output) if output else work_dir / flow_path.stem

    executor = FlowExecutor(work_dir=work_dir, verbose=verbose)

    try:
        result = asyncio.run(
            executor.run_flow(
                flow_path,
                variables=variables,
                output_dir=output_dir,
                headless=headless,
            ),
        )
    except Exception as e:
        result = {"success": False, "error": str(e)}

    if json_output:
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        if result.get("success"):
            msg = f"Completed: {result['steps_executed']} steps, {len(result['screenshots'])} screenshots"
            click.echo(msg)
        else:
            click.echo(f"Failed: {result.get('error', 'Unknown error')}", err=True)
            sys.exit(1)


@cli.command()
@click.argument("flow", type=click.Path(exists=True))
@click.option("--json", "json_output", is_flag=True, help="Output result as JSON")
def validate(flow: str, json_output: bool) -> None:
    """Validate a flow file without executing."""
    flow_path = Path(flow)
    executor = FlowExecutor(work_dir=Path.cwd())
    errors = executor.validate_flow_file(flow_path)

    if json_output:
        result = {"valid": len(errors) == 0, "errors": errors}
        click.echo(json.dumps(result, indent=2))
    else:
        if errors:
            click.echo("Validation failed:")
            for err in errors:
                click.echo(f"  - {err}")
        else:
            click.echo("Validation passed")


@cli.command()
def install() -> None:
    """Install Playwright browser (chromium)."""
    click.echo("Installing Playwright chromium browser...")
    try:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
        )
        click.echo("Installation completed successfully")
    except subprocess.CalledProcessError as e:
        click.echo(f"Installation failed: {e}", err=True)
        sys.exit(1)
    except FileNotFoundError:
        click.echo("Playwright not found. Please install pomelo-pw first:", err=True)
        click.echo("  uvx pomelo-pw install", err=True)
        sys.exit(1)


@cli.command("list")
def list_flows() -> None:
    """List available flows in current directory."""
    work_dir = Path.cwd()
    flows_dir = work_dir / "flows"

    if flows_dir.exists():
        click.echo("Flows in ./flows/:")
        for flow_file in flows_dir.glob("*.yaml"):
            click.echo(f"  - {flow_file.stem}")

    for flow_file in work_dir.glob("*.yaml"):
        click.echo(f"  - {flow_file.name}")


@cli.command()
def steps() -> None:
    """List available step types."""
    click.echo("Available steps:")
    for step_name in sorted(list_steps()):
        step_class = get_step(step_name)
        if step_class is not None:
            click.echo(f"  {step_name}: {step_class.spec.description}")


@cli.command()
@click.argument("step_type")
def spec(step_type: str) -> None:
    """Show specification for a step type."""
    step_class = get_step(step_type)
    if step_class is None:
        click.echo(f"Unknown step type: {step_type}", err=True)
        return

    spec = step_class.spec
    click.echo(f"\n{spec.name}: {spec.description}")

    if spec.aliases:
        click.echo(f"\nAliases: {', '.join(spec.aliases)}")

    click.echo("\nRequired parameters:")
    for p in spec.required_params:
        click.echo(f"  - {p}")

    click.echo("\nOptional parameters:")
    for p, default in spec.optional_params.items():
        click.echo(f"  - {p}: {default}")


@cli.command()
@click.argument("url")
@click.option("--headless", is_flag=True, help="Run in headless mode")
def explore(url: str, headless: bool) -> None:
    """Launch interactive page explorer to discover selectors.
    
    Hover over elements to see available selectors.
    Click an element to display its selectors in the terminal.
    """
    from pomelo_pw.explorer import explore_page
    
    try:
        asyncio.run(explore_page(url, headless=headless))
    except KeyboardInterrupt:
        pass


@cli.command()
@click.argument("url")
@click.argument("output", type=click.Path())
@click.option("--headless", is_flag=True, help="Run in headless mode")
def record(url: str, output: str, headless: bool) -> None:
    """Record user interactions and generate a YAML flow.
    
    Click elements to record click actions.
    Type in inputs to record fill actions.
    Press Enter to record key press.
    Press Ctrl+C to stop and save the flow.
    """
    from pomelo_pw.recorder import record_flow
    
    try:
        asyncio.run(record_flow(url, output, headless=headless))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    cli()
