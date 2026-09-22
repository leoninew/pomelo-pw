# Pomelo PW

[![CI](https://github.com/leoninew/pomelo-pw/actions/workflows/ci.yml/badge.svg)](https://github.com/leoninew/pomelo-pw/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/pomelo-pw)](https://pypi.org/project/pomelo-pw/)
[![GitHub Release](https://img.shields.io/github/v/release/leoninew/pomelo-pw)](https://github.com/leoninew/pomelo-pw/releases)

[English](README.md) | [简体中文](README_CN.md)

Pomelo PW is a Playwright-powered CLI for browser automation. It runs declarative YAML flows, so browser checks can live alongside application code without requiring a custom test harness.

It is intended for repeatable UI checks, scripted workflows, visual comparisons, and agent-assisted browser tasks. Flows validate their parameters before execution and collect screenshots, page snapshots, console errors, and network failures when a step fails.

## What It Provides

- YAML flows with `{{variable}}` substitution and CLI overrides
- Browser steps for navigation, forms, waits, screenshots, state reuse, conditions, and loops
- Interactive explorer and recorder for finding selectors and creating starting flows
- Step-level retries, data-driven runs, and screenshot baseline comparison
- Native plugin packaging for Claude Code, Codex, and Grok Build

## Install

Pomelo PW requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

The Python package is available on [PyPI](https://pypi.org/project/pomelo-pw/). Standalone Windows, macOS, and Linux executables are available from [GitHub Releases](https://github.com/leoninew/pomelo-pw/releases).

```bash
# Install the published CLI, then install its browser
uv tool install pomelo-pw
pomelo-pw install

# Or invoke the published package once without installing the CLI
uvx pomelo-pw install

# Work from a source checkout
uv sync --all-groups --locked
uv run pomelo-pw install
```

The `install` command downloads Playwright Chromium for package installations. When run from a source checkout or the standalone binary, Pomelo PW uses an installed system Chrome or Chromium when it can find one.

Install visual comparison support only when flows use screenshot baselines:

```bash
uv pip install pillow
```

## Quick Start

Create `smoke.yaml`:

```yaml
name: example-smoke
output_dir: "output"
headless: false
variables:
  base_url: "https://the-internet.herokuapp.com"
  run_id: "local"

steps:
  - type: navigate
    url: "{{base_url}}"
  - type: screenshot
    file: "homepage.png"
  - type: scroll
    direction: down
    distance: 500
  - type: screenshot
    file: "scrolled.png"
```

Run and validate it:

```bash
uvx pomelo-pw validate smoke.yaml
uvx pomelo-pw run smoke.yaml --headless
```

Screenshots and failure artifacts are written to `./smoke/` by default. A flow can set a top-level `output_dir`, including `{{variable}}` references; relative paths are resolved from the command working directory. Flows can also set a top-level boolean `headless`; it defaults to `false`. Use `-o <directory>` or `--headless` to override either setting for one run.

## Use Pomelo PW

### Find Selectors and Create Flows

```bash
# Inspect a page and copy a selector from the interactive overlay
pomelo-pw explore https://the-internet.herokuapp.com

# Record clicks, fills, and Enter presses into a YAML flow
pomelo-pw record https://the-internet.herokuapp.com recorded-flow.yaml
```

Prefer selectors based on stable semantics, such as `role=button[name="Continue"]`, over presentation-oriented CSS classes.

### Run Flows

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

Variables use `{{name}}`; CLI values take precedence over step-level values, which take precedence over flow-level values. The `${name}` form is preserved for JavaScript and shell template literals.

### Author Flows

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

| Step | Main parameters | Purpose |
| --- | --- | --- |
| `navigate` | `url` | Open a page |
| `click`, `hover`, `press` | `selector` or `key` | Interact with an element or keyboard |
| `fill`, `type` | `selector`, `value` | Enter text |
| `select` | `selector`, one of `value` / `label` / `index` | Choose an option by HTML value, visible text, or zero-based position |
| `wait` | selector, URL, network, or timing condition | Synchronize with dynamic UI |
| `screenshot` | `file` | Capture a page or element, optionally against a baseline |
| `check`, `uncheck` | `selector` | Control checkboxes |
| `save-state`, `load-state` | `file` | Reuse authenticated browser state |
| `if`, `loop` | condition or iteration settings | Model branches and repeated actions |
| `evaluate`, `scroll`, `set-viewport` | step-specific parameters | Run browser-side scripts or adjust the viewport |

List the available steps or inspect any step's exact parameters before writing a flow:

```bash
pomelo-pw steps
pomelo-pw spec wait
pomelo-pw spec select
```

The [example/](example/) directory organizes runnable flows into public checks, browser interactions, and browser-state reuse. Its [README](example/README.md) describes each scenario, prerequisites, and variable overrides. The bundled [agent skill](plugins/pomelo-pw/skills/pomelo-pw/SKILL.md) contains agent-oriented guidance and reusable flow templates.

## Develop

Install the locked development environment:

```bash
uv sync --all-groups --locked
```

Run the normal quality gates directly with `uv`:

```bash
uv run --locked --no-sync ruff format --check src tests scripts
uv run --locked --no-sync ruff check src tests scripts
uv run --locked --no-sync mypy src tests scripts
uv run --locked --no-sync pytest
```

On systems with GNU Make and Bash, `make check` and `make test` wrap those commands. `make test cov=1` also writes an HTML coverage report.

### Refresh the Native Plugin

The repository packages the `pomelo-pw` skill as a native plugin. Validate the package first, then refresh the editable CLI and installed plugin for available agent clients:

```bash
uv run --locked python scripts/install.py plugin check
uv tool install --editable . --force
uv run --locked python scripts/install.py plugin apply
```

Restart the agent client after applying a plugin update so it loads the new skill.

### Build and Release

```bash
# Inspect the Git-derived release version
uv run --locked --no-sync python scripts/version_calc.py

# Apply the calculated version to pyproject.toml and uv.lock
uv run --locked --no-sync python scripts/version_calc.py --no-dry-run

# Build source and wheel distributions
uv build

# Upload existing distributions to PyPI
make pypi

# Build a standalone executable when GNU Make and Bash are available
make binary
```

`make pypi` loads `./.env` when it exists; otherwise, Twine uses the current environment, `.pypirc`, or keyring. For a PyPI API token, set `TWINE_USERNAME=__token__` and `TWINE_PASSWORD` to the token in the ignored `.env` file or in your shell environment. The target is non-interactive and will fail without usable credentials.

Release versions are derived from Git history. After reviewing the version-file changes, commit them and create the matching `vX.Y.Z` tag; GitHub Actions builds the wheel and platform binaries from that tag.

## Repository Layout

```text
src/pomelo_pw/       CLI, executor, configuration, and step implementations
tests/               Unit and integration-style tests
example/             Runnable YAML examples and usage guide
plugins/pomelo-pw/   Native plugin and agent skill
docs/                Architecture and process documentation
scripts/             Plugin synchronization and release helpers
```

## License

MIT
