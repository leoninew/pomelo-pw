"""Tests for browser command dispatch."""

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
