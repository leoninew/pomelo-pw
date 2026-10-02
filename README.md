# Pomelo PW

[![CI](https://github.com/leoninew/pomelo-pw/actions/workflows/ci.yml/badge.svg)](https://github.com/leoninew/pomelo-pw/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/pomelo-pw)](https://pypi.org/project/pomelo-pw/)
[![GitHub Release](https://img.shields.io/github/v/release/leoninew/pomelo-pw)](https://github.com/leoninew/pomelo-pw/releases)

[English](README.md) | [简体中文](README_CN.md)

Pomelo PW is a Playwright-powered CLI for browser automation. It runs declarative YAML flows, so browser checks can live alongside application code without requiring a custom test harness.

It is intended for repeatable UI checks, scripted workflows, visual comparisons, and agent-assisted browser tasks. Flows validate their parameters before execution and collect screenshots, page snapshots, console errors, and network failures when a step fails.

## What It Provides

- YAML browser flows: navigation, forms, waits, screenshots, and login-state reuse
- Typed runtime data, DOM extraction, session HTTP requests, conditions, iteration, polling, and assertions
- Retries, data-driven runs, structured reports, and screenshot baseline comparison
- CLI, Python package integration, and native plugins for Claude Code, Codex, and Grok Build

## Install

The Python package requires Python 3.12+. Install it with [uv](https://docs.astral.sh/uv/):

```bash
uv tool install pomelo-pw
pomelo-pw install
```

The package is available on [PyPI](https://pypi.org/project/pomelo-pw/). Standalone Windows, macOS, and Linux executables are available from [GitHub Releases](https://github.com/leoninew/pomelo-pw/releases). See the [usage guide](docs/USAGE.md) for browser selection, optional dependencies, and package integration.

## Quick Start

Create `smoke.yaml`:

```yaml
name: example-smoke
variables:
  base_url: "https://the-internet.herokuapp.com"
steps:
  - type: navigate
    url: "{{base_url}}"
  - type: screenshot
    file: homepage.png
```

Validate and run:

```bash
pomelo-pw validate smoke.yaml
pomelo-pw run smoke.yaml --headless
```

Artifacts are written to `smoke/` under the working directory by default. Use `-o <directory>` to override the output location or `--var key=value` to override flow variables.

## Documentation

| Document | Contents |
| --- | --- |
| [Usage guide](docs/USAGE.md) | CLI, authoring flows, login-state reuse, Python API, and common run options |
| [Flow reference](docs/FLOW_REFERENCE.md) | Step overview, data references, conditions, waits, polling, requests, extraction, and reports |
| [Examples](example/README.md) | Runnable YAML, prerequisites, and combined workflows |
| [Development guide](docs/DEVELOPMENT.md) | Development setup, checks, plugin synchronization, builds, and releases |
| [Architecture](docs/DESIGN.md) | Internal modules, execution lifecycle, scopes, retries, and timeout boundaries (Chinese) |
| [Agent skill](plugins/pomelo-pw/skills/pomelo-pw/SKILL.md) | Agent instructions and flow templates |

## License

MIT
