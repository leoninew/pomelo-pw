"""Shared Playwright browser setup."""

from __future__ import annotations

from typing import Any

from playwright.async_api import Browser, BrowserContext, Playwright

from pomelo_pw.config import PlaywrightConfig


class BrowserLifecycle:
    """Create browser resources from the resolved Playwright configuration."""

    def __init__(self, config: PlaywrightConfig) -> None:
        self.config = config

    async def launch(self, playwright: Playwright, *, headless: bool) -> Browser:
        """Launch Chromium with the configured runtime options."""
        launch_options: dict[str, Any] = {
            "headless": headless,
            "timeout": self.config.timeout,
            "slow_mo": self.config.slow_mo,
        }
        if self.config.executable_path:
            launch_options["executable_path"] = self.config.executable_path
        return await playwright.chromium.launch(**launch_options)

    async def new_context(self, browser: Browser) -> BrowserContext:
        """Create a browser context with the configured viewport."""
        return await browser.new_context(
            viewport={
                "width": self.config.viewport.width,
                "height": self.config.viewport.height,
            },
        )
