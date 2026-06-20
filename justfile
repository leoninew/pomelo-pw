set shell := ["bash", "-cu"]

SKILL_SRC := ".claude/skills/pomelo-pw"
CLAUDE_SKILL_DST := env_var("HOME") + "/.claude/skills/pomelo-pw"
CODEX_SKILL_DST := env_var("HOME") + "/.codex/skills/pomelo-pw"

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

@release:
    pip install -e .
    test -f "{{SKILL_SRC}}/skill.md" || { printf '%s\n' "Missing skill source: {{SKILL_SRC}}/skill.md" >&2; exit 1; }
    mkdir -p "{{CLAUDE_SKILL_DST}}" "{{CODEX_SKILL_DST}}"
    rsync -av "{{SKILL_SRC}}"/ "{{CLAUDE_SKILL_DST}}"/ --del
    rsync -av "{{SKILL_SRC}}"/ "{{CODEX_SKILL_DST}}"/ --del
    printf '%s\n' "Installed pomelo-pw package in editable mode."
    printf '%s\n' "Synced pomelo-pw skill files to {{CLAUDE_SKILL_DST}}"
    printf '%s\n' "Synced pomelo-pw skill files to {{CODEX_SKILL_DST}}"

clean:
    find . -type d -name "__pycache__" -not -path "./.git/*" -exec rm -rf {} +
    find . -type d -name ".mypy_cache" -not -path "./.git/*" -exec rm -rf {} +
    find . -type d -name ".ruff_cache" -not -path "./.git/*" -exec rm -rf {} +
    rm -rf dist output
    find . -type d -name "*.egg-info" -exec rm -rf {} +
    rm -f .coverage
