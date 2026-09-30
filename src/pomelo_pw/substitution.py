"""Typed references and scalar text interpolation."""

from __future__ import annotations

import json
import re
from copy import deepcopy
from typing import Any

from pomelo_pw.runtime import validate_inputs

REFERENCE = re.compile(r"\\\{\{|(?<!\\)\{\{([^{}]*)\}\}")
ROOT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
SEGMENT = re.compile(r"\.([A-Za-z_][A-Za-z0-9_]*)|\[([0-9]+)\]")


class UndefinedVariableError(ValueError):
    def __init__(self, var_name: str) -> None:
        self.var_name = var_name
        super().__init__(f"Variable or field '{var_name}' is not defined")


class CircularReferenceError(ValueError):
    def __init__(self, var_name: str, chain: tuple[str, ...]) -> None:
        self.var_name = var_name
        super().__init__(f"Circular reference detected: {' -> '.join((*chain, var_name))}")


def _parse_path(path: str) -> list[str | int]:
    match = ROOT.match(path)
    if match is None:
        raise ValueError(f"Invalid reference path: {path!r}")
    parts: list[str | int] = [match.group()]
    position = match.end()
    while position < len(path):
        match = SEGMENT.match(path, position)
        if match is None:
            raise ValueError(f"Invalid reference path: {path!r}")
        parts.append(match.group(1) if match.group(1) is not None else int(match.group(2)))
        position = match.end()
    return parts


def validate_reference(value: Any) -> None:
    """Validate a complete reference without resolving its data."""
    match = REFERENCE.fullmatch(value) if isinstance(value, str) else None
    if match is None or match.group(1) is None:
        raise ValueError("Expected a complete {{...}} reference")
    _parse_path(match.group(1).strip())


class _Resolver:
    def __init__(self, inputs: dict[str, Any], results: dict[str, Any] | None) -> None:
        self.inputs = inputs
        self.results = results

    @staticmethod
    def _input_key(location: tuple[str | int, ...]) -> str:
        return "inputs" + "".join(f"[{part}]" if isinstance(part, int) else f".{part}" for part in location)

    def reference(self, path: str, chain: tuple[str, ...], suffix: tuple[str | int, ...] = ()) -> Any:
        parts = _parse_path(path)
        parts.extend(suffix)
        root = parts.pop(0)
        if root == "results":
            if self.results is None:
                raise UndefinedVariableError(path)
            return deepcopy(self._read(self.results, parts, path))
        if root not in ("inputs", "results"):
            parts.insert(0, root)
        value: Any = self.inputs
        location: tuple[str | int, ...] = ()
        for index, part in enumerate(parts):
            # A template alias is resolved once; its returned data stays opaque.
            if isinstance(value, str):
                match = REFERENCE.fullmatch(value)
                if match is not None and match.group(1) is not None:
                    key = self._input_key(location)
                    if key in chain:
                        raise CircularReferenceError(key, chain)
                    return self.reference(match.group(1).strip(), (*chain, key), tuple(parts[index:]))
                resolved = self.value(value, chain, location)
                return deepcopy(self._read(resolved, parts[index:], path))
            value = self._read(value, [part], path)
            location = (*location, part)
        return deepcopy(self.value(value, chain, location))

    @staticmethod
    def _read(value: Any, parts: list[str | int], path: str) -> Any:
        for part in parts:
            if isinstance(part, int):
                if not isinstance(value, list) or part >= len(value):
                    raise UndefinedVariableError(path)
            elif not isinstance(value, dict) or part not in value:
                raise UndefinedVariableError(path)
            value = value[part]
        return value

    def value(
        self,
        value: Any,
        chain: tuple[str, ...] = (),
        location: tuple[str | int, ...] | None = None,
    ) -> Any:
        if location is not None:
            key = self._input_key(location)
            if key in chain:
                raise CircularReferenceError(key, chain)
            chain = (*chain, key)
        if isinstance(value, dict):
            return {
                key: self.value(item, chain, (*location, key) if location is not None else None)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [
                self.value(item, chain, (*location, index) if location is not None else None)
                for index, item in enumerate(value)
            ]
        if not isinstance(value, str):
            return value
        match = REFERENCE.fullmatch(value)
        if match is not None and match.group(1) is not None:
            return self.reference(match.group(1).strip(), chain)

        def replace(match: re.Match[str]) -> str:
            if match.group(1) is None:
                return "{{"
            item = self.reference(match.group(1).strip(), chain)
            if isinstance(item, (dict, list)):
                raise ValueError("Objects and arrays cannot be interpolated into text")
            if isinstance(item, str):
                return item
            return json.dumps(item, allow_nan=False, ensure_ascii=False)

        return REFERENCE.sub(replace, value)


def substitute_vars(
    params: dict[str, Any], variables: dict[str, Any], results: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Resolve parameter containers without interpreting referenced result data."""
    validate_inputs(variables)
    resolver = _Resolver(variables, results)
    return {key: resolver.value(value) for key, value in params.items()}
