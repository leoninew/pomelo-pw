"""Tests for variable substitution module."""

from typing import Any

import pytest

from pomelo_pw.substitution import (
    CircularReferenceError,
    UndefinedVariableError,
    substitute_vars,
)


class TestSubstituteVars:
    """Tests for substitute_vars function."""

    def test_simple_substitution(self) -> None:
        """Test simple variable substitution."""
        params = {"url": "{{base_url}}/login"}
        variables = {"base_url": "https://example.com"}

        result = substitute_vars(params, variables)

        assert result == {"url": "https://example.com/login"}

    def test_multiple_variables(self) -> None:
        """Test multiple variable substitutions in one value."""
        params = {"text": "{{greeting}}, {{name}}!"}
        variables = {"greeting": "Hello", "name": "World"}

        result = substitute_vars(params, variables)

        assert result == {"text": "Hello, World!"}

    def test_nested_variable(self) -> None:
        """Test nested variable reference."""
        params = {"url": "{{login_url}}"}
        variables = {
            "base_url": "https://example.com",
            "login_url": "{{base_url}}/login",
        }

        result = substitute_vars(params, variables)

        assert result == {"url": "https://example.com/login"}

    def test_empty_variable_value(self) -> None:
        """Test empty variable value is allowed."""
        params = {"value": "{{empty_var}}"}
        variables = {"empty_var": ""}

        result = substitute_vars(params, variables)

        assert result == {"value": ""}

    def test_undefined_variable_raises_error(self) -> None:
        """Test undefined variable raises UndefinedVariableError."""
        params = {"url": "{{undefined_var}}"}
        variables = {"base_url": "https://example.com"}

        with pytest.raises(UndefinedVariableError) as exc_info:
            substitute_vars(params, variables)

        assert exc_info.value.var_name == "undefined_var"

    def test_circular_reference_raises_error(self) -> None:
        """Test circular reference raises CircularReferenceError."""
        params = {"a": "{{b}}"}
        variables = {
            "a": "{{b}}",
            "b": "{{a}}",
        }

        with pytest.raises(CircularReferenceError) as exc_info:
            substitute_vars(params, variables)

        assert exc_info.value.var_name in ("inputs.a", "inputs.b")

    def test_dict_value_substitution(self) -> None:
        """Test substitution in nested dict values."""
        params = {"options": {"url": "{{base_url}}/api"}}
        variables = {"base_url": "https://example.com"}

        result = substitute_vars(params, variables)

        assert result == {"options": {"url": "https://example.com/api"}}

    def test_list_value_substitution(self) -> None:
        """Test substitution in list values."""
        params = {"urls": ["{{base_url}}/a", "{{base_url}}/b"]}
        variables = {"base_url": "https://example.com"}

        result = substitute_vars(params, variables)

        assert result == {"urls": ["https://example.com/a", "https://example.com/b"]}

    def test_non_string_values_unchanged(self) -> None:
        """Test non-string values remain unchanged."""
        params = {"count": 42, "enabled": True, "ratio": 3.14}
        variables = {"base_url": "https://example.com"}

        result = substitute_vars(params, variables)

        assert result == {"count": 42, "enabled": True, "ratio": 3.14}

    def test_no_variables_in_value(self) -> None:
        """Test values without variables remain unchanged."""
        params = {"url": "https://example.com/static"}
        variables = {"base_url": "https://other.com"}

        result = substitute_vars(params, variables)

        assert result == {"url": "https://example.com/static"}

    def test_double_brace_syntax(self) -> None:
        """Test double brace {{ }} syntax."""
        params = {"url": "{{base_url}}/login"}
        variables = {"base_url": "https://example.com"}

        result = substitute_vars(params, variables)

        assert result == {"url": "https://example.com/login"}

    def test_double_brace_with_js_template(self) -> None:
        """Test double brace doesn't conflict with JS template strings."""
        params = {"text": "const token = '{{api_token}}'; fetch(`/api?token=${token}`)"}
        variables = {"api_token": "abc123"}

        result = substitute_vars(params, variables)

        assert result == {"text": "const token = 'abc123'; fetch(`/api?token=${token}`)"}

    def test_dollar_brace_syntax_remains_unchanged(self) -> None:
        """Test ${ } syntax is left for host languages like JavaScript."""
        params = {"url": "${base_url}/login"}
        variables = {"base_url": "https://example.com"}

        result = substitute_vars(params, variables)

        assert result == {"url": "${base_url}/login"}

    def test_double_brace_syntax_allows_inner_whitespace(self) -> None:
        """Test double brace syntax supports spaces around variable names."""
        params = {"url": "{{ base_url }}/login"}
        variables = {"base_url": "https://example.com"}

        result = substitute_vars(params, variables)

        assert result == {"url": "https://example.com/login"}

    def test_double_brace_nested_variable(self) -> None:
        """Test nested variable reference with double brace syntax."""
        params = {"url": "{{login_url}}"}
        variables = {
            "base_url": "https://example.com",
            "login_url": "{{base_url}}/login",
        }

        result = substitute_vars(params, variables)

        assert result == {"url": "https://example.com/login"}

    def test_double_brace_undefined_variable(self) -> None:
        """Test undefined variable with double brace syntax raises error."""
        params = {"url": "{{undefined_var}}"}
        variables = {"base_url": "https://example.com"}

        with pytest.raises(UndefinedVariableError) as exc_info:
            substitute_vars(params, variables)

        assert exc_info.value.var_name == "undefined_var"


