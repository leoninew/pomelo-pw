"""Tests for error context collection."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from pomelo_pw.error_context import ErrorContext, ErrorContextCollector


class TestErrorContext:
    def test_to_dict_all_fields(self) -> None:
        ctx = ErrorContext(
            url="https://example.com",
            screenshot_path="/out/error.png",
            html_snapshot_path="/out/error.html",
            console_errors=["[ERROR] oops"],
            network_errors=[{"url": "/api", "status": 500}],
            visible_text="Something went wrong",
            step_index=2,
            step_type="click",
        )
        d = ctx.to_dict()
        assert d["url"] == "https://example.com"
        assert d["screenshot"] == "/out/error.png"
        assert d["html_snapshot"] == "/out/error.html"
        assert d["console_errors"] == ["[ERROR] oops"]
        assert d["network_errors"] == [{"url": "/api", "status": 500}]
        assert d["visible_text"] == "Something went wrong"
        assert d["step_index"] == 2
        assert d["step_type"] == "click"

    def test_to_dict_defaults(self) -> None:
        ctx = ErrorContext(url="https://example.com")
        d = ctx.to_dict()
        assert d["screenshot"] is None
        assert d["html_snapshot"] is None
        assert d["console_errors"] == []
        assert d["network_errors"] == []
        assert d["visible_text"] is None
        assert d["step_index"] == 0
        assert d["step_type"] == "unknown"


class TestErrorContextCollector:
    def _make_collector(self) -> ErrorContextCollector:
        return ErrorContextCollector()

    def test_console_error_captured(self) -> None:
        collector = self._make_collector()
        msg = MagicMock()
        msg.type = "error"
        msg.text = "Something failed"
        collector._on_console(msg)
        assert "[ERROR] Something failed" in collector.console_messages

    def test_console_warning_captured(self) -> None:
        collector = self._make_collector()
        msg = MagicMock()
        msg.type = "warning"
        msg.text = "Deprecated API"
        collector._on_console(msg)
        assert "[WARNING] Deprecated API" in collector.console_messages

    def test_console_info_ignored(self) -> None:
        collector = self._make_collector()
        msg = MagicMock()
        msg.type = "log"
        msg.text = "Just a log"
        collector._on_console(msg)
        assert len(collector.console_messages) == 0

    def test_page_error_captured(self) -> None:
        collector = self._make_collector()
        collector._on_page_error("Uncaught TypeError")
        assert "[PAGE ERROR] Uncaught TypeError" in collector.console_messages

    def test_network_error_4xx_captured(self) -> None:
        collector = self._make_collector()
        response = MagicMock()
        response.status = 404
        response.url = "https://example.com/api/missing"
        response.status_text = "Not Found"
        response.request.method = "GET"
        collector._on_response(response)
        assert len(collector.network_errors) == 1
        assert collector.network_errors[0]["status"] == 404

    def test_network_error_5xx_captured(self) -> None:
        collector = self._make_collector()
        response = MagicMock()
        response.status = 500
        response.url = "https://example.com/api/crash"
        response.status_text = "Internal Server Error"
        response.request.method = "POST"
        collector._on_response(response)
        assert len(collector.network_errors) == 1
        assert collector.network_errors[0]["status"] == 500

    def test_network_success_ignored(self) -> None:
        collector = self._make_collector()
        response = MagicMock()
        response.status = 200
        collector._on_response(response)
        assert len(collector.network_errors) == 0

    def test_network_redirect_ignored(self) -> None:
        collector = self._make_collector()
        response = MagicMock()
        response.status = 302
        collector._on_response(response)
        assert len(collector.network_errors) == 0

    def test_setup_listeners_registers_events(self) -> None:
        collector = self._make_collector()
        page = MagicMock()
        collector.setup_listeners(page)
        # Verify all three event types are registered
        assert page.on.call_count == 3
        registered_events = {c.args[0] for c in page.on.call_args_list}
        assert registered_events == {"console", "pageerror", "response"}

    @pytest.mark.asyncio
    async def test_collect_error_context_captures_url(self, tmp_path: Path) -> None:
        collector = self._make_collector()
        page = MagicMock()
        page.url = "https://example.com/fail"
        page.screenshot = AsyncMock()
        page.content = AsyncMock(return_value="<html><body>Error</body></html>")
        page.evaluate = AsyncMock(return_value="Error page text")

        ctx = await collector.collect_error_context(page=page, output_dir=tmp_path, step_index=2, step_type="click")

        assert ctx.url == "https://example.com/fail"
        assert ctx.step_index == 2
        assert ctx.step_type == "click"

    @pytest.mark.asyncio
    async def test_collect_error_context_saves_screenshot(self, tmp_path: Path) -> None:
        collector = self._make_collector()
        page = MagicMock()
        page.url = "https://example.com"
        page.screenshot = AsyncMock()
        page.content = AsyncMock(return_value="<html></html>")
        page.evaluate = AsyncMock(return_value="text")

        ctx = await collector.collect_error_context(page=page, output_dir=tmp_path, step_index=0, step_type="navigate")

        page.screenshot.assert_called_once()
        assert ctx.screenshot_path is not None
        assert "error-step-1.png" in ctx.screenshot_path

    @pytest.mark.asyncio
    async def test_collect_error_context_saves_html(self, tmp_path: Path) -> None:
        collector = self._make_collector()
        page = MagicMock()
        page.url = "https://example.com"
        page.screenshot = AsyncMock()
        page.content = AsyncMock(return_value="<html><body>content</body></html>")
        page.evaluate = AsyncMock(return_value="content")

        ctx = await collector.collect_error_context(page=page, output_dir=tmp_path, step_index=0, step_type="click")

        assert ctx.html_snapshot_path is not None
        html_file = Path(ctx.html_snapshot_path)
        assert html_file.exists()
        assert html_file.read_text(encoding="utf-8") == "<html><body>content</body></html>"

    @pytest.mark.asyncio
    async def test_collect_error_context_truncates_visible_text(self, tmp_path: Path) -> None:
        collector = self._make_collector()
        page = MagicMock()
        page.url = "https://example.com"
        page.screenshot = AsyncMock()
        page.content = AsyncMock(return_value="<html></html>")
        page.evaluate = AsyncMock(return_value="x" * 1000)

        ctx = await collector.collect_error_context(page=page, output_dir=tmp_path, step_index=0, step_type="click")

        assert ctx.visible_text is not None
        assert len(ctx.visible_text) == 500

    @pytest.mark.asyncio
    async def test_collect_error_context_includes_prior_errors(self, tmp_path: Path) -> None:
        collector = self._make_collector()
        # Simulate prior console errors
        msg = MagicMock()
        msg.type = "error"
        msg.text = "Prior error"
        collector._on_console(msg)

        page = MagicMock()
        page.url = "https://example.com"
        page.screenshot = AsyncMock()
        page.content = AsyncMock(return_value="<html></html>")
        page.evaluate = AsyncMock(return_value="")

        ctx = await collector.collect_error_context(page=page, output_dir=tmp_path, step_index=0, step_type="click")

        assert "[ERROR] Prior error" in ctx.console_errors

    @pytest.mark.asyncio
    async def test_collect_error_context_survives_screenshot_failure(self, tmp_path: Path) -> None:
        """Should not raise even if screenshot fails."""
        collector = self._make_collector()
        page = MagicMock()
        page.url = "https://example.com"
        page.screenshot = AsyncMock(side_effect=RuntimeError("page crashed"))
        page.content = AsyncMock(return_value="<html></html>")
        page.evaluate = AsyncMock(return_value="")

        ctx = await collector.collect_error_context(page=page, output_dir=tmp_path, step_index=0, step_type="click")

        assert ctx.screenshot_path is None  # Failed gracefully
