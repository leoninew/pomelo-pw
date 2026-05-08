"""Variable substitution module."""

from __future__ import annotations

import re
from typing import Any


class UndefinedVariableError(Exception):
    """变量未定义错误."""

    def __init__(self, var_name: str) -> None:
        self.var_name = var_name
        super().__init__(f"Variable '{var_name}' is not defined")


class CircularReferenceError(Exception):
    """循环引用错误."""

    def __init__(self, var_name: str, chain: list[str]) -> None:
        self.var_name = var_name
        self.chain = chain
        super().__init__(f"Circular reference detected: {' -> '.join(chain)} -> {var_name}")


def _substitute_string(value: str, variables: dict[str, Any], visited: set[str]) -> str:
    """替换单个字符串中的变量.

    支持两种语法:
    - {{ var }} - 推荐语法，不会与 JS/Shell 等语言冲突
    - ${ var } - 向后兼容语法（仅在字符串中不包含 {{ }} 时启用）

    策略: 如果字符串包含 {{ }}，则只处理 {{ }}，忽略 ${ }
    """
    # 检查是否使用了双花括号语法
    has_double_brace = "{{" in value and "}}" in value

    # 处理双花括号语法 {{ var }}
    double_brace_pattern = r"\{\{(\w+)\}\}"

    def replace_double_brace(match: re.Match[str]) -> str:
        var_name = match.group(1).strip()
        return _resolve_variable(var_name, variables, visited)

    value = re.sub(double_brace_pattern, replace_double_brace, value)

    # 仅在未使用双花括号时处理单花括号语法（向后兼容）
    if not has_double_brace:
        single_brace_pattern = r"\$\{(\w+)\}"

        def replace_single_brace(match: re.Match[str]) -> str:
            var_name = match.group(1)
            return _resolve_variable(var_name, variables, visited)

        value = re.sub(single_brace_pattern, replace_single_brace, value)

    return value


def _resolve_variable(var_name: str, variables: dict[str, Any], visited: set[str]) -> str:
    """解析变量值，支持嵌套引用."""
    if var_name in visited:
        raise CircularReferenceError(var_name, list(visited))

    if var_name not in variables:
        raise UndefinedVariableError(var_name)

    var_value = variables[var_name]

    # 如果变量值本身包含变量引用，递归替换
    if isinstance(var_value, str) and ("${" in var_value or "{{" in var_value):
        new_visited = visited | {var_name}
        return _substitute_string(var_value, variables, new_visited)

    return str(var_value)


def substitute_vars(params: dict[str, Any], variables: dict[str, Any]) -> dict[str, Any]:
    """替换参数中的所有变量引用.

    支持两种语法:
    - {{ var }} - 推荐语法，不会与 JS/Shell 等语言冲突
    - ${ var } - 向后兼容语法

    Args:
        params: 参数字典，可能包含 {{ var }} 或 ${ var } 形式的变量引用
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
