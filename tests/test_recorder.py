"""Tests for the interactive recorder entrypoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pomelo_pw.config import ConfigContainer, PlaywrightConfig
from pomelo_pw.recorder import FlowRecorder, record_flow


def _playwright_context(playwright: MagicMock) -> MagicMock:
    """Create an async context manager that yields a mocked Playwright instance."""
    context_manager = MagicMock()
    context_manager.__aenter__ = AsyncMock(return_value=playwright)
    context_manager.__aexit__ = AsyncMock(return_value=None)
    return context_manager


@pytest.mark.asyncio
async def test_recorder_closes_resources_when_no_steps_are_recorded() -> None:
    """Recorder closes context and browser when recording produces no flow."""
    playwright = MagicMock()
    browser = MagicMock()
    browser.close = AsyncMock()
    context = MagicMock()
    context.close = AsyncMock()
    page = MagicMock()
    page.goto = AsyncMock()
    context.new_page = AsyncMock(return_value=page)

    with (
        patch("pomelo_pw.recorder.async_playwright", return_value=_playwright_context(playwright)),
        patch("pomelo_pw.recorder.load_app_config", return_value=ConfigContainer(PlaywrightConfig())),
        patch("pomelo_pw.recorder.BrowserLifecycle.launch", new=AsyncMock(return_value=browser)) as launch,
        patch("pomelo_pw.recorder.BrowserLifecycle.new_context", new=AsyncMock(return_value=context)) as new_context,
        patch.object(FlowRecorder, "inject_recorder_ui", new=AsyncMock()),
        patch.object(FlowRecorder, "wait_for_recording", new=AsyncMock()),
        patch.object(FlowRecorder, "get_recorded_steps", new=AsyncMock(return_value=[])),
    ):
        await record_flow("https://example.com", "recorded.yaml", headless=True)

    launch.assert_awaited_once_with(playwright, headless=True)
    new_context.assert_awaited_once_with(browser)
    page.goto.assert_awaited_once_with("https://example.com", wait_until="domcontentloaded")
    context.close.assert_awaited_once()
    browser.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_recorder_closes_resources_when_navigation_fails() -> None:
    """Recorder releases resources when page setup raises an operational error."""
    playwright = MagicMock()
    browser = MagicMock()
    browser.close = AsyncMock()
    context = MagicMock()
    context.close = AsyncMock()
    page = MagicMock()
    page.goto = AsyncMock(side_effect=RuntimeError("navigation failed"))
    context.new_page = AsyncMock(return_value=page)

    with (
        patch("pomelo_pw.recorder.async_playwright", return_value=_playwright_context(playwright)),
        patch("pomelo_pw.recorder.load_app_config", return_value=ConfigContainer(PlaywrightConfig())),
        patch("pomelo_pw.recorder.BrowserLifecycle.launch", new=AsyncMock(return_value=browser)),
        patch("pomelo_pw.recorder.BrowserLifecycle.new_context", new=AsyncMock(return_value=context)),
        pytest.raises(RuntimeError, match="navigation failed"),
    ):
        await record_flow("https://example.com", "recorded.yaml")

    context.close.assert_awaited_once()
    browser.close.assert_awaited_once()
