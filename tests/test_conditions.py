"""Focused contract tests for shared structured conditions."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from pomelo_pw.browser_functions import CALL_FUNCTION
from pomelo_pw.conditions import ConditionEvaluationError, evaluate_condition, validate_condition
from pomelo_pw.runtime import RuntimeContext
from pomelo_pw.steps.base import StepContext
from pomelo_pw.steps.loop import LoopStep


def _context() -> StepContext:
    page = MagicMock()
    page.url = "https://example.com/user/42"
    page.locator.return_value.count = AsyncMock(return_value=0)
    page.locator.return_value.first.is_visible = AsyncMock(return_value=False)
    page.get_by_text.return_value.count = AsyncMock(return_value=0)
    page.evaluate = AsyncMock(return_value=True)
    return StepContext(page, RuntimeContext(), Path("/tmp/out"), [])


@pytest.mark.parametrize(
    ("left", "right", "equal"),
    [
        (None, None, True),
        (None, False, False),
        (False, 0, False),
        (True, 1, False),
        (1, 1.0, True),
        (0, "0", False),
        (False, False, True),
        ("a", "a", True),
        ([], [], True),
        ({}, {}, True),
        ([1, 2], [2, 1], False),
        ({"a": 1, "b": [False]}, {"b": [False], "a": 1.0}, True),
        ({"a": [False]}, {"a": [0]}, False),
        ([], {}, False),
    ],
)
async def test_json_equality_and_inequality(left: Any, right: Any, equal: bool) -> None:
    context = _context()
    assert await evaluate_condition(context, {"eq": [left, right]}) is equal
    assert await evaluate_condition(context, {"ne": [left, right]}) is not equal


@pytest.mark.parametrize(
    ("value", "collection", "member"),
    [
        (False, [0], False),
        (1, [1.0], True),
        ({"x": [False]}, [{"x": [0]}], False),
        (None, [None], True),
        (0, [], False),
    ],
)
async def test_array_membership(value: Any, collection: Any, member: bool) -> None:
    context = _context()
    context.runtime.publish("collection", collection)
    assert await evaluate_condition(context, {"in": [value, "{{results.collection}}"]}) is member


@pytest.mark.parametrize("value", [None, False, 0, "", [], {}])
async def test_exists_checks_presence_instead_of_truthiness(value: Any) -> None:
    context = _context()
    context.runtime.publish("value", value)
    assert await evaluate_condition(context, {"exists": "{{results.value}}"})


@pytest.mark.parametrize(
    "reference",
    [
        "{{absent}}",
        "{{results.absent}}",
        "{{results.record.absent}}",
        "{{results.record.items[2]}}",
        "{{results.record.empty.field}}",
        "{{results.record.number.field}}",
    ],
)
async def test_exists_returns_false_for_unreadable_paths(reference: str) -> None:
    context = _context()
    context.runtime.publish("record", {"items": [], "empty": None, "number": 0})
    assert not await evaluate_condition(context, {"exists": reference})


async def test_exists_does_not_swallow_circular_or_invalid_references() -> None:
    context = _context()
    context.runtime = RuntimeContext({"a": "{{b}}", "b": "{{a}}"})
    with pytest.raises(ConditionEvaluationError, match="condition.exists: Circular reference"):
        await evaluate_condition(context, {"exists": "{{a}}"})
    with pytest.raises(ConditionEvaluationError, match="Invalid reference path"):
        await evaluate_condition(context, {"exists": "{{results.record[-1]}}"})


@pytest.mark.parametrize(
    "condition",
    [
        {"all": [{"exists": "{{results.absent}}"}, {"eq": ["{{results.absent.field}}", True]}]},
        {"all": [{"eq": [1, 2]}, {"js": {"script": "() => {throw new Error('unvisited');}"}}]},
        {"not": {"any": [{"eq": [1, 1]}, {"eq": ["{{results.absent}}", 1]}]}},
    ],
)
async def test_short_circuit_skips_resolution_and_js(condition: Any) -> None:
    context = _context()
    assert not await evaluate_condition(context, condition)
    cast(MagicMock, context.page).evaluate.assert_not_awaited()


async def test_guarded_field_is_evaluated_when_present() -> None:
    context = _context()
    context.runtime.publish("record", {"enabled": False})
    assert await evaluate_condition(
        context,
        {
            "all": [
                {"exists": "{{results.record.enabled}}"},
                {"eq": ["{{results.record.enabled}}", False]},
            ]
        },
    )
    assert await evaluate_condition(context, {"any": [{"eq": [1, 2]}, {"eq": [1, 1]}]})


@pytest.mark.parametrize(
    ("condition", "message"),
    [
        ({"eq": ["{{results.absent}}", None]}, "condition.eq.*not defined"),
        ({"in": [1, "{{results.value}}"]}, "condition.in.*resolve to an array"),
        ({"page": {"url_contains": "{{results.value}}"}}, "condition.page.*non-empty string"),
        ({"page": {"url_matches": "{{pattern}}"}}, "condition.page.*unterminated"),
    ],
)
async def test_runtime_errors_are_not_false_and_include_node_paths(condition: Any, message: str) -> None:
    context = _context()
    context.runtime = RuntimeContext({"pattern": "["})
    context.runtime.publish("value", None)
    with pytest.raises(ConditionEvaluationError, match=message):
        await evaluate_condition(context, condition)


async def test_one_probe_uses_one_snapshot_and_next_probe_reads_new_results() -> None:
    context = _context()
    context.runtime.publish("count", 0)

    async def change_result(script: str, payload: dict[str, Any]) -> bool:
        context.runtime.publish("count", 1)
        return True

    cast(MagicMock, context.page).evaluate = AsyncMock(side_effect=change_result)
    assert await evaluate_condition(
        context,
        {
            "all": [
                {"js": {"script": "() => true"}},
                {"eq": ["{{results.count}}", 0]},
            ]
        },
    )
    assert await evaluate_condition(context, {"eq": ["{{results.count}}", 1]})


async def test_input_aliases_and_result_templates_stay_opaque() -> None:
    context = _context()
    context.runtime = RuntimeContext({"record": "{{results.record}}"})
    context.runtime.publish("record", {"text": "{{missing}} ${host}", "enabled": False})
    assert await evaluate_condition(context, {"exists": "{{record.enabled}}"})
    context.runtime.publish("literal", "{{missing}} ${host}")
    assert await evaluate_condition(context, {"eq": ["{{record.text}}", "{{results.literal}}"]})


@pytest.mark.parametrize(
    ("operator", "count", "visible", "expected"),
    [
        ("element_exists", 0, False, False),
        ("element_exists", 2, False, True),
        ("element_visible", 0, False, False),
        ("element_visible", 2, False, False),
        ("element_visible", 2, True, True),
        ("element_hidden", 0, False, True),
        ("element_hidden", 2, False, True),
        ("element_hidden", 2, True, False),
    ],
)
async def test_element_probes_use_first_visibility(operator: str, count: int, visible: bool, expected: bool) -> None:
    context = _context()
    page = cast(MagicMock, context.page)
    page.locator.return_value.count.return_value = count
    page.locator.return_value.first.is_visible.return_value = visible
    assert await evaluate_condition(context, {"page": {operator: "h1"}}) is expected
    page.locator.assert_called_once_with("h1")
    if operator != "element_exists":
        page.locator.return_value.first.is_visible.assert_awaited_once()


@pytest.mark.parametrize(
    ("operator", "parameter", "expected"),
    [
        ("url_contains", "https:", True),
        ("url_contains", "dashboard", False),
        ("url_matches", r"/user/\d+$", True),
        ("url_matches", "/login$", False),
    ],
)
async def test_url_probes(operator: str, parameter: str, expected: bool) -> None:
    assert await evaluate_condition(_context(), {"page": {operator: parameter}}) is expected


@pytest.mark.parametrize("count", [0, 2])
async def test_text_probe_uses_playwright_text_matching(count: int) -> None:
    context = _context()
    page = cast(MagicMock, context.page)
    page.get_by_text.return_value.count.return_value = count
    assert await evaluate_condition(context, {"page": {"text_contains": "Welcome"}}) is (count > 0)
    page.get_by_text.assert_called_once_with("Welcome", exact=False)


@pytest.mark.parametrize("supplied", [False, True])
async def test_js_distinguishes_omitted_args_from_explicit_null(supplied: bool) -> None:
    context = _context()
    predicate: dict[str, Any] = {"script": "function () {return arguments.length === 0;}"}
    if supplied:
        predicate["args"] = None
    assert await evaluate_condition(context, {"js": predicate})
    cast(MagicMock, context.page).evaluate.assert_awaited_once_with(
        CALL_FUNCTION,
        {"script": predicate["script"], "hasArgs": supplied, "args": None},
    )


async def test_js_raw_source_and_structured_args_do_not_mutate_results() -> None:
    context = _context()
    record = {"text": "quote'\n\\{{literal}} ${host}", "enabled": False}
    context.runtime.publish("record", record)
    script = "async ({record}) => record.enabled === false && '{{raw}}'.length > 0"

    async def mutate_arg(wrapper: str, payload: dict[str, Any]) -> bool:
        assert payload == {"script": script, "hasArgs": True, "args": {"record": record}}
        payload["args"]["record"]["enabled"] = True
        return True

    cast(MagicMock, context.page).evaluate = AsyncMock(side_effect=mutate_arg)
    assert await evaluate_condition(context, {"js": {"script": script, "args": {"record": "{{results.record}}"}}})
    assert context.runtime.snapshot_results()["record"] == record


@pytest.mark.parametrize("response", [None, 0, "true", [], {}])
async def test_js_requires_a_boolean(response: Any) -> None:
    context = _context()
    cast(MagicMock, context.page).evaluate.return_value = response
    with pytest.raises(ConditionEvaluationError, match="condition.js.*must return a boolean"):
        await evaluate_condition(context, {"js": {"script": "() => null"}})


async def test_js_false_and_exceptions() -> None:
    context = _context()
    page = cast(MagicMock, context.page)
    page.evaluate.return_value = False
    assert not await evaluate_condition(context, {"js": {"script": "() => false"}})
    page.evaluate.side_effect = RuntimeError("script threw")
    with pytest.raises(ConditionEvaluationError, match="condition.js.*script threw"):
        await evaluate_condition(context, {"js": {"script": "() => {throw new Error('script threw');}"}})


@pytest.mark.parametrize(
    "condition",
    [
        "element_exists: h1",
        "true",
        True,
        None,
        {},
        {"unknown": []},
        {"eq": [1]},
        {"all": []},
        {"any": []},
        {"not": []},
        {"eq": [1, 1], "ne": [1, 2]},
        {"exists": "prefix {{results.record}}"},
        {"exists": "{{results.record[-1]}}"},
        {"in": [1, None]},
        {"page": {}},
        {"page": {"unknown": "x"}},
        {"page": {"url_contains": 1}},
        {"page": {"url_matches": "["}},
        {"js": "() => true"},
        {"js": {"script": ""}},
        {"js": {"script": "() => true", "unknown": None}},
        {"eq": [float("nan"), 1]},
        {"all": [{"eq": [1, 2]}, {"in": [1]}]},
    ],
)
def test_static_validation_rejects_invalid_conditions_even_in_unvisited_nodes(condition: Any) -> None:
    assert validate_condition(condition)


def test_validation_allows_future_references_and_business_operand_keys() -> None:
    assert validate_condition({"eq": ["{{results.future}}", {"all": [], "js": "data"}]}) == []
    assert validate_condition({"page": {"url_matches": "{{pattern}}"}}) == []
    assert validate_condition({"js": {"script": "() => '{{raw}}' === '{{raw}}'"}}) == []
    assert validate_condition({"all": [{"eq": [1]}, {"exists": "{{x[-1]}}"}]})[0].startswith("condition.all[0].eq")


def test_circular_condition_data_is_rejected() -> None:
    condition: dict[str, Any] = {"not": None}
    condition["not"] = condition
    assert "circular data" in validate_condition(condition)[0]


def test_loop_validates_the_same_condition_contract() -> None:
    assert LoopStep.validate_params({"steps": [], "while": {"exists": "{{results.future}}"}}) == []
    assert "while.all" in LoopStep.validate_params({"steps": [], "while": {"all": []}})[0]