@pytest.mark.parametrize("value", [None, False, 0, [], {}, {"id": [1]}])
@pytest.mark.parametrize("path", ["value", "inputs.value", "results.value"])
def test_complete_references_preserve_types(value: Any, path: str) -> None:
    assert substitute_vars({"arg": "{{" + path + "}}"}, {"value": value}, {"value": value}) == {"arg": value}


def test_nested_containers_paths_and_scalar_text() -> None:
    result = substitute_vars(
        {"args": [{"item": "{{results.records[0]}}"}], "text": "{{flag}}/{{zero}}/{{empty}}"},
        {"flag": False, "zero": 0, "empty": None},
        {"records": [{"id": 7}]},
    )
    assert result == {"args": [{"item": {"id": 7}}], "text": "false/0/null"}


def test_sibling_field_references_and_alias_paths() -> None:
    variables = {"item": {"id": 7, "copy": "{{item.id}}"}, "alias": "{{item}}"}
    assert substitute_vars({"whole": "{{item}}", "field": "{{alias.copy}}"}, variables) == {
        "whole": {"id": 7, "copy": 7},
        "field": 7,
    }


def test_alias_field_lookup_does_not_resolve_unrelated_definitions() -> None:
    variables = {"item": {"id": 7, "other": "{{missing}}"}, "alias": "{{item}}"}
    assert substitute_vars({"id": "{{alias.id}}"}, variables) == {"id": 7}
    variables["item"] = {"id": 7, "copy": "{{alias.id}}"}
    assert substitute_vars({"item": "{{item}}"}, variables) == {"item": {"id": 7, "copy": 7}}


def test_results_stay_opaque_through_input_aliases_and_fields() -> None:
    variables = {"alias": "{{results.record}}", "nested": {"alias": "{{alias}}"}}
    record = {"text": "{{missing}} ${host}", "list": [r"\{{literal}}"]}
    result = substitute_vars(
        {
            "direct": "{{results.record}}",
            "alias": "{{alias}}",
            "field": "{{alias.text}}",
            "nested": "{{nested.alias.list[0]}}",
        },
        variables,
        {"record": record},
    )
    assert result == {"direct": record, "alias": record, "field": record["text"], "nested": r"\{{literal}}"}


def test_escaping_is_applied_once_and_host_templates_are_untouched() -> None:
    assert substitute_vars({"text": r"\{{missing}} {{literal}} ${host}"}, {"literal": r"\{{another}}"}) == {
        "text": "{{missing}} {{another}} ${host}"
    }
    assert substitute_vars({"text": "prefix/{{results.text}}"}, {}, {"text": r"\{{missing}}"}) == {
        "text": r"prefix/\{{missing}}"
    }


@pytest.mark.parametrize("path", ["results.record[-1]", "results.record[*]", "item..id", "item.id()"])
def test_rejects_invalid_path_syntax(path: str) -> None:
    with pytest.raises(ValueError, match="Invalid reference path"):
        substitute_vars({"arg": "{{" + path + "}}"}, {})


@pytest.mark.parametrize("path", ["item.none", "item.items[2]", "item.items[0].id", "item.null.id"])
def test_missing_field_wrong_container_and_out_of_range(path: str) -> None:
    with pytest.raises(UndefinedVariableError):
        substitute_vars({"arg": "{{" + path + "}}"}, {"item": {"items": [0], "null": None}})


@pytest.mark.parametrize("value", [[], {"id": 1}])
def test_objects_cannot_be_embedded_in_text(value: Any) -> None:
    with pytest.raises(ValueError, match="cannot be interpolated"):
        substitute_vars({"text": "value={{value}}"}, {"value": value})


@pytest.mark.parametrize(
    "variables",
    [
        {"item": {"a": "{{item.b}}", "b": "{{inputs.item.a}}"}},
        {"item": {"self": "{{item}}"}},
        {"item": "{{inputs}}"},
        {"item": ["{{item[0]}}"]},
    ],
)
def test_nested_cycles_are_detected(variables: dict[str, Any]) -> None:
    with pytest.raises(CircularReferenceError):
        substitute_vars({"arg": "{{item}}"}, variables)
