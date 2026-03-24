"""Variable substitution module."""

from __future__ import annotations

import re
from typing import Any


class UndefinedVariableError(Exception):
    """变量未定义错误."""

    def __init__(self, var_name: str) -> None:
        self.var_name = var_name
        super().__init__(f"Variable '${var_name}' is not defined")


class CircularReferenceError(Exception):
    """循环引用错误."""

    def __init__(self, var_name: str, chain: list[str]) -> None:
        self.var_name = var_name
        self.chain = chain
        super().__init__(f"Circular reference detected: {' -> '.join(chain)} -> {var_name}")


def _substitute_string(value: str, variables: dict[str, Any], visited: set[str]) -> str:
    """替换单个字符串中的变量."""
    pattern = r"\$\{(\w+)\}"

    def replace(match: re.Match[str]) -> str:
        var_name = match.group(1)

        if var_name in visited:
            raise CircularReferenceError(var_name, list(visited))

        if var_name not in variables:
            raise UndefinedVariableError(var_name)

        var_value = variables[var_name]

        if isinstance(var_value, str) and "${" in var_value:
            new_visited = visited | {var_name}
            return _substitute_string(var_value, variables, new_visited)

        return str(var_value)

    return re.sub(pattern, replace, value)


def substitute_vars(params: dict[str, Any], variables: dict[str, Any]) -> dict[str, Any]:
    """替换参数中的所有变量引用.

    Args:
        params: 参数字典，可能包含 ${var} 形式的变量引用
        variables: 变量字典

    Returns:
        替换后的参数字典

    Raises:
        UndefinedVariableError: 变量未定义
        CircularReferenceError: 变量循环引用
    """
    result: dict[str, Any] = {}

    for key, value in params.items():
        if isinstance(value, str):
            result[key] = _substitute_string(value, variables, set())
        elif isinstance(value, dict):
            result[key] = substitute_vars(value, variables)
        elif isinstance(value, list):
            result[key] = [
                _substitute_string(item, variables, set()) if isinstance(item, str) else item for item in value
            ]
        else:
            result[key] = value

    return result
