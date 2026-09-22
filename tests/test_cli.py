"""Tests for browser command dispatch."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

from click.testing import CliRunner

from pomelo_pw.cli import cli


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

    def test_run_leaves_output_unset_for_flow_configuration(self) -> None:
        """Flow output_dir remains available when the CLI option is omitted."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            Path("sample.yaml").write_text("steps: []\n", encoding="utf-8")
            with patch("pomelo_pw.cli.FlowExecutor") as executor_class:
                executor_class.return_value.run_flow = AsyncMock(
                    return_value={"success": True, "steps_executed": 0, "screenshots": []}
                )
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
                executor_class.return_value.run_flow = AsyncMock(
                    return_value={"success": True, "steps_executed": 0, "screenshots": []}
                )
                result = runner.invoke(cli, ["run", "sample.yaml", "-o", "artifacts"])

        assert result.exit_code == 0
        assert executor_class.return_value.run_flow.call_args.kwargs["output_dir"] == Path("artifacts")

    def test_run_passes_headless_as_cli_override(self) -> None:
        """The explicit headless flag overrides the flow declaration."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            Path("sample.yaml").write_text("steps: []\n", encoding="utf-8")
            with patch("pomelo_pw.cli.FlowExecutor") as executor_class:
                executor_class.return_value.run_flow = AsyncMock(
                    return_value={"success": True, "steps_executed": 0, "screenshots": []}
                )
                result = runner.invoke(cli, ["run", "sample.yaml", "--headless"])

        assert result.exit_code == 0
        assert executor_class.return_value.run_flow.call_args.kwargs["headless"] is True
