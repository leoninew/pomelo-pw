"""Tests for flow executor."""

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
import yaml

from pomelo_pw.executor import FlowExecutor


class TestFlowExecutorValidation:
    """Tests for flow validation."""

    @pytest.fixture
    def executor(self) -> FlowExecutor:
        """Create executor instance."""
        return FlowExecutor()

    @pytest.fixture
    def temp_dir(self) -> Generator[Path, None, None]:
        """Create temporary directory."""
        with tempfile.TemporaryDirectory() as d:
            yield Path(d)

    def test_validate_empty_flow(self, executor: FlowExecutor) -> None:
        """Test validation of empty flow."""
        errors = executor.validate_flow({})
        assert len(errors) == 0

    def test_validate_flow_missing_type(self, executor: FlowExecutor) -> None:
        """Test validation fails when step has no type."""
        flow = {"steps": [{"url": "https://example.com"}]}
        errors = executor.validate_flow(flow)
        assert len(errors) == 1
        assert "Missing 'type' field" in errors[0]

    def test_validate_flow_unknown_step(self, executor: FlowExecutor) -> None:
        """Test validation fails for unknown step type."""
        flow = {"steps": [{"type": "unknown_step"}]}
        errors = executor.validate_flow(flow)
        assert len(errors) == 1
        assert "Unknown step type" in errors[0]

    def test_validate_flow_missing_required_param(self, executor: FlowExecutor) -> None:
        """Test validation fails when required param is missing."""
        flow = {"steps": [{"type": "screenshot"}]}
        errors = executor.validate_flow(flow)
        assert len(errors) == 1
        assert "Missing required parameter: file" in errors[0]

    def test_validate_flow_valid(self, executor: FlowExecutor) -> None:
        """Test validation passes for valid flow."""
        flow = {
            "name": "test-flow",
            "variables": {"base_url": "https://example.com"},
            "steps": [
                {"type": "navigate", "url": "${base_url}"},
                {"type": "screenshot", "file": "test.png"},
            ],
        }
        errors = executor.validate_flow(flow)
        assert len(errors) == 0

    def test_validate_flow_with_variables_field(self, executor: FlowExecutor) -> None:
        """Test validation allows variables field in steps."""
        flow = {
            "steps": [
                {
                    "type": "navigate",
                    "url": "https://example.com",
                    "variables": {"custom_var": "value"},
                },
            ],
        }
        errors = executor.validate_flow(flow)
        assert len(errors) == 0

    def test_load_flow(self, executor: FlowExecutor, temp_dir: Path) -> None:
        """Test loading flow from file."""
        flow_path = temp_dir / "test.yaml"
        flow_data = {"name": "test", "steps": [{"type": "navigate", "url": "https://example.com"}]}
        flow_path.write_text(yaml.dump(flow_data), encoding="utf-8")

        loaded = executor.load_flow(flow_path)
        assert loaded["name"] == "test"
        assert len(loaded["steps"]) == 1

    def test_validate_flow_file(self, executor: FlowExecutor, temp_dir: Path) -> None:
        """Test validating flow file."""
        flow_path = temp_dir / "test.yaml"
        flow_data = {"steps": [{"type": "invalid_step"}]}
        flow_path.write_text(yaml.dump(flow_data), encoding="utf-8")

        errors = executor.validate_flow_file(flow_path)
        assert len(errors) == 1


class TestFlowExecutorVariables:
    """Tests for variable handling."""

    @pytest.fixture
    def executor(self) -> FlowExecutor:
        """Create executor instance."""
        return FlowExecutor()

    def test_validate_flow_with_flow_variables(self, executor: FlowExecutor) -> None:
        """Test validation handles flow variables."""
        flow = {
            "variables": {
                "base_url": "https://example.com",
                "username": "admin",
            },
            "steps": [
                {"type": "navigate", "url": "${base_url}/login"},
                {"type": "fill", "selector": "#user", "value": "${username}"},
            ],
        }
        errors = executor.validate_flow(flow)
        assert len(errors) == 0

    def test_validate_flow_with_empty_variable(self, executor: FlowExecutor) -> None:
        """Test validation allows empty variable values."""
        flow = {
            "variables": {"empty_var": ""},
            "steps": [{"type": "navigate", "url": "https://example.com"}],
        }
        errors = executor.validate_flow(flow)
        assert len(errors) == 0
