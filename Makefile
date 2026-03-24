.PHONY: install test lint check clean build skill example help

# Skill installation paths
SKILL_SRC = .claude/skills/pomelo-pw
SKILL_DST = $(HOME)/.claude/skills/pomelo-pw

help:
	@echo "Available targets:"
	@echo "  install      - Install dependencies and Playwright browsers"
	@echo "  test         - Run tests"
	@echo "  lint         - Run ruff and mypy checks"
	@echo "  check        - Run all checks (lint + test)"
	@echo "  build        - Build wheel package"
	@echo "  skill        - Install skill to Claude Code"
	@echo "  clean        - Clean build artifacts"
	@echo "  example      - Run example flow"

install:
	uv sync
	uv run pomelo-pw install

test:
	uv run pytest tests/ -v

check:
	uv run ruff format src/ tests/
	uv run ruff check src/ tests/ --fix
	uv run mypy src/ tests/

build:
	uv build

skill:
	@echo "Installing pomelo-pw skill to $(SKILL_DST)..."
	@mkdir -p $(SKILL_DST)
	rsync -av --delete $(SKILL_SRC)/ $(SKILL_DST)/
	@echo "Done. Skill installed to $(SKILL_DST)"

clean:
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf dist
	rm -rf output
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +

example:
	uv run pomelo-pw run flows/example.yaml -v