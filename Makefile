SHELL := bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

SKILL_SRC := .claude/skills/pomelo-pw
CLAUDE_SKILL_DST := $(HOME)/.claude/skills/pomelo-pw
CODEX_SKILL_DST := $(HOME)/.codex/skills/pomelo-pw
GROK_SKILL_DST := $(HOME)/.grok/skills/pomelo-pw
ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))

.PHONY: help install run check test build release clean

help:
	@printf "Available targets:\n"
	@printf "  install  Install development dependencies\n"
	@printf "  run      Run pomelo-pw CLI, optionally with ARGS='...'\n"
	@printf "  check    Run ruff and mypy checks\n"
	@printf "  test     Run pytest\n"
	@printf "  build    Build package distributions\n"
	@printf "  release  Install package and sync skill files to Claude, Codex, and Grok\n"
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
	pip install -e .
	test -f "$(SKILL_SRC)/skill.md" || { printf '%s\n' "Missing skill source: $(SKILL_SRC)/skill.md" >&2; exit 1; }
	mkdir -p "$(CLAUDE_SKILL_DST)" "$(CODEX_SKILL_DST)" "$(GROK_SKILL_DST)"
	rsync -av "$(SKILL_SRC)"/ "$(CLAUDE_SKILL_DST)"/ --del
	rm -f "$(CODEX_SKILL_DST)/SKILL.md"
	rsync -av "$(SKILL_SRC)"/ "$(CODEX_SKILL_DST)"/ --del
	mv "$(CODEX_SKILL_DST)/skill.md" "$(CODEX_SKILL_DST)/SKILL.md"
	# Grok discovers the conventional uppercase SKILL.md entrypoint.
	rm -f "$(GROK_SKILL_DST)/SKILL.md"
	rsync -av "$(SKILL_SRC)"/ "$(GROK_SKILL_DST)"/ --del
	mv "$(GROK_SKILL_DST)/skill.md" "$(GROK_SKILL_DST)/SKILL.md"
	printf '%s\n' "Installed pomelo-pw package in editable mode."
	printf '%s\n' "Synced pomelo-pw skill files to $(CLAUDE_SKILL_DST)"
	printf '%s\n' "Synced pomelo-pw skill files to $(CODEX_SKILL_DST)"
	printf '%s\n' "Synced pomelo-pw skill files to $(GROK_SKILL_DST)"

clean:
	find . -type d -name "__pycache__" -not -path "./.git/*" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -not -path "./.git/*" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -not -path "./.git/*" -exec rm -rf {} +
	rm -rf dist output
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -f .coverage

%:
	@:
