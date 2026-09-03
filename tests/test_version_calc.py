"""Tests for Git-history version calculation and uv metadata updates."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "scripts" / "version_calc.py"
SPEC = importlib.util.spec_from_file_location("pomelo_pw_version_calc", SCRIPT)
assert SPEC is not None
assert SPEC.loader is not None
version_calc = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = version_calc
SPEC.loader.exec_module(version_calc)


def test_calculate_version_resets_patch_for_feature_commits(monkeypatch: pytest.MonkeyPatch) -> None:
    """Feature subjects advance the minor version; every other subject advances patch."""
    commits = iter(
        [
            ("a" * 40, "2026-01-01T00:00:00Z", "chore: initial setup"),
            ("b" * 40, "2026-01-02T00:00:00Z", " feat: add browser command"),
            ("c" * 40, "2026-01-03T00:00:00Z", "fix: handle timeout"),
            ("d" * 40, "2026-01-04T00:00:00Z", "FEAT: add recorder"),
        ]
    )
    monkeypatch.setattr(version_calc, "iter_commits", lambda: commits)

    assert version_calc.calculate_version(print_history=False) == "0.2.0"


def test_main_only_applies_version_with_no_dry_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """The default is a dry run; metadata changes require the explicit flag."""
    applied: list[str] = []

    monkeypatch.setattr(version_calc, "calculate_version", lambda **_: "0.2.0")
    monkeypatch.setattr(version_calc, "apply_version", applied.append)

    assert version_calc.main(["--quiet"]) == 0
    assert applied == []

    assert version_calc.main(["--quiet", "--no-dry-run"]) == 0
    assert applied == ["0.2.0"]


def test_prepare_project_version_update_only_changes_project_version(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """The apply path preserves non-project version fields and CRLF newlines."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_bytes(
        b'[project]\r\nname = "pomelo-pw"\r\nversion = "0.3.1"\r\n\r\n[tool.example]\r\nversion = "keep"\r\n'
    )
    monkeypatch.setattr(version_calc, "PYPROJECT_FILE", pyproject)

    previous, updated = version_calc.prepare_project_version_update("0.14.0")

    assert previous == "0.3.1"
    assert updated == (
        b'[project]\r\nname = "pomelo-pw"\r\nversion = "0.14.0"\r\n\r\n[tool.example]\r\nversion = "keep"\r\n'
    )


def test_apply_version_refreshes_uv_lock(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Applying a version updates pyproject.toml and refreshes its uv lock file."""
    pyproject = tmp_path / "pyproject.toml"
    lock = tmp_path / "uv.lock"
    pyproject.write_text('[project]\nname = "pomelo-pw"\nversion = "0.3.1"\n', encoding="utf-8")
    lock.write_text('[[package]]\nname = "pomelo-pw"\nversion = "0.3.1"\n', encoding="utf-8")
    calls: list[tuple[str, ...]] = []

    def refresh_lock(*args: str) -> None:
        calls.append(args)
        if args == ("lock",):
            lock.write_text('[[package]]\nname = "pomelo-pw"\nversion = "0.14.0"\n', encoding="utf-8")

    monkeypatch.setattr(version_calc, "PYPROJECT_FILE", pyproject)
    monkeypatch.setattr(version_calc, "UV_LOCK_FILE", lock)
    monkeypatch.setattr(version_calc, "run_uv", refresh_lock)

    version_calc.apply_version("0.14.0")

    assert 'version = "0.14.0"' in pyproject.read_text(encoding="utf-8")
    assert 'version = "0.14.0"' in lock.read_text(encoding="utf-8")
    assert calls == [("lock",)]


def test_apply_version_restores_metadata_when_uv_lock_fails(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """A failed lock refresh leaves both version files at their original contents."""
    pyproject = tmp_path / "pyproject.toml"
    lock = tmp_path / "uv.lock"
    original_pyproject = '[project]\nname = "pomelo-pw"\nversion = "0.3.1"\n'
    original_lock = '[[package]]\nname = "pomelo-pw"\nversion = "0.3.1"\n'
    pyproject.write_text(original_pyproject, encoding="utf-8")
    lock.write_text(original_lock, encoding="utf-8")

    def fail_lock(*args: str) -> None:
        raise RuntimeError(f"uv failed for {args}")

    monkeypatch.setattr(version_calc, "PYPROJECT_FILE", pyproject)
    monkeypatch.setattr(version_calc, "UV_LOCK_FILE", lock)
    monkeypatch.setattr(version_calc, "run_uv", fail_lock)

    with pytest.raises(RuntimeError, match="uv failed"):
        version_calc.apply_version("0.14.0")

    assert pyproject.read_text(encoding="utf-8") == original_pyproject
    assert lock.read_text(encoding="utf-8") == original_lock
