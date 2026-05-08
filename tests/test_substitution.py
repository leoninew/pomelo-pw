"""Tests for variable substitution module."""

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
        params = {"url": "${base_url}/login"}
        variables = {"base_url": "https://example.com"}

        result = substitute_vars(params, variables)

        assert result == {"url": "https://example.com/login"}

    def test_multiple_variables(self) -> None:
        """Test multiple variable substitutions in one value."""
        params = {"text": "${greeting}, ${name}!"}
        variables = {"greeting": "Hello", "name": "World"}

        result = substitute_vars(params, variables)

        assert result == {"text": "Hello, World!"}

    def test_nested_variable(self) -> None:
        """Test nested variable reference."""
        params = {"url": "${login_url}"}
        variables = {
            "base_url": "https://example.com",
            "login_url": "${base_url}/login",
        }

        result = substitute_vars(params, variables)

        assert result == {"url": "https://example.com/login"}

    def test_empty_variable_value(self) -> None:
        """Test empty variable value is allowed."""
        params = {"value": "${empty_var}"}
        variables = {"empty_var": ""}

        result = substitute_vars(params, variables)

        assert result == {"value": ""}

    def test_undefined_variable_raises_error(self) -> None:
        """Test undefined variable raises UndefinedVariableError."""
        params = {"url": "${undefined_var}"}
        variables = {"base_url": "https://example.com"}

        with pytest.raises(UndefinedVariableError) as exc_info:
            substitute_vars(params, variables)

        assert exc_info.value.var_name == "undefined_var"

    def test_circular_reference_raises_error(self) -> None:
        """Test circular reference raises CircularReferenceError."""
        params = {"a": "${b}"}
        variables = {
            "a": "${b}",
            "b": "${a}",
        }

        with pytest.raises(CircularReferenceError) as exc_info:
            substitute_vars(params, variables)

        assert exc_info.value.var_name in ("a", "b")

    def test_dict_value_substitution(self) -> None:
        """Test substitution in nested dict values."""
        params = {"options": {"url": "${base_url}/api"}}
        variables = {"base_url": "https://example.com"}

        result = substitute_vars(params, variables)

        assert result == {"options": {"url": "https://example.com/api"}}

    def test_list_value_substitution(self) -> None:
        """Test substitution in list values."""
        params = {"urls": ["${base_url}/a", "${base_url}/b"]}
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
        params = {"script": "const token = '{{api_token}}'; fetch(`/api?token=${token}`)"}
        variables = {"api_token": "abc123"}

        result = substitute_vars(params, variables)

        assert result == {"script": "const token = 'abc123'; fetch(`/api?token=${token}`)"}

    def test_single_brace_backward_compat(self) -> None:
        """Test ${ } syntax still works when {{ }} is not used."""
        params = {"url": "${base_url}/login"}
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
