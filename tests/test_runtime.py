"""Run-scoped JSON data and input precedence."""

from typing import Any

import pytest

from pomelo_pw.runtime import NO_OUTPUT, RuntimeContext, snapshot_json
from pomelo_pw.steps.base import StepResult


@pytest.mark.parametrize("value", [None, False, 0, [], {}, {"records": [{"id": 1}]}])
def test_results_preserve_native_json_values(value: Any) -> None:
    runtime = RuntimeContext()
    runtime.publish("record", value)
    assert runtime.snapshot_results() == {"record": value}
    assert StepResult(success=True).output is NO_OUTPUT
    assert StepResult(success=True, output=None).output is None


def test_result_snapshots_do_not_alias_inputs_or_consumers() -> None:
    runtime = RuntimeContext()
    value = {"records": [1]}
    runtime.publish("record", value)
    value["records"].append(2)
    fetched = runtime.snapshot_results()
    assert isinstance(fetched["record"], dict)
    records = fetched["record"]["records"]
    assert isinstance(records, list)
    records.append(3)
    assert runtime.snapshot_results() == {"record": {"records": [1]}}
    runtime.publish("record", False)
    assert runtime.snapshot_results() == {"record": False}
    runtime.invalidate("record")
    assert runtime.snapshot_results() == {}


@pytest.mark.parametrize("value", [float("nan"), float("inf"), (1, 2), {1: "key"}, object()])
def test_rejects_non_json_data(value: Any) -> None:
    with pytest.raises(ValueError):
        snapshot_json(value)


def test_rejects_circular_data_but_allows_shared_children() -> None:
    value: list[Any] = []
    value.append(value)
    with pytest.raises(ValueError, match="circular"):
        snapshot_json(value)
    child = [1]
    assert snapshot_json([child, child]) == [[1], [1]]


def test_input_precedence_and_copies() -> None:
    runtime = RuntimeContext({"key": "flow"}, {"key": "cli"}, {"key": "row"})
    scopes = ({"key": "parent", "parent": 1}, {"key": "child", "child": [1]})
    assert runtime.effective_inputs(scopes) == {"key": "cli", "parent": 1, "child": [1]}
    runtime.overrides.clear()
    assert runtime.effective_inputs(scopes)["key"] == "child"
    assert runtime.effective_inputs(scopes[:1])["key"] == "parent"
    assert runtime.effective_inputs()["key"] == "row"
    runtime.row_inputs.clear()
    assert runtime.effective_inputs()["key"] == "flow"


@pytest.mark.parametrize("name", ["inputs", "results"])
def test_reserved_names_in_every_input_source(name: str) -> None:
    for source in ("flow_inputs", "overrides", "row_inputs"):
        with pytest.raises(ValueError, match="Reserved input names"):
            RuntimeContext(**{source: {name: 1}})
    with pytest.raises(ValueError, match="Reserved input names"):
        RuntimeContext().effective_inputs(({name: 1},))
