SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

UV ?= uv
UV_RUN ?= $(UV) run
ARGS ?=

CHECK_FIX := $(filter 1 true yes,$(fix))
COVER_ENABLED := $(filter 1 true yes,$(cov))
RUFF_FORMAT_ARGS := --check
RUFF_CHECK_ARGS :=
COVER_ARGS :=

ifneq ($(CHECK_FIX),)
RUFF_FORMAT_ARGS :=
RUFF_CHECK_ARGS := --fix
endif

ifneq ($(COVER_ENABLED),)
COVER_ARGS := --cov=src/pomelo_pw --cov-report=term-missing --cov-report=html
endif

.PHONY: help deps install check test release clean run

help: ## Show available workflow targets.
	@printf "Usage: make <target> [fix=1] [cov=1]\n"
	@printf "\nTargets:\n"
	@printf "  deps      Sync locked development dependencies\n"
	@printf "  install   Install the CLI and synchronize the local plugin\n"
	@printf "  check     Check format, lint, and types [fix=1]\n"
	@printf "  test      Run unit tests [cov=1]\n"
	@printf "  release   Build source and wheel distributions\n"
	@printf "  run       Run pomelo-pw from the source tree [ARGS='...']\n"
	@printf "  clean     Remove local build and cache artifacts\n"

deps: ## Sync locked development dependencies without installing the project.
	$(UV) sync --all-groups --locked --no-install-project

install: ## Install the CLI and synchronize the local plugin.
	$(UV) run python scripts/release.py plugin check
	$(UV) tool install --editable . --force
	$(UV) run python scripts/release.py plugin apply

check: ## Check format, lint, and types; use fix=1 to apply fixes.
	$(UV_RUN) ruff format $(RUFF_FORMAT_ARGS) src tests
	$(UV_RUN) ruff check $(RUFF_CHECK_ARGS) src tests
	$(UV_RUN) mypy src

test: ## Run unit tests; use cov=1 to collect coverage.
	$(UV_RUN) pytest $(COVER_ARGS) tests

release: ## Build source and wheel distributions.
	$(UV) build

run: ## Run pomelo-pw from the source tree.
	$(UV_RUN) pomelo-pw $(ARGS)

clean: ## Remove explicitly listed local build and cache artifacts.
	rm -rf dist output .pytest_cache .mypy_cache .ruff_cache htmlcov coverage
	rm -f .coverage
	find . -type d -name "__pycache__" -not -path "./.git/*" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -not -path "./.git/*" -exec rm -rf {} +
