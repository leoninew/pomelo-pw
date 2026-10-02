"""Collection contracts and execution regressions."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from pomelo_pw.executor import FlowExecutor
from pomelo_pw.reporting import CollectionLimitError
from pomelo_pw.runtime import RuntimeContext
from pomelo_pw.steps import get_step
from pomelo_pw.steps.base import StepContext
from pomelo_pw.steps.foreach import ForeachStep
from pomelo_pw.substitution import substitute_vars


@pytest.fixture
def context(tmp_path: Path) -> StepContext:
    page = MagicMock()
    page.evaluate = AsyncMock(return_value=None)
    return StepContext(page, RuntimeContext(), tmp_path, [])


def test_foreach_registered_independently() -> None:
    assert get_step("foreach") is ForeachStep


async def test_collect_resolves_each_item_scope_once_and_preserves_opaque_values(context: StepContext) -> None:
    context.runtime.publish("source", [{"id": 1}, {"id": "{{missing}}"}, None])
    result = await FlowExecutor()._execute_step(
        {
            "type": "foreach",
            "items": "{{results.source}}",
            "as": "record",
            "variables": {"tag": "local"},
            "collect": {"record": "{{record}}", "i": "{{index}}", "tag": "{{tag}}"},
            "steps": [],
            "save_as": "collected",
        },
        context,
        "1",
        1,
    )
    assert result.output == {
        "iterations": 3,
        "items": [
            {"record": {"id": 1}, "i": 0, "tag": "local"},
            {"record": {"id": "{{missing}}"}, "i": 1, "tag": "local"},
            {"record": None, "i": 2, "tag": "local"},
        ],
    }
    assert context.runtime.snapshot_results()["collected"] == result.output
    assert context.bindings == {} and "tag" not in context.inputs


@pytest.mark.parametrize("collect", [False, True])
async def test_empty_and_uncollected_output(context: StepContext, collect: bool) -> None:
    step: dict[str, Any] = {"type": "foreach", "items": [] if collect else [1, 2], "steps": [], "save_as": "out"}
    if collect:
        step["collect"] = "{{missing}}"
    result = await FlowExecutor()._execute_step(step, context, "1", 1)
    assert result.output == {"iterations": 0 if collect else 2, "items": []}


@pytest.mark.parametrize("limits", [{"max_collect_items": 1}, {"max_collect_bytes": 4}])
async def test_collection_limits_fail_without_replay_or_partial_publication(
    context: StepContext,
    limits: dict[str, int],
) -> None:
    context.runtime.publish("collected", ["old"])
    context.page.evaluate = AsyncMock(return_value="large")  # type: ignore[method-assign]
    with pytest.raises(CollectionLimitError):
        await FlowExecutor()._execute_step(
            {
                "type": "foreach",
                "items": [1, 2],
                "collect": "{{results.value}}",
                "save_as": "collected",
                "retry": 2,
                "steps": [{"type": "evaluate", "script": "() => 'large'", "save_as": "value"}],
                **limits,
            },
            context,
            "1",
            1,
        )
    assert cast(MagicMock, context.page).evaluate.await_count == 1
    assert "collected" not in context.runtime.snapshot_results()


async def test_nested_collection_snapshots_survive_rebinding(context: StepContext) -> None:
    result = await FlowExecutor()._execute_step(
        {
            "type": "foreach",
            "items": [[1], [2, 3]],
            "collect": "{{results.inner.items}}",
            "steps": [
                {
                    "type": "foreach",
                    "items": "{{item}}",
                    "collect": "{{item}}",
                    "steps": [],
                    "save_as": "inner",
                }
            ],
        },
        context,
        "1",
        1,
    )
    assert result.output == {"iterations": 2, "items": [[1], [2, 3]]}


async def test_collection_byte_limit_counts_utf8_and_array_framing(context: StepContext) -> None:
    step = {"type": "foreach", "items": ["\u4e2d"], "steps": [], "collect": "{{item}}", "max_collect_bytes": 7}
    result = await FlowExecutor()._execute_step(step, context, "1", 1)
    assert result.output == {"iterations": 1, "items": ["\u4e2d"]}
    with pytest.raises(CollectionLimitError, match="observed_bytes=7"):
        await FlowExecutor()._execute_step({**step, "max_collect_bytes": 6}, context, "1", 1)


@pytest.mark.parametrize(
    "items", [None, {}, 1, True, 1.5, "[]", "text {{items}}", "{{items[-1]}}", [float("nan")], [object()]]
)
def test_invalid_collection_declarations(items: object) -> None:
    assert ForeachStep.validate_params({"items": items, "steps": []})


@pytest.mark.parametrize("items", [[], [None, False, 0, "text", {"id": 1}, [2]], "{{results.records}}"])
def test_valid_collection_declarations(items: object) -> None:
    assert not ForeachStep.validate_params({"items": items, "steps": []})


@pytest.mark.parametrize("alias", ["", "inputs", "results", "a.b", "{{name}}", "非标识符", 0, None])
@pytest.mark.parametrize("field", ["as", "index_as"])
def test_invalid_binding_names(field: str, alias: object) -> None:
    assert ForeachStep.validate_params({"items": [], "steps": [], field: alias})


@pytest.mark.parametrize(
    "extra",
    [
        {"as": "index"},
        {"index_as": "item"},
        {"times": 1},
        {"while": {"eq": [1, 1]}},
        {"max_iterations": 2},
        {"max_collect_items": 1},
    ],
)
def test_conflicting_modes_and_bindings(extra: dict[str, Any]) -> None:
    assert ForeachStep.validate_params({"items": [], "steps": [], **extra})


def test_recursive_validation_and_legacy_foreach_rejection() -> None:
    executor = FlowExecutor()
    errors = executor.validate_flow({"steps": [{"type": "foreach", "items": [], "steps": [{"type": "click"}]}]})
    assert "steps[0].steps[0] (click)" in errors[0]
    assert executor.validate_flow({"steps": [{"type": "foreach", "times": 3, "steps": []}]})


@pytest.mark.parametrize("items", [None, {}, "[]", False, 3])
async def test_dynamic_non_array_fails_before_body(context: StepContext, items: object) -> None:
    context.runtime.publish("records", items)
    with pytest.raises(ValueError, match="items must resolve to an array"):
        await FlowExecutor()._execute_step(
            {
                "type": "foreach",
                "items": "{{results.records}}",
                "steps": [{"type": "evaluate", "script": "() => null"}],
            },
            context,
            "1",
            1,
        )
    cast(MagicMock, context.page).evaluate.assert_not_awaited()


async def test_empty_collection_does_not_resolve_children(context: StepContext) -> None:
    await FlowExecutor()._execute_steps(
        [{"type": "foreach", "items": [], "steps": [{"type": "evaluate", "script": "x => x", "args": "{{missing}}"}]}],
        context,
    )
    cast(MagicMock, context.page).evaluate.assert_not_awaited()


async def test_order_index_and_snapshot_rewrite(context: StepContext) -> None:
    records = [None, False, 0, "{{missing}}", {"id": 5}, [6]]
    context.runtime.publish("records", records)
    page = cast(MagicMock, context.page)
    await FlowExecutor()._execute_steps(
        [
            {
                "type": "foreach",
                "items": "{{results.records}}",
                "steps": [
                    {
                        "type": "evaluate",
                        "script": "payload => payload",
                        "args": {"item": "{{item}}", "index": "{{index}}"},
                    },
                    {"type": "evaluate", "script": "() => null", "save_as": "records"},
                ],
            }
        ],
        context,
    )
    assert [call.args[1]["args"] for call in page.evaluate.await_args_list[::2]] == [
        {"item": item, "index": index} for index, item in enumerate(records)
    ]
    assert context.runtime.snapshot_results()["records"] is None
    assert context.bindings == {}
    assert "item" not in context.inputs and "index" not in context.inputs


async def test_nested_shadowing_cli_and_sibling_restoration(context: StepContext) -> None:
    context.runtime = RuntimeContext({"item": "flow", "index": -1}, {"item": "cli", "index": 99})
    page = cast(MagicMock, context.page)
    echo = {
        "type": "evaluate",
        "script": "x => x",
        "args": ["{{item}}", "{{inputs.index}}"],
        "variables": {"item": "child"},
    }
    await FlowExecutor()._execute_steps(
        [
            {
                "type": "foreach",
                "items": ["outer"],
                "steps": [
                    echo,
                    {"type": "foreach", "items": ["inner-0", "inner-1"], "steps": [echo]},
                    echo,
                ],
            },
            echo,
        ],
        context,
    )
    assert [call.args[1]["args"] for call in page.evaluate.await_args_list] == [
        ["outer", 0],
        ["inner-0", 0],
        ["inner-1", 1],
        ["outer", 0],
        ["cli", 99],
    ]


async def test_aliases_work_in_url_selector_args_and_conditions(context: StepContext) -> None:
    page = cast(MagicMock, context.page)
    page.goto = AsyncMock()
    page.click = AsyncMock()
    await FlowExecutor()._execute_steps(
        [
            {
                "type": "foreach",
                "as": "record",
                "index_as": "position",
                "items": [{"id": "a", "enabled": True}, {"id": "b", "enabled": False}],
                "steps": [
                    {
                        "type": "if",
                        "condition": {"all": [{"exists": "{{record.enabled}}"}, {"eq": ["{{record.enabled}}", True]}]},
                        "then": [
                            {"type": "navigate", "url": "https://example.com/{{record.id}}/{{position}}"},
                            {"type": "click", "selector": "#{{record.id}}"},
                            {"type": "evaluate", "args": "{{inputs.record}}", "script": "x => x"},
                        ],
                    },
                ],
            }
        ],
        context,
    )
    assert page.goto.await_args_list[0].args[0] == "https://example.com/a/0"
    assert page.click.await_args_list[0].args[0] == "#a"
    assert page.evaluate.await_args_list[0].args[1]["args"] == {"id": "a", "enabled": True}


async def test_opaque_bindings_in_conditions_and_whole_inputs(context: StepContext) -> None:
    page = cast(MagicMock, context.page)
    context.runtime.publish("records", [{"text": "\\{{literal}}", "nested": ["{{missing}}"]}])
    await FlowExecutor()._execute_steps(
        [
            {
                "type": "foreach",
                "items": "{{results.records}}",
                "steps": [
                    {
                        "type": "if",
                        "condition": {"eq": ["{{item.nested[0]}}", "\\{{missing}}"]},
                        "then": [
                            {"type": "evaluate", "script": "x => x", "args": "{{inputs}}"},
                        ],
                    },
                ],
            }
        ],
        context,
    )
    assert page.evaluate.await_args_list[0].args[1]["args"] == {
        "item": {"text": "\\{{literal}}", "nested": ["{{missing}}"]},
        "index": 0,
    }


def test_binding_reference_copies_and_aliases() -> None:
    bindings = {"item": {"text": "{{missing}}", "values": [1]}}
    resolved = substitute_vars({"payload": "{{alias}}"}, {"alias": "{{inputs.item}}"}, bindings=bindings)
    resolved["payload"]["values"].append(2)
    assert bindings["item"]["values"] == [1]
    assert resolved["payload"]["text"] == "{{missing}}"


@pytest.mark.parametrize(
    "parent",
    [
        {"type": "foreach", "items": [0, 1, 2]},
        {"type": "loop", "times": 3},
        {"type": "loop", "while": {"eq": [1, 1]}, "max_iterations": 3},
        {"type": "if", "condition": {"eq": [1, 1]}},
    ],
)
async def test_parent_retries_never_replay_successful_bodies(context: StepContext, parent: dict[str, Any]) -> None:
    page = cast(MagicMock, context.page)
    page.evaluate = AsyncMock(side_effect=[None, None, None, RuntimeError("write failed")])
    body = [{"type": "evaluate", "script": "() => null"}, {"type": "evaluate", "script": "() => null"}]
    if parent["type"] == "if":
        body *= 2
    parent = {**parent, "retry": 2, "retry_delay": 0, "then" if parent["type"] == "if" else "steps": body}
    with pytest.raises(RuntimeError, match="write failed") as error:
        await FlowExecutor()._execute_steps([parent], context)
    assert page.evaluate.await_count == 4
    assert "Step 1." in str(error.value)
    if parent["type"] == "foreach":
        assert "index-1.2 (evaluate)" in str(error.value)
    assert context.bindings == {}


async def test_child_retry_does_not_restart_prior_iteration(context: StepContext) -> None:
    page = cast(MagicMock, context.page)
    page.evaluate = AsyncMock(side_effect=[0, RuntimeError("transient"), 1, 2])
    await FlowExecutor()._execute_steps(
        [
            {
                "type": "foreach",
                "items": [0, 1, 2],
                "retry": 2,
                "retry_delay": 0,
                "steps": [
                    {
                        "type": "evaluate",
                        "script": "x => x",
                        "args": "{{item}}",
                        "save_as": "last",
                        "retry": 1,
                        "retry_delay": 0,
                    },
                ],
            }
        ],
        context,
    )
    assert [call.args[1]["args"] for call in page.evaluate.await_args_list] == [0, 1, 1, 2]
    assert context.runtime.snapshot_results() == {"last": 2}


async def test_parent_condition_probe_can_retry_before_body(context: StepContext) -> None:
    page = cast(MagicMock, context.page)
    page.evaluate = AsyncMock(side_effect=[RuntimeError("transient probe"), True, None])
    await FlowExecutor()._execute_steps(
        [
            {
                "type": "if",
                "retry": 1,
                "retry_delay": 0,
                "condition": {"js": {"script": "() => true"}},
                "then": [{"type": "evaluate", "script": "() => null"}],
            }
        ],
        context,
    )
    assert page.evaluate.await_count == 3


async def test_failed_nested_collection_identifies_both_indices(context: StepContext) -> None:
    page = cast(MagicMock, context.page)
    page.evaluate = AsyncMock(side_effect=[None, RuntimeError("nested failure")])
    with pytest.raises(RuntimeError, match=r"index-0.*index-1.1.*nested failure"):
        await FlowExecutor()._execute_steps(
            [
                {
                    "type": "foreach",
                    "items": ["outer"],
                    "steps": [
                        {
                            "type": "foreach",
                            "items": ["first", "second"],
                            "steps": [{"type": "evaluate", "script": "() => null"}],
                        },
                    ],
                }
            ],
            context,
        )
    assert page.evaluate.await_count == 2
