# Development Guide

[Home](../README.md) | [Architecture](DESIGN.md) | [简体中文](DEVELOPMENT_CN.md)

This guide is for repository contributors. See the [usage guide](USAGE.md) to run an installed CLI or use the package from another project.

## Development Setup and Checks

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

With GNU Make and Bash, `make check` runs formatting, lint, and type checks; `make test` runs tests. `make test cov=1` also writes an HTML coverage report. For a focused change, limit pytest to the relevant test files.

## Refresh the Native Plugin

The repository packages the `pomelo-pw` skill as a native plugin. Validate the package first, then refresh the editable CLI and installed plugin for available agent clients:

```bash
uv run --locked python scripts/install.py plugin check
uv tool install --editable . --force
uv run --locked python scripts/install.py plugin apply
```

Restart the agent client after applying a plugin update so it loads the new skill.

## Build and Release

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
docs/                Usage, reference, architecture, development, and process documents
scripts/             Plugin synchronization and release helpers
```

See the [architecture](DESIGN.md) for implementation responsibilities and extension contracts. `docs/requirement/`, `docs/intent/`, `docs/plan/`, and `docs/verification/` contain historical requirements, plans, and verification records. Use the [flow reference](FLOW_REFERENCE.md) for current behavior.
