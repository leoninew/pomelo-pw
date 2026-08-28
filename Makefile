SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

UV ?= uv
UV_RUN ?= $(UV) run --locked --no-sync
VERSION_ARGS ?=

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

.PHONY: help deps install check test version release binary clean

help: ## Show available workflow targets.
	@printf "Usage: make <target> [fix=1] [cov=1]\n"
	@printf "\nTargets:\n"
	@printf "  deps      Sync locked dependencies and install the project\n"
	@printf "  install   Install the CLI and synchronize the local plugin\n"
	@printf "  check     Check format, lint, and types [fix=1]\n"
	@printf "  test      Run unit tests [cov=1]\n"
	@printf "  version   Calculate version [VERSION_ARGS='--quiet --apply']\n"
	@printf "  release   Build source and wheel distributions\n"
	@printf "  binary    Build a standalone pomelo-pw executable\n"
	@printf "  clean     Remove local build and cache artifacts\n"

deps: ## Sync locked development dependencies and install the project.
	$(UV) sync --all-groups --locked

install: ## Install the CLI and synchronize the local plugin.
	$(UV) run --locked python scripts/install.py plugin check
	$(UV) tool install --editable . --force
	$(UV) run --locked python scripts/install.py plugin apply

check: ## Check format, lint, and types; use fix=1 to apply fixes.
	$(UV_RUN) ruff format $(RUFF_FORMAT_ARGS) src tests
	$(UV_RUN) ruff check $(RUFF_CHECK_ARGS) src tests
	$(UV_RUN) mypy src

test: ## Run unit tests; use cov=1 to collect coverage.
	$(UV_RUN) pytest $(COVER_ARGS) tests

version: ## Calculate or apply the Git-derived project version.
	$(UV_RUN) python scripts/version_calc.py $(VERSION_ARGS)

release: ## Build source and wheel distributions.
	$(UV) build

binary: ## Build a standalone executable that uses a system Chrome installation.
	$(UV_RUN) pyinstaller --noconfirm --clean --onefile --name pomelo-pw --paths src --workpath build/pyinstaller --specpath build/pyinstaller --collect-all playwright --copy-metadata pomelo-pw src/pomelo_pw/__main__.py

clean: ## Remove explicitly listed local build and cache artifacts.
	rm -rf build dist output .pytest_cache .mypy_cache .ruff_cache htmlcov coverage
	rm -f .coverage
	find . -type d -name "__pycache__" -not -path "./.git/*" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -not -path "./.git/*" -exec rm -rf {} +
