"""Tests for shared Playwright browser setup."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from pomelo_pw.browser import BrowserLifecycle
from pomelo_pw.config import PlaywrightConfig, ViewportConfig


class TestBrowserLifecycle:
    """Tests for BrowserLifecycle."""

    @pytest.mark.asyncio
    async def test_launch_forwards_runtime_options(self) -> None:
        """Launch forwards explicit headless and configured runtime values."""
        config = PlaywrightConfig(timeout=60000, slow_mo=150)
        lifecycle = BrowserLifecycle(config)
        browser = MagicMock()
        playwright = MagicMock()
        playwright.chromium.launch = AsyncMock(return_value=browser)

        result = await lifecycle.launch(playwright, headless=False)

        assert result is browser
        playwright.chromium.launch.assert_awaited_once_with(
            headless=False,
            timeout=60000,
            slow_mo=150,
        )

    @pytest.mark.asyncio
    async def test_launch_includes_configured_executable_path(self) -> None:
        """Launch includes an executable path only when configuration provides one."""
        config = PlaywrightConfig(executable_path="/usr/bin/chromium")
        lifecycle = BrowserLifecycle(config)
        playwright = MagicMock()
        playwright.chromium.launch = AsyncMock()

        await lifecycle.launch(playwright, headless=True)

        playwright.chromium.launch.assert_awaited_once_with(
            headless=True,
            timeout=30000,
            slow_mo=0,
            executable_path="/usr/bin/chromium",
        )

    @pytest.mark.asyncio
    async def test_new_context_uses_configured_viewport(self) -> None:
        """Every consumer receives a context with the configured viewport."""
        config = PlaywrightConfig(viewport=ViewportConfig(width=1920, height=1080))
        lifecycle = BrowserLifecycle(config)
        context = MagicMock()
        browser = MagicMock()
        browser.new_context = AsyncMock(return_value=context)

        result = await lifecycle.new_context(browser)

        assert result is context
        browser.new_context.assert_awaited_once_with(viewport={"width": 1920, "height": 1080})

    @pytest.mark.asyncio
    async def test_executor_closes_context_when_page_setup_fails(self) -> None:
        """Executor closes its context when creating a page raises unexpectedly."""
        from pomelo_pw.executor import FlowExecutor

        executor = FlowExecutor()
        browser = MagicMock()
        context = MagicMock()
        context.close = AsyncMock()
        context.new_page = AsyncMock(side_effect=RuntimeError("page setup failed"))
        executor.browser_lifecycle.new_context = AsyncMock(return_value=context)

        with pytest.raises(RuntimeError, match="page setup failed"):
            await executor._run_once(
                browser=browser,
                flow={"name": "test"},
                flow_path=MagicMock(stem="test"),
                steps=[],
                global_vars={},
                output=MagicMock(),
                start_time=0,
            )

        context.close.assert_awaited_once()
