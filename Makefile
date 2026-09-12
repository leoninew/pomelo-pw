SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

UV ?= uv
UV_RUN ?= $(UV) run --locked --no-sync

CHECK_FIX := $(filter 1 true yes,$(fix))
RUFF_FORMAT_ARGS := --check
RUFF_CHECK_ARGS :=
TEST_COV_ARGS :=

ifneq ($(CHECK_FIX),)
RUFF_FORMAT_ARGS :=
RUFF_CHECK_ARGS := --fix
endif

ifneq ($(filter 1 true yes,$(cov)),)
TEST_COV_ARGS := --cov=src/pomelo_pw --cov-report=term-missing --cov-report=html
endif

.PHONY: help deps install check test version release pypi binary

help: ## Show available workflow targets.
	@printf "Usage: make <target> [fix=1] [cov=1]\n"
	@printf "\nTargets:\n"
	@printf "  deps      Sync locked dependencies and install the project\n"
	@printf "  install   Install the CLI and synchronize the local plugin\n"
	@printf "  check     Check format, lint, and types [fix=1]\n"
	@printf "  test      Run unit tests [cov=1]\n"
	@printf "  version   Calculate the Git-derived version [apply=1]\n"
	@printf "  release   Build source and wheel distributions\n"
	@printf "  pypi      Upload the pyproject.toml version's dist artifacts to PyPI\n"
	@printf "  binary    Build a standalone pomelo-pw executable\n"

deps: ## Sync locked development dependencies and install the project.
	$(UV) sync --all-groups --locked

install: ## Install the CLI and synchronize the local plugin.
	$(UV) run --locked python scripts/install.py plugin check
	$(UV) tool install --editable . --force
	$(UV) run --locked python scripts/install.py plugin apply

check: ## Check format, lint, and types; use fix=1 to apply fixes.
	$(UV_RUN) ruff format $(RUFF_FORMAT_ARGS) src tests scripts
	$(UV_RUN) ruff check $(RUFF_CHECK_ARGS) src tests scripts
	$(UV_RUN) mypy src tests scripts

test: ## Run unit tests; use cov=1 to collect coverage.
	$(UV_RUN) pytest $(TEST_COV_ARGS)

version: ## Calculate the Git-derived project version; use apply=1 to update version files.
ifeq ($(apply),1)
	$(UV_RUN) python scripts/version_calc.py --no-dry-run
else
	$(UV_RUN) python scripts/version_calc.py
endif

release: ## Build source and wheel distributions.
	$(UV) build

# version_calc.py writes [project].version; uv version reads that same field.
VERSION = $(shell $(UV) version --short)
DIST_NAME = $(subst -,_,pomelo-pw)
PYPI_ENV_FILE ?= .env
PYPI_ENV_ARGS := $(if $(wildcard $(PYPI_ENV_FILE)),--env-file $(PYPI_ENV_FILE))

pypi: ## Upload the current package version's sdist and wheel to PyPI.
	$(if $(VERSION),,$(error could not read [project].version from pyproject.toml))
	$(if $(wildcard dist/$(DIST_NAME)-$(VERSION).tar.gz),,$(error Missing dist/$(DIST_NAME)-$(VERSION).tar.gz))
	$(if $(wildcard dist/$(DIST_NAME)-$(VERSION)-py3-none-any.whl),,$(error Missing dist/$(DIST_NAME)-$(VERSION)-py3-none-any.whl))
	$(UV) tool run $(PYPI_ENV_ARGS) twine upload --non-interactive \
		"dist/$(DIST_NAME)-$(VERSION).tar.gz" \
		"dist/$(DIST_NAME)-$(VERSION)-py3-none-any.whl"

binary: ## Build a standalone executable that uses a system Chrome installation.
	$(UV_RUN) pyinstaller --noconfirm --clean --onefile --name pomelo-pw --paths src --workpath build/pyinstaller --specpath build/pyinstaller --collect-all playwright --copy-metadata pomelo-pw src/pomelo_pw/__main__.py
