"""Tests for configuration module."""

from pomelo_pw.config import (
    ConfigContainer,
    PlaywrightConfig,
    ViewportConfig,
    load_app_config,
)


class TestViewportConfig:
    """Tests for ViewportConfig."""

    def test_default_values(self) -> None:
        """Test default viewport values."""
        config = ViewportConfig()
        assert config.width == 1280
        assert config.height == 720

    def test_custom_values(self) -> None:
        """Test custom viewport values."""
        config = ViewportConfig(width=1920, height=1080)
        assert config.width == 1920
        assert config.height == 1080


class TestPlaywrightConfig:
    """Tests for PlaywrightConfig."""

    def test_default_values(self) -> None:
        """Test default playwright config values."""
        config = PlaywrightConfig()
        assert config.headless is True
        assert config.viewport.width == 1280
        assert config.viewport.height == 720
        assert config.timeout == 30000
        assert config.slow_mo == 0

    def test_from_dict(self) -> None:
        """Test creating from dictionary."""
        data = {
            "headless": False,
            "viewport": {"width": 1920, "height": 1080},
            "timeout": 60000,
            "slow_mo": 100,
        }
        config = PlaywrightConfig.from_dict(data)
        assert config.headless is False
        assert config.viewport.width == 1920
        assert config.viewport.height == 1080
        assert config.timeout == 60000
        assert config.slow_mo == 100

    def test_from_dict_partial(self) -> None:
        """Test creating from partial dictionary."""
        data = {"headless": False}
        config = PlaywrightConfig.from_dict(data)
        assert config.headless is False
        assert config.viewport.width == 1280  # default
        assert config.viewport.height == 720  # default


class TestLoadAppConfig:
    """Tests for load_app_config function."""

    def test_returns_config_container(self) -> None:
        """Test that it returns ConfigContainer."""
        config = load_app_config()
        assert isinstance(config, ConfigContainer)

    def test_has_playwright_config(self) -> None:
        """Test that it has playwright config."""
        config = load_app_config()
        assert isinstance(config.playwright, PlaywrightConfig)
