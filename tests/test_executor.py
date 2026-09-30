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
                {"type": "navigate", "url": "{{base_url}}"},
                {"type": "screenshot", "file": "test.png"},
            ],
        }
        errors = executor.validate_flow(flow)
        assert len(errors) == 0

    @pytest.mark.parametrize("output_dir", [None, 42, [], "   "])
    def test_validate_flow_rejects_invalid_output_dir(self, executor: FlowExecutor, output_dir: object) -> None:
        """Test validation rejects absent, non-string, and blank output directories."""
        errors = executor.validate_flow({"output_dir": output_dir, "steps": []})
        assert errors == ["Flow field 'output_dir' must be a non-empty string"]

    @pytest.mark.parametrize("headless", [None, 1, "true", []])
    def test_validate_flow_rejects_invalid_headless(self, executor: FlowExecutor, headless: object) -> None:
        """Test validation rejects non-boolean headless values."""
        errors = executor.validate_flow({"headless": headless, "steps": []})
        assert errors == ["Flow field 'headless' must be a boolean"]

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

    @pytest.mark.parametrize("save_as", ["", "a.b", "{{name}}", 1, "非标识符"])
    def test_rejects_invalid_binding_names(self, executor: FlowExecutor, save_as: object) -> None:
        errors = executor.validate_flow({"steps": [{"type": "evaluate", "script": "() => null", "save_as": save_as}]})
        assert "save_as must be an ASCII identifier" in errors[0]

    def test_recursive_validation_reports_nested_paths(self, executor: FlowExecutor) -> None:
        errors = executor.validate_flow(
            {
                "steps": [
                    {
                        "type": "if",
                        "condition": {"eq": [1, 1]},
                        "then": [
                            {
                                "type": "loop",
                                "times": 1,
                                "steps": [{"type": "click", "selector": "#ok", "save_as": "value"}],
                            }
                        ],
                        "else": "invalid",
                    }
                ]
            }
        )
        assert "steps[0].then[0].steps[0]" in errors[0]
        assert "does not produce output" in errors[0]
        assert "steps[0].else: must be a list" in errors[1]

    def test_validation_keeps_future_results_and_business_data(self, executor: FlowExecutor) -> None:
        assert (
            executor.validate_flow(
                {
                    "steps": [
                        {
                            "type": "evaluate",
                            "script": "x => x",
                            "args": {"steps": ["{{results.future}}"]},
                            "save_as": "record",
                        }
                    ]
                }
            )
            == []
        )

    def test_nested_condition_errors_include_step_and_node_paths(self, executor: FlowExecutor) -> None:
        errors = executor.validate_flow(
            {
                "steps": [
                    {
                        "type": "loop",
                        "times": 1,
                        "steps": [
                            {
                                "type": "if",
                                "condition": {"all": [{"eq": [1]}]},
                                "then": [],
                            }
                        ],
                    }
                ]
            }
        )
        assert "steps[0].steps[0] (if): condition.all[0].eq" in errors[0]

    def test_future_condition_references_and_operand_objects_are_valid(self, executor: FlowExecutor) -> None:
        assert (
            executor.validate_flow(
                {
                    "steps": [
                        {
                            "type": "if",
                            "condition": {"eq": ["{{results.future}}", {"all": [], "js": "data"}]},
                            "then": [],
                        }
                    ]
                }
            )
            == []
        )

    @pytest.mark.parametrize(
        "flow",
        [
            {"variables": {"results": 1}},
            {"data": [{"inputs": 1}]},
            {"steps": [{"type": "evaluate", "script": "() => 1", "variables": {"inputs": 1}}]},
        ],
    )
    def test_validation_rejects_reserved_input_names(self, executor: FlowExecutor, flow: dict[str, object]) -> None:
        assert "Reserved input names" in executor.validate_flow(flow)[0]

    @pytest.mark.parametrize("steps", [None, {}, [None], [{"type": []}]])
    def test_malformed_steps_return_validation_errors(self, executor: FlowExecutor, steps: object) -> None:
        assert executor.validate_flow({"steps": steps})


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
                {"type": "navigate", "url": "{{base_url}}/login"},
                {"type": "fill", "selector": "#user", "value": "{{username}}"},
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

    def test_resolve_output_dir_uses_flow_value_and_variables(self, tmp_path: Path) -> None:
        """Test flow output_dir resolves with the merged flow variables."""
        executor = FlowExecutor(work_dir=tmp_path)

        output = executor._resolve_output_dir(
            {"output_dir": ".pomelo-pw/artifacts/{{run_id}}"},
            tmp_path / "course-management.yaml",
            {"run_id": "20260922"},
            None,
        )

        assert output == tmp_path / ".pomelo-pw" / "artifacts" / "20260922"

    def test_resolve_output_dir_prefers_cli_value(self, tmp_path: Path) -> None:
        """Test a CLI output directory overrides the flow declaration."""
        executor = FlowExecutor(work_dir=tmp_path)

        output = executor._resolve_output_dir(
            {"output_dir": "flow-artifacts"},
            tmp_path / "course-management.yaml",
            {},
            Path("cli-artifacts"),
        )

        assert output == tmp_path / "cli-artifacts"

    def test_resolve_output_dir_defaults_to_flow_file_name(self, tmp_path: Path) -> None:
        """Test the default output root remains derived from the flow file name."""
        executor = FlowExecutor(work_dir=tmp_path)

        output = executor._resolve_output_dir({}, tmp_path / "course-management.yaml", {}, None)

        assert output == tmp_path / "course-management"

    @pytest.mark.parametrize("variables", [{"path": []}, {"path": {"id": 1}}, {"path": None}])
    def test_output_dir_requires_a_string(self, executor: FlowExecutor, variables: dict[str, object]) -> None:
        with pytest.raises(ValueError, match="must resolve to a non-empty string"):
            executor._resolve_output_dir({"output_dir": "{{path}}"}, Path("test.yaml"), variables, None)

    def test_output_dir_cannot_read_runtime_results(self, executor: FlowExecutor) -> None:
        with pytest.raises(ValueError, match="cannot reference results"):
            executor._resolve_output_dir(
                {"output_dir": "{{path}}"}, Path("test.yaml"), {"path": "{{results.path}}"}, None
            )

    @pytest.mark.parametrize(
        ("flow", "cli_headless", "expected"),
        [
            ({"headless": True}, None, True),
            ({"headless": False}, True, True),
            ({}, None, False),
        ],
    )
    def test_resolve_headless_prefers_cli_value(
        self, executor: FlowExecutor, flow: dict[str, object], cli_headless: bool | None, expected: bool
    ) -> None:
        """Test CLI browser mode overrides the flow value and defaults to visible."""
        assert executor._resolve_headless(flow, cli_headless) is expected
