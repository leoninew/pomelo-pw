# Usage Guide

[Home](../README.md) | [Flow reference](FLOW_REFERENCE.md) | [简体中文](USAGE_CN.md)

This guide covers running flows and integrating with other projects. See the [flow reference](FLOW_REFERENCE.md) for parameters and contracts, or the [development guide](DEVELOPMENT.md) for development and releases.

## Browser Setup and One-Off Runs

See [installation](../README.md#install). `pomelo-pw install` downloads Playwright Chromium for package installations; source checkouts and standalone binaries use system Chrome/Chromium when found. Use `uvx pomelo-pw` to invoke the published package without installing the CLI first.

```bash
uvx pomelo-pw install
uvx pomelo-pw run flow.yaml --headless
```

## Find Selectors and Create Flows

```bash
# Inspect a page and copy a selector from the interactive overlay
pomelo-pw explore https://the-internet.herokuapp.com

# Record clicks, fills, and Enter presses into a YAML flow
pomelo-pw record https://the-internet.herokuapp.com recorded-flow.yaml
```

Prefer selectors based on stable semantics, such as `role=button[name="Continue"]`, over presentation-oriented CSS classes.

## Run Flows

```bash
# Run visibly with step progress
pomelo-pw run flow.yaml -v

# Run headlessly and emit the result as JSON
pomelo-pw run flow.yaml --headless --json

# Override a flow variable for this run
pomelo-pw run flow.yaml --var base_url=https://staging.example.com

# Override the flow output_dir for this run
pomelo-pw run flow.yaml -o .pomelo-pw/artifacts/manual-run

# Validate YAML and step parameters without launching a browser
pomelo-pw validate flow.yaml
```

Input precedence is CLI/API overrides > current step variables > enclosing step variables > data row > flow variables. `--var key=value` remains a text input. `inputs` and `results` are reserved input names.

## Output Directory and Browser Mode

Screenshots and failure artifacts are written to `./<flow-file-stem>/` by default, for example `./smoke/` for `smoke.yaml`. A flow can set a top-level `output_dir`, including `{{variable}}` references; relative paths are resolved from the command working directory. Flows can also set a top-level boolean `headless`; it defaults to `false`. Use `-o <directory>` or `--headless` to override either setting for one run.

## Author Flows

The following flow shows the common pattern: navigate, interact, wait for a meaningful result, then capture evidence.

```yaml
name: login-smoke
variables:
  base_url: "https://app.example.com"
  username: "user@example.com"
  password: "secret"

steps:
  - type: navigate
    url: "{{base_url}}/login"
  - type: fill
    selector: "input[name='email']"
    value: "{{username}}"
  - type: fill
    selector: "input[name='password']"
    value: "{{password}}"
  - type: click
    selector: "button[type='submit']"
  - type: wait
    url_contains: "/dashboard"
  - type: screenshot
    file: "dashboard.png"
```

## Save and Reuse Login State

Save state after login. In another flow, explicitly load the same file before navigating to the application. Both flows can set `output_dir: output/auth`:

```yaml
# Login flow: run after a successful login.
- type: save-state
  file: session.json
```

```yaml
# New flow: restore state before opening the application.
- type: load-state
  file: session.json
- type: navigate
  url: "{{base_url}}/"
```

Relative `file` paths resolve from the flow output directory; absolute paths can share state across different output directories. Cookies (including HttpOnly) and localStorage are saved and restored. sessionStorage and IndexedDB are not included. Each run creates a new browser context and does not load previous state automatically.

`load-state` fails if the file is missing and does not check server-side session validity. Log in and save first; handle expired or revoked sessions with a login branch in the flow. `request` shares restored cookies, but does not convert localStorage tokens into headers.

See the [browser state examples](../example/README.md#browser-state). They save anonymous public-page state; configure application-specific login steps for authenticated use.

## Use as a Python Package

Add the dependency in the calling project, then install the browser. Use the published package, or an editable source dependency for local development:

```bash
uv add pomelo-pw
uv run pomelo-pw install

# Alternative for local development:
uv add --editable ../pomelo-pw
```

The CLI and Python API use the same `FlowExecutor` to run existing YAML. This example uses the calling project's current directory as its working directory:

```python
import asyncio
from pathlib import Path

from pomelo_pw.executor import FlowExecutor


async def main():
    root = Path.cwd()
    executor = FlowExecutor(work_dir=root)
    result = await executor.run_flow(
        root / "flow.yaml",
        variables={"base_url": "http://localhost:3000"},
        output_dir=root / "output",
        headless=True,
    )
    if result["status"] == "failed":
        raise RuntimeError(result["errors"])
    return result


result = asyncio.run(main())
```

In an existing async entry point, use `await executor.run_flow(...)` directly. `executor.validate_flow_file(path)` validates YAML and returns a list of errors. Execution failures are represented by `status` and `errors`; callers must check the report. See the [report contract](FLOW_REFERENCE.md#assertions-and-execution-reports).

Pin the dependency version for deployed use; YAML must follow that version's syntax. `work_dir` resolves relative output directories; pass an absolute `flow_path` to identify the YAML independently of the process working directory.

## Retries and Data-Driven Runs

Ordinary steps accept `retry`, `retry_delay` (milliseconds), and `retry_on` (error class names). Retries repeat the current step; child failures do not replay a completed branch or traversal. Put poll retries on child queries and submissions before polling. Callers must ensure idempotency for write retries.

A top-level `data` array runs the flow independently for each row. Row fields override flow variables; `_label` names the output subdirectory. `on_error: stop` is the default. `continue` can run later top-level steps or data rows, but any execution error still fails the final report. See the [agent skill example](../plugins/pomelo-pw/skills/pomelo-pw/SKILL.md#data-driven-testing).

## Screenshot Baseline Comparison

Install optional dependencies in the same environment that runs the CLI:

```bash
# Tool installation:
uv tool install "pomelo-pw[visual]" --force

# Project dependency:
uv add "pomelo-pw[visual]"
```

Try the [visual comparison example](../example/README.md#visual-comparison).

## Examples and Parameter Reference

The [example guide](../example/README.md) lists prerequisites, commands, and variable overrides. The [combined example](../example/README.md#integrated-flow-capabilities) connects pagination, login-state restoration, serial tasks, and report exports. See the [flow reference](FLOW_REFERENCE.md) for parameters and data semantics, or the [agent skill](../plugins/pomelo-pw/skills/pomelo-pw/SKILL.md) for templates.
