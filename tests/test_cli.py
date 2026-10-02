"""Tests for browser command dispatch."""

import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from pomelo_pw import __version__
from pomelo_pw.cli import cli
from pomelo_pw.reporting import ExecutionReport


def _report(message: str | None = None, row_label: str | None = None) -> dict[str, Any]:
    report = ExecutionReport()
    if message:
        report.add_error(ValueError(message), "1", "wait")
    result = report.result("sample", 10, screenshots=["ready.png"] if not message else [], completed=2)
    if row_label:
        result["errors"][0]["row"] = {"index": 1, "label": row_label}
    return result


def test_version_reports_package_version() -> None:
    """The root CLI reports the installed package version."""
    result = CliRunner().invoke(cli, ["--version"])

    assert result.exit_code == 0
    assert result.output == f"cli, version {__version__}\n"


def test_evaluate_spec_exposes_structured_args_and_binding() -> None:
    result = CliRunner().invoke(cli, ["spec", "evaluate"])
    assert result.exit_code == 0
    assert "args:" in result.output
    assert "save_as:" in result.output
    assert "save_as:" not in CliRunner().invoke(cli, ["spec", "click"]).output


class TestBrowserCommands:
    """Tests for interactive browser command dispatch."""

    def test_explore_forwards_headless_option(self) -> None:
        """Explore dispatches its URL and explicit headless flag."""
        runner = CliRunner()

        with patch("pomelo_pw.explorer.explore_page", new=AsyncMock()) as explore_page:
            result = runner.invoke(cli, ["explore", "https://example.com", "--headless"])

        assert result.exit_code == 0
        explore_page.assert_awaited_once_with("https://example.com", headless=True)

    def test_record_defaults_to_visible_browser(self) -> None:
        """Record preserves its visible-browser default when flag is omitted."""
        runner = CliRunner()

        with patch("pomelo_pw.recorder.record_flow", new=AsyncMock()) as record_flow:
            result = runner.invoke(cli, ["record", "https://example.com", "recorded.yaml"])

        assert result.exit_code == 0
        record_flow.assert_awaited_once_with("https://example.com", "recorded.yaml", headless=False)

    def test_install_uses_playwright_driver(self) -> None:
        """The install command works both from source and a frozen executable."""
        runner = CliRunner()

        with (
            patch("pomelo_pw.cli.compute_driver_executable", return_value=("node", "cli.js")),
            patch("pomelo_pw.cli.get_driver_env", return_value={}),
            patch("pomelo_pw.cli.subprocess.run") as run,
        ):
            result = runner.invoke(cli, ["install"])

        assert result.exit_code == 0
        run.assert_called_once_with(
            ["node", "cli.js", "install", "chromium"],
            check=True,
            env={},
        )


