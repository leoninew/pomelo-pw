"""Tests for step classes."""

from pomelo_pw.steps import get_step, list_steps
from pomelo_pw.steps.click import ClickStep
from pomelo_pw.steps.fill import FillStep
from pomelo_pw.steps.navigate import NavigateStep
from pomelo_pw.steps.screenshot import ScreenshotStep
from pomelo_pw.steps.wait import WaitStep


class TestStepRegistry:
    """Tests for step registry."""

    def test_navigate_step_registered(self) -> None:
        """Test navigate step is registered."""
        step_class = get_step("navigate")
        assert step_class is NavigateStep

    def test_screenshot_step_registered(self) -> None:
        """Test screenshot step is registered."""
        step_class = get_step("screenshot")
        assert step_class is ScreenshotStep

    def test_screenshot_aliases_registered(self) -> None:
        """Test screenshot aliases are registered."""
        assert get_step("capture") is ScreenshotStep
        assert get_step("snap") is ScreenshotStep

    def test_list_steps_returns_primary_names(self) -> None:
        """Test list_steps returns only primary names."""
        steps = list_steps()
        assert "navigate" in steps
        assert "screenshot" in steps
        assert "click" in steps
        assert "fill" in steps
        assert "wait" in steps
        # Aliases should not be in the list
        assert "capture" not in steps
        assert "snap" not in steps

    def test_get_unknown_step_returns_none(self) -> None:
        """Test get_step returns None for unknown step."""
        assert get_step("unknown_step") is None


class TestNavigateStepValidation:
    """Tests for navigate step validation."""

    def test_validate_missing_url(self) -> None:
        """Test validation fails when url is missing."""
        errors = NavigateStep.validate_params({})
        assert "Missing required parameter: url" in errors

    def test_validate_with_url(self) -> None:
        """Test validation passes with url."""
        errors = NavigateStep.validate_params({"type": "navigate", "url": "https://example.com"})
        assert len(errors) == 0

    def test_validate_unknown_param(self) -> None:
        """Test validation fails for unknown parameter."""
        params = {
            "type": "navigate",
            "url": "https://example.com",
            "unknown": "value",
        }
        errors = NavigateStep.validate_params(params)
        assert "Unknown parameter: unknown" in errors

    def test_validate_variables_allowed(self) -> None:
        """Test validation allows variables parameter."""
        errors = NavigateStep.validate_params(
            {
                "type": "navigate",
                "url": "https://example.com",
                "variables": {"key": "value"},
            }
        )
        assert len(errors) == 0


class TestScreenshotStepValidation:
    """Tests for screenshot step validation."""

    def test_validate_missing_file(self) -> None:
        """Test validation fails when file is missing."""
        errors = ScreenshotStep.validate_params({})
        assert "Missing required parameter: file" in errors

    def test_validate_with_file(self) -> None:
        """Test validation passes with file."""
        errors = ScreenshotStep.validate_params({"type": "screenshot", "file": "test.png"})
        assert len(errors) == 0

    def test_validate_optional_params(self) -> None:
        """Test validation passes with optional params."""
        errors = ScreenshotStep.validate_params(
            {
                "type": "screenshot",
                "file": "test.png",
                "full_page": True,
                "selector": "#element",
            }
        )
        assert len(errors) == 0


class TestClickStepValidation:
    """Tests for click step validation."""

    def test_validate_missing_selector(self) -> None:
        """Test validation fails when selector is missing."""
        errors = ClickStep.validate_params({})
        assert "Missing required parameter: selector" in errors

    def test_validate_with_selector(self) -> None:
        """Test validation passes with selector."""
        errors = ClickStep.validate_params({"type": "click", "selector": "#button"})
        assert len(errors) == 0


class TestFillStepValidation:
    """Tests for fill step validation."""

    def test_validate_missing_selector(self) -> None:
        """Test validation fails when selector is missing."""
        errors = FillStep.validate_params({"type": "fill", "value": "test"})
        assert "Missing required parameter: selector" in errors

    def test_validate_missing_value(self) -> None:
        """Test validation fails when value is missing."""
        errors = FillStep.validate_params({"type": "fill", "selector": "#input"})
        assert "Missing required parameter: value" in errors

    def test_validate_with_required_params(self) -> None:
        """Test validation passes with required params."""
        errors = FillStep.validate_params(
            {
                "type": "fill",
                "selector": "#input",
                "value": "test",
            }
        )
        assert len(errors) == 0


class TestWaitStepValidation:
    """Tests for wait step validation."""

    def test_validate_no_required_params(self) -> None:
        """Test validation passes with no params (all optional)."""
        errors = WaitStep.validate_params({"type": "wait"})
        assert len(errors) == 0

    def test_validate_with_selector(self) -> None:
        """Test validation passes with selector."""
        errors = WaitStep.validate_params(
            {
                "type": "wait",
                "selector": "#element",
            }
        )
        assert len(errors) == 0
