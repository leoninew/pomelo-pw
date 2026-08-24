SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))

.PHONY: help install run check test build release clean

help:
	@printf "Available targets:\n"
	@printf "  install  Install development dependencies\n"
	@printf "  run      Run pomelo-pw CLI, optionally with ARGS='...'\n"
	@printf "  check    Run ruff and mypy checks\n"
	@printf "  test     Run pytest\n"
	@printf "  build    Build package distributions\n"
	@printf "  release  Preflight, editable-install, and publish the native plugin\n"
	@printf "  clean    Remove local build and cache artifacts\n"

install:
	uv sync --group dev

run:
	uv run pomelo-pw $(ARGS)

check:
	uv run ruff check --fix src tests
	uv run ruff format src tests
	uv run mypy src

test:
	uv run pytest

build:
	uv build

release:
	python scripts/release.py plugin check
	python -m pip install -e .
	python scripts/release.py plugin apply

clean:
	find . -type d -name "__pycache__" -not -path "./.git/*" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -not -path "./.git/*" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -not -path "./.git/*" -exec rm -rf {} +
	rm -rf dist output
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -f .coverage

%:
	@:
