"""Error context collection module."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from playwright.async_api import Page


@dataclass
class ErrorContext:
    """Error context information."""

    url: str
    screenshot_path: str | None = None
    html_snapshot_path: str | None = None
    console_errors: list[str] = field(default_factory=list)
    network_errors: list[dict[str, Any]] = field(default_factory=list)
    visible_text: str | None = None
    step_index: int = 0
    step_type: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "url": self.url,
            "screenshot": self.screenshot_path,
            "html_snapshot": self.html_snapshot_path,
            "console_errors": self.console_errors,
            "network_errors": self.network_errors,
            "visible_text": self.visible_text,
            "step_index": self.step_index,
            "step_type": self.step_type,
        }


class ErrorContextCollector:
    """Collects error context during flow execution."""

    def __init__(self) -> None:
        self.console_messages: list[str] = []
        self.network_errors: list[dict[str, Any]] = []

    def setup_listeners(self, page: Page) -> None:
        """Setup page event listeners to collect errors."""
        page.on("console", self._on_console)
        page.on("pageerror", self._on_page_error)
        page.on("response", self._on_response)

    def _on_console(self, msg: Any) -> None:
        """Handle console messages."""
        msg_type = msg.type
        if msg_type in ("error", "warning"):
            text = msg.text
            self.console_messages.append(f"[{msg_type.upper()}] {text}")

    def _on_page_error(self, error: Any) -> None:
        """Handle page errors."""
        self.console_messages.append(f"[PAGE ERROR] {error}")

    def _on_response(self, response: Any) -> None:
        """Handle network responses."""
        status = response.status
        if status >= 400:
            self.network_errors.append(
                {
                    "url": response.url,
                    "status": status,
                    "statusText": response.status_text,
                    "method": response.request.method,
                }
            )

    async def collect_error_context(
        self,
        page: Page,
        output_dir: Path,
        step_index: int,
        step_type: str,
    ) -> ErrorContext:
        """Collect error context when a step fails.

        Args:
            page: Playwright page object
            output_dir: Output directory for error artifacts
            step_index: Index of the failed step
            step_type: Type of the failed step

        Returns:
            ErrorContext with collected information
        """
        context = ErrorContext(
            url=page.url,
            step_index=step_index,
            step_type=step_type,
        )

        # Save error screenshot
        try:
            screenshot_path = output_dir / f"error-step-{step_index + 1}.png"
            screenshot_path.parent.mkdir(parents=True, exist_ok=True)
            await page.screenshot(path=str(screenshot_path))
            context.screenshot_path = str(screenshot_path)
        except Exception:
            pass  # Screenshot may fail if page is in bad state

        # Save HTML snapshot
        try:
            html_path = output_dir / f"error-step-{step_index + 1}.html"
            html_content = await page.content()
            html_path.write_text(html_content, encoding="utf-8")
            context.html_snapshot_path = str(html_path)
        except Exception:
            pass

        # Get visible text (first 500 chars)
        try:
            visible_text = await page.evaluate("() => document.body.innerText")
            if visible_text:
                context.visible_text = visible_text[:500]
        except Exception:
            pass

        # Copy collected errors
        context.console_errors = self.console_messages.copy()
        context.network_errors = self.network_errors.copy()

        return context