class TestRunCommand:
    """Tests for flow runtime option dispatch."""

    def test_missing_flow_returns_json_startup_error(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            result = runner.invoke(cli, ["run", "missing.yaml", "--json"])
        assert result.exit_code == 1
        payload = json.loads(result.stdout)
        assert payload["status"] == "failed"
        assert payload["errors"][0]["error_type"] == "FileNotFoundError"
        assert payload["errors"][0]["kind"] == "startup"
        assert "Loading flow" in result.stderr

    def test_run_json_success_exits_zero(self) -> None:
        payload = _report()
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("sample.yaml").write_text("steps: []\n", encoding="utf-8")
            with patch("pomelo_pw.cli.FlowExecutor") as executor_class:
                executor_class.return_value.run_flow = AsyncMock(return_value=payload)
                result = runner.invoke(cli, ["run", "sample.yaml", "--json"])

        assert result.exit_code == 0
        assert json.loads(result.stdout) == payload
        assert result.stderr == ""

    @pytest.mark.parametrize(
        "payload",
        [
            _report("Condition timed out after 25ms"),
            _report("Row failed", "second"),
        ],
        ids=["flow", "data-driven"],
    )
    def test_run_json_failure_exits_one_preserving_result(self, payload: dict[str, Any]) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("sample.yaml").write_text("steps: []\n", encoding="utf-8")
            with patch("pomelo_pw.cli.FlowExecutor") as executor_class:
                executor_class.return_value.run_flow = AsyncMock(return_value=payload)
                result = runner.invoke(cli, ["run", "sample.yaml", "--json"])

        assert result.exit_code == 1
        assert json.loads(result.stdout) == payload
        assert result.stderr == ""

    def test_run_json_exception_exits_one_preserving_error(self) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("sample.yaml").write_text("steps: []\n", encoding="utf-8")
            with patch("pomelo_pw.cli.FlowExecutor") as executor_class:
                executor_class.return_value.run_flow = AsyncMock(side_effect=ValueError("Invalid wait condition"))
                result = runner.invoke(cli, ["run", "sample.yaml", "--json"])

        assert result.exit_code == 1
        payload = json.loads(result.stdout)
        assert payload["schema_version"] == 1
        assert payload["status"] == "failed"
        assert payload["errors"][0]["message"] == "Invalid wait condition"
        assert payload["errors"][0]["kind"] == "startup"
        assert result.stderr == ""

    @pytest.mark.parametrize(
        ("payload", "expected"),
        [
            (_report("Invalid flow"), "Invalid flow"),
            (
                _report("extract rows[0].fields.name: element is missing"),
                "extract rows[0].fields.name: element is missing",
            ),
            (
                _report("Missing field", "second"),
                "Row second: Missing field",
            ),
        ],
        ids=["flow-error", "failed-step", "data-row"],
    )
    def test_run_text_failure_preserves_original_reason(self, payload: dict[str, Any], expected: str) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("sample.yaml").write_text("steps: []\n", encoding="utf-8")
            with patch("pomelo_pw.cli.FlowExecutor") as executor_class:
                executor_class.return_value.run_flow = AsyncMock(return_value=payload)
                result = runner.invoke(cli, ["run", "sample.yaml"])

        assert result.exit_code == 1
        assert result.stderr == f"Failed: {expected}\n"
        assert result.stdout == ""

    def test_run_reports_data_driven_summary(self) -> None:
        runner = CliRunner()
        payload = _report()
        payload["row_summary"] = {"total": 3, "executed": 3, "passed": 3, "failed": 0}
        payload["artifacts"]["screenshots"] = ["homepage.png", "a.png", "b.png"]
        with runner.isolated_filesystem():
            Path("sample.yaml").write_text("steps: []\n", encoding="utf-8")
            with patch("pomelo_pw.cli.FlowExecutor") as executor_class:
                executor_class.return_value.run_flow = AsyncMock(return_value=payload)
                result = runner.invoke(cli, ["run", "sample.yaml"])

        assert result.exit_code == 0
        assert result.output == "Completed: 3/3 rows, 3 screenshots\n"

    def test_run_leaves_output_unset_for_flow_configuration(self) -> None:
        """Flow output_dir remains available when the CLI option is omitted."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            Path("sample.yaml").write_text("steps: []\n", encoding="utf-8")
            with patch("pomelo_pw.cli.FlowExecutor") as executor_class:
                executor_class.return_value.run_flow = AsyncMock(return_value=_report())
                result = runner.invoke(cli, ["run", "sample.yaml"])

        assert result.exit_code == 0
        assert executor_class.return_value.run_flow.call_args.kwargs["output_dir"] is None
        assert executor_class.return_value.run_flow.call_args.kwargs["headless"] is None

    def test_run_passes_explicit_output_as_cli_override(self) -> None:
        """An explicit CLI output directory takes precedence over flow configuration."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            Path("sample.yaml").write_text("steps: []\n", encoding="utf-8")
            with patch("pomelo_pw.cli.FlowExecutor") as executor_class:
                executor_class.return_value.run_flow = AsyncMock(return_value=_report())
                result = runner.invoke(cli, ["run", "sample.yaml", "-o", "artifacts"])

        assert result.exit_code == 0
        assert executor_class.return_value.run_flow.call_args.kwargs["output_dir"] == Path("artifacts")

    def test_run_passes_headless_as_cli_override(self) -> None:
        """The explicit headless flag overrides the flow declaration."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            Path("sample.yaml").write_text("steps: []\n", encoding="utf-8")
            with patch("pomelo_pw.cli.FlowExecutor") as executor_class:
                executor_class.return_value.run_flow = AsyncMock(return_value=_report())
                result = runner.invoke(cli, ["run", "sample.yaml", "--headless"])

        assert result.exit_code == 0
        assert executor_class.return_value.run_flow.call_args.kwargs["headless"] is True

    def test_json_redirects_execution_logs_to_stderr(self) -> None:
        import click

        async def execute(*args: Any, **kwargs: Any) -> dict[str, Any]:
            click.echo("Loading flow")
            print("[console] read completed")
            return _report()

        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("sample.yaml").write_text("steps: []\n", encoding="utf-8")
            with patch("pomelo_pw.cli.FlowExecutor") as executor_class:
                executor_class.return_value.run_flow = execute
                result = runner.invoke(cli, ["run", "sample.yaml", "--json", "--verbose"])
        assert result.exit_code == 0
        assert json.loads(result.stdout)["status"] == "passed"
        assert result.stderr == "Loading flow\n[console] read completed\n"


class TestValidateCommand:
    """Validation failures are visible to both people and calling processes."""

    @pytest.mark.parametrize(
        ("valid", "json_output"),
        [(True, True), (False, False), (False, True)],
        ids=["valid-json", "invalid-text", "invalid-json"],
    )
    def test_validate_exit_status_matches_report(self, valid: bool, json_output: bool) -> None:
        runner = CliRunner()
        with runner.isolated_filesystem():
            Path("sample.yaml").write_text("steps: []\n" if valid else "steps:\n  - type: wait\n", encoding="utf-8")
            result = runner.invoke(cli, ["validate", "sample.yaml", *(["--json"] if json_output else [])])

        assert result.exit_code == (0 if valid else 1)
        assert result.stderr == ""
        if json_output:
            payload = json.loads(result.stdout)
            assert payload["valid"] is valid
            if valid:
                assert payload["errors"] == []
            else:
                assert payload["errors"]
                assert "steps[0] (wait)" in payload["errors"][0]
        else:
            assert "Validation failed:" in result.stdout
            assert "steps[0] (wait)" in result.stdout
