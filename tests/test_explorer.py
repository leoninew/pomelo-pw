"""Tests for the interactive explorer entrypoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pomelo_pw.config import ConfigContainer, PlaywrightConfig
from pomelo_pw.explorer import PageExplorer, explore_page


def _playwright_context(playwright: MagicMock) -> MagicMock:
    """Create an async context manager that yields a mocked Playwright instance."""
    context_manager = MagicMock()
    context_manager.__aenter__ = AsyncMock(return_value=playwright)
    context_manager.__aexit__ = AsyncMock(return_value=None)
    return context_manager


@pytest.mark.asyncio
async def test_explorer_uses_shared_lifecycle_and_closes_resources() -> None:
    """Explorer forwards headless mode and closes context before browser."""
    playwright = MagicMock()
    browser = MagicMock()
    browser.close = AsyncMock()
    context = MagicMock()
    context.close = AsyncMock()
    page = MagicMock()
    page.goto = AsyncMock()
    context.new_page = AsyncMock(return_value=page)

    with (
        patch("pomelo_pw.explorer.async_playwright", return_value=_playwright_context(playwright)),
        patch("pomelo_pw.explorer.load_app_config", return_value=ConfigContainer(PlaywrightConfig())),
        patch("pomelo_pw.explorer.BrowserLifecycle.launch", new=AsyncMock(return_value=browser)) as launch,
        patch("pomelo_pw.explorer.BrowserLifecycle.new_context", new=AsyncMock(return_value=context)) as new_context,
        patch.object(PageExplorer, "inject_explorer_ui", new=AsyncMock()),
        patch.object(PageExplorer, "wait_for_selection", new=AsyncMock(side_effect=KeyboardInterrupt)),
    ):
        await explore_page("https://example.com", headless=True)

    launch.assert_awaited_once_with(playwright, headless=True)
    new_context.assert_awaited_once_with(browser)
    page.goto.assert_awaited_once_with("https://example.com", wait_until="domcontentloaded")
    context.close.assert_awaited_once()
    browser.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_explorer_closes_resources_when_navigation_fails() -> None:
    """Explorer releases resources when page setup raises an operational error."""
    playwright = MagicMock()
    browser = MagicMock()
    browser.close = AsyncMock()
    context = MagicMock()
    context.close = AsyncMock()
    page = MagicMock()
    page.goto = AsyncMock(side_effect=RuntimeError("navigation failed"))
    context.new_page = AsyncMock(return_value=page)

    with (
        patch("pomelo_pw.explorer.async_playwright", return_value=_playwright_context(playwright)),
        patch("pomelo_pw.explorer.load_app_config", return_value=ConfigContainer(PlaywrightConfig())),
        patch("pomelo_pw.explorer.BrowserLifecycle.launch", new=AsyncMock(return_value=browser)),
        patch("pomelo_pw.explorer.BrowserLifecycle.new_context", new=AsyncMock(return_value=context)),
        pytest.raises(RuntimeError, match="navigation failed"),
    ):
        await explore_page("https://example.com")

    context.close.assert_awaited_once()
    browser.close.assert_awaited_once()
