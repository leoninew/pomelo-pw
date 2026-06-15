set shell := ["bash", "-cu"]

SKILL_SRC := ".claude/skills/pomelo-pw"
SKILL_DST := env_var("HOME") + "/.claude/skills/pomelo-pw"

install:
    uv sync --group dev

dev *ARGS:
    uv run pomelo-pw {{ARGS}}

check:
    uv run ruff check --fix src tests
    uv run ruff format src tests
    uv run mypy src

test:
    uv run pytest

build:
    uv build

clean:
    find . -type d -name "__pycache__" -not -path "./.git/*" -exec rm -rf {} +
    find . -type d -name ".mypy_cache" -not -path "./.git/*" -exec rm -rf {} +
    find . -type d -name ".ruff_cache" -not -path "./.git/*" -exec rm -rf {} +
    rm -rf dist output
    find . -type d -name "*.egg-info" -exec rm -rf {} +
    rm -f .coverage
