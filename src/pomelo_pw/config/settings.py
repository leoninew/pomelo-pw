"""Configuration settings."""

from __future__ import annotations

import os
import platform
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ViewportConfig:
    """Viewport configuration."""

    width: int = 1280
    height: int = 720


@dataclass
class PlaywrightConfig:
    """Playwright browser configuration."""

    headless: bool = True
    viewport: ViewportConfig = field(default_factory=ViewportConfig)
    timeout: int = 30000
    slow_mo: int = 0
    executable_path: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PlaywrightConfig:
        """Create from dictionary."""
        vp_data = data.get("viewport", {})
        viewport = ViewportConfig(
            width=vp_data.get("width", 1280),
            height=vp_data.get("height", 720),
        )
        return cls(
            headless=data.get("headless", True),
            viewport=viewport,
            timeout=data.get("timeout", 30000),
            slow_mo=data.get("slow_mo", 0),
            executable_path=data.get("executable_path"),
        )


@dataclass
class ConfigContainer:
    """Tool configuration container."""

    playwright: PlaywrightConfig = field(default_factory=PlaywrightConfig)


# Default configuration
DEFAULT_CONFIG: dict[str, Any] = {
    "playwright": {
        "headless": True,
        "viewport": {
            "width": 1280,
            "height": 720,
        },
        "timeout": 30000,
        "slow_mo": 0,
        "executable_path": None,
    },
}


def _find_chrome_executable() -> str | None:
    """Find Chrome executable path on the system."""
    # Common Chrome installation paths
    if os.name == "nt":  # Windows
        paths = [
            Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
            Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
            Path.home() / r"AppData\Local\Google\Chrome\Application\chrome.exe",
        ]
    elif os.name == "posix":
        if platform.system() == "Darwin":  # macOS
            paths = [
                Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            ]
        else:  # Linux
            paths = [
                Path("/usr/bin/google-chrome"),
                Path("/usr/bin/google-chrome-stable"),
                Path("/usr/bin/chromium"),
                Path("/usr/bin/chromium-browser"),
            ]
    else:
        return None

    for path in paths:
        if path.exists():
            return str(path)
    return None


def _is_dev_mode() -> bool:
    """Check if running in development mode (from source)."""
    # Check if running from source by looking for pyproject.toml in parent directories
    current = Path(__file__).resolve()
    return any((parent / "pyproject.toml").exists() for parent in current.parents)


def load_app_config() -> ConfigContainer:
    """Load tool configuration.

    Automatically uses system Chrome if running in development mode.

    Returns:
        ConfigContainer with loaded configuration.
    """
    config = DEFAULT_CONFIG.copy()

    if _is_dev_mode():
        chrome_path = _find_chrome_executable()
        if chrome_path:
            config["playwright"]["executable_path"] = chrome_path

    return ConfigContainer(
        playwright=PlaywrightConfig.from_dict(config["playwright"]),
    )
