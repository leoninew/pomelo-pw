"""Run-scoped inputs and immutable JSON result snapshots."""

from __future__ import annotations

import math
import re
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, cast

type JsonValue = None | bool | int | float | str | list[JsonValue] | dict[str, JsonValue]

IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
RESERVED_INPUT_NAMES = frozenset({"inputs", "results"})


class NoOutput(Enum):
    MISSING = "no-output"


NO_OUTPUT = NoOutput.MISSING


def validate_json(value: Any, path: str = "value", ancestors: frozenset[int] = frozenset()) -> None:
    """Reject values that cannot be safely transferred as JSON."""
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path}: number must be finite")
        return
    if isinstance(value, (list, dict)):
        if id(value) in ancestors:
            raise ValueError(f"{path}: circular data is not supported")
        ancestors = ancestors | {id(value)}
        if isinstance(value, list):
            for index, item in enumerate(value):
                validate_json(item, f"{path}[{index}]", ancestors)
        else:
            for key, item in value.items():
                if not isinstance(key, str):
                    raise ValueError(f"{path}: object keys must be strings")
                validate_json(item, f"{path}.{key}", ancestors)
        return
    raise ValueError(f"{path}: unsupported JSON value {type(value).__name__}")


def snapshot_json(value: Any) -> JsonValue:
    validate_json(value)
    return cast(JsonValue, deepcopy(value))


def validate_inputs(value: Any) -> None:
    if not isinstance(value, dict):
        raise ValueError("variables must be an object")
    validate_json(value, "variables")
    reserved = RESERVED_INPUT_NAMES.intersection(value)
    if reserved:
        raise ValueError(f"Reserved input names: {', '.join(sorted(reserved))}")


@dataclass
class RuntimeContext:
    flow_inputs: dict[str, Any] = field(default_factory=dict)
    overrides: dict[str, Any] = field(default_factory=dict)
    row_inputs: dict[str, Any] = field(default_factory=dict)
    _results: dict[str, JsonValue] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        for inputs in (self.flow_inputs, self.overrides, self.row_inputs):
            validate_inputs(inputs)
        self.flow_inputs = deepcopy(self.flow_inputs)
        self.overrides = deepcopy(self.overrides)
        self.row_inputs = deepcopy(self.row_inputs)

    def effective_inputs(self, scopes: tuple[dict[str, Any], ...] = ()) -> dict[str, Any]:
        inputs = {**self.flow_inputs, **self.row_inputs}
        for scope in scopes:
            validate_inputs(scope)
            inputs.update(scope)
        inputs.update(self.overrides)
        return deepcopy(inputs)

    def snapshot_results(self) -> dict[str, JsonValue]:
        return deepcopy(self._results)

    def invalidate(self, name: str) -> None:
        self._results.pop(name, None)

    def publish(self, name: str, value: Any) -> None:
        if not IDENTIFIER.fullmatch(name):
            raise ValueError("Result name must be an ASCII identifier")
        self._results[name] = snapshot_json(value)
