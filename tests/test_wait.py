"""Targeted page-condition waits, deadlines and strict mode contracts."""

from __future__ import annotations

import asyncio
import json
import re
import subprocess
from pathlib import Path
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from playwright._impl._driver import compute_driver_executable
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from pomelo_pw.browser_functions import WAIT_FOR_BOOLEAN
from pomelo_pw.conditions import ConditionEvaluationError, ConditionWaitTimeout, wait_for_condition
from pomelo_pw.executor import FlowExecutor
from pomelo_pw.runtime import RuntimeContext
from pomelo_pw.steps.base import StepContext
from pomelo_pw.steps.wait import WaitStep


@pytest.fixture
def context(tmp_path: Path) -> StepContext:
    page = MagicMock()
    page.url = "https://example.com/items?page=2"
    page.evaluate = AsyncMock(return_value=True)
    page.wait_for_url = AsyncMock()
    page.wait_for_selector = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    page.wait_for_function = AsyncMock(return_value=MagicMock(dispose=AsyncMock()))
    page.locator.return_value.first.wait_for = AsyncMock()
    page.locator.return_value.first.is_visible = AsyncMock(return_value=True)
    page.locator.return_value.count = AsyncMock(return_value=1)
    page.get_by_text.return_value.first.wait_for = AsyncMock()
    return StepContext(page, RuntimeContext(), tmp_path, [])


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"delay": 0, "selector": "h1"},
        {"condition": {"eq": [1, 1]}, "url_contains": "/items"},
        {"selector": None},
        {"selector": " "},
        {"condition": "element_visible: h1"},
        {"condition": {"all": []}},
        {"network_idle": False},
        {"route_stable": None},
        {"delay": -1},
        {"timeout": 0, "selector": "h1"},
        {"delay": True},
        {"delay": "1"},
        {"selector": "h1", "state": "unknown"},
        {"for": "unknown"},
        {"delay": 1, "interval": 100},
        {"delay": 1, "state": "visible"},
        {"delay": 1, "route_stable_duration": 100},
        {"url_pattern": "["},
        {"condition": {"eq": [1, 1]}, "interval": float("inf")},
    ],
)
def test_invalid_wait_contracts(params: dict[str, Any]) -> None:
    assert WaitStep.validate_params(params)


@pytest.mark.parametrize(
    "params",
    [
        {"delay": 0},
        {"delay": 0.1},
        {"selector": "h1", "state": "attached"},
        {"network_idle": True},
        {"animation_stable": True},
        {"route_stable": True},
        {"for": "domcontentloaded"},
        {"url_pattern": "{{pattern}}"},
        {"condition": {"eq": ["{{results.future}}", 1]}, "interval": "{{interval}}", "timeout": "{{timeout}}"},
    ],
)
def test_valid_native_modes(params: dict[str, Any]) -> None:
    assert not WaitStep.validate_params(params)


@pytest.mark.parametrize(
    "params",
    [
        {"delay": "{{value}}"},
        {"condition": {"eq": [1, 1]}, "timeout": "{{value}}"},
        {"selector": "h1", "state": []},
        {"network_idle": "{{value}}"},
    ],
)
def test_resolved_types_are_strict(params: dict[str, Any]) -> None:
    assert WaitStep.validate_resolved_params(params)


async def test_invalid_execute_does_not_select_a_mode(context: StepContext) -> None:
    result = await WaitStep().execute(context, {"delay": 0, "selector": "h1"})
    assert not result.success and "exactly one mode" in result.message
    cast(MagicMock, context.page).wait_for_selector.assert_not_awaited()


@pytest.mark.parametrize(
    "operator,state", [("element_exists", "attached"), ("element_visible", "visible"), ("element_hidden", "hidden")]
)
async def test_page_leaf_uses_native_locator_wait(context: StepContext, operator: str, state: str) -> None:
    await wait_for_condition(context, {"page": {operator: "h1"}}, timeout=250)
    cast(MagicMock, context.page).locator.return_value.first.wait_for.assert_awaited_once_with(state=state, timeout=250)


async def test_text_and_url_leaves_use_native_wait(context: StepContext) -> None:
    page = cast(MagicMock, context.page)
    await wait_for_condition(context, {"page": {"text_contains": "Ready"}}, timeout=250)
    page.get_by_text.assert_called_once_with("Ready", exact=False)
    page.get_by_text.return_value.first.wait_for.assert_awaited_once_with(state="attached", timeout=250)
    await wait_for_condition(context, {"page": {"url_contains": "/items"}}, timeout=250)
    matcher = page.wait_for_url.await_args.args[0]
    assert matcher("https://example.com/items") and not matcher("https://example.com/other")
    assert page.wait_for_url.await_args.kwargs["wait_until"] == "commit"
    await wait_for_condition(context, {"page": {"url_matches": "/items$"}}, timeout=250)
    assert isinstance(page.wait_for_url.await_args.args[0], re.Pattern)


@pytest.mark.parametrize(
    "args,has_args", [({}, False), ({"args": None}, True), ({"args": {"key": "{{inputs.key}}"}}, True)]
)
async def test_native_js_keeps_source_and_argument_contract(
    context: StepContext, args: dict[str, Any], has_args: bool
) -> None:
    context.runtime = RuntimeContext({"key": "{{literal}}"})
    context.bindings = {"key": "{{literal}}"}
    page = cast(MagicMock, context.page)
    script = "async payload => '{{source}}' === '{{source}}'"
    await wait_for_condition(context, {"js": {"script": script, **args}}, timeout=250, interval=5)
    page.wait_for_function.assert_awaited_once_with(
        WAIT_FOR_BOOLEAN,
        arg={
            "script": script,
            "hasArgs": has_args,
            "args": json.dumps({"key": "{{literal}}"} if args.get("args") is not None else None),
        },
        timeout=250,
        polling=5,
    )
    page.wait_for_function.return_value.dispose.assert_awaited_once()


@pytest.mark.parametrize(
    "script",
    ["state => state.ready && state.optional === null", "async state => state.ready && state.optional === null"],
    ids=["sync", "async"],
)
def test_native_js_polling_observes_boolean_instead_of_promise(script: str) -> None:
    node, _ = compute_driver_executable()
    javascript = f"""
        const assert = require('node:assert/strict');
        const predicate = ({WAIT_FOR_BOOLEAN});
        const payload = {{script: {json.dumps(script)}, hasArgs: true, args: JSON.stringify({{ready: false, optional: null}})}};
        (async () => {{
            assert.equal(predicate(payload), false);
            await new Promise(setImmediate);
            assert.equal(predicate(payload), false);
            await new Promise(setImmediate);
            payload.args = JSON.stringify({{ready: true, optional: null}});
            let ready = false;
            for (let attempt = 0; attempt < 3; attempt++) {{
                ready = predicate(payload);
                assert.equal(typeof ready, 'boolean');
                if (ready) break;
                await new Promise(setImmediate);
            }}
            assert.equal(ready, true);
        }})().catch(error => {{ console.error(error); process.exitCode = 1; }});
    """
    result = subprocess.run([str(node), "-e", javascript], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


async def test_composite_immediate_and_short_circuit(context: StepContext) -> None:
    with patch("pomelo_pw.conditions.asyncio.sleep", new_callable=AsyncMock) as sleep:
        await wait_for_condition(
            context, {"any": [{"eq": [1, 1]}, {"js": {"script": "() => {throw new Error('unvisited');}"}}]}, timeout=250
        )
    sleep.assert_not_awaited()
    cast(MagicMock, context.page).evaluate.assert_not_awaited()


async def test_composite_checks_live_page_until_true(context: StepContext) -> None:
    page = cast(MagicMock, context.page)
    page.locator.return_value.first.is_visible = AsyncMock(side_effect=[False, False, True])
    await wait_for_condition(
        context,
        {"all": [{"page": {"url_contains": "page=2"}}, {"page": {"element_visible": "table"}}]},
        timeout=250,
        interval=1,
    )
    assert page.locator.return_value.first.is_visible.await_count == 3


@pytest.mark.parametrize("native", [False, True])
async def test_timeout_has_condition_and_deadline(context: StepContext, native: bool) -> None:
    page = cast(MagicMock, context.page)
    if native:
        page.wait_for_function.side_effect = PlaywrightTimeoutError("timeout")
        condition: dict[str, Any] = {"js": {"script": "() => false"}}
    else:
        condition = {"all": [{"eq": [1, 2]}]}
    with pytest.raises(ConditionWaitTimeout, match="10ms waiting for condition"):
        await wait_for_condition(context, condition, timeout=10, interval=1)


async def test_deadline_bounds_a_hanging_probe(context: StepContext) -> None:
    async def hanging(script: str, args: object) -> None:
        await asyncio.Event().wait()

    cast(MagicMock, context.page).evaluate.side_effect = hanging
    with pytest.raises(ConditionWaitTimeout):
        await wait_for_condition(context, {"all": [{"js": {"script": "async () => false"}}]}, timeout=10, interval=1)


async def test_timeout_consumes_late_playwright_errors_without_cancelling_call(context: StepContext) -> None:
    loop = asyncio.get_running_loop()
    error_handler = MagicMock()
    previous_handler = loop.get_exception_handler()
    response: asyncio.Future[bool] = loop.create_future()

    async def delayed(script: str, args: object) -> bool:
        loop.call_later(0.03, response.set_exception, PlaywrightError("late navigation failure"))
        return await response

    cast(MagicMock, context.page).evaluate.side_effect = delayed
    loop.set_exception_handler(error_handler)
    try:
        with pytest.raises(ConditionWaitTimeout):
            await wait_for_condition(context, {"all": [{"js": {"script": "() => true"}}]}, timeout=10, interval=1)
        assert not response.cancelled()
        await asyncio.sleep(0.05)
        error_handler.assert_not_called()
        assert response.done()
    finally:
        loop.set_exception_handler(previous_handler)


@pytest.mark.parametrize(
    "error",
    [
        PlaywrightError("JS predicate must return a boolean"),
        PlaywrightError("Page closed"),
        PlaywrightError("SyntaxError: bad script"),
    ],
)
async def test_predicate_errors_fail_immediately(context: StepContext, error: Exception) -> None:
    page = cast(MagicMock, context.page)
    page.evaluate.side_effect = error
    with pytest.raises(ConditionEvaluationError, match="condition.all.*js"):
        await wait_for_condition(context, {"all": [{"js": {"script": "() => null"}}]}, timeout=250)
    assert page.evaluate.await_count == 1


async def test_composite_retries_only_navigation_context_loss(context: StepContext) -> None:
    page = cast(MagicMock, context.page)
    page.evaluate.side_effect = [
        PlaywrightError("Execution context was destroyed, most likely because of a navigation"),
        True,
    ]
    await wait_for_condition(context, {"all": [{"js": {"script": "() => true"}}]}, timeout=250, interval=1)
    assert page.evaluate.await_count == 2


async def test_runtime_snapshot_stays_fixed_during_wait(context: StepContext) -> None:
    context.runtime.publish("target", 1)
    page = cast(MagicMock, context.page)
    calls = 0

    async def probe(script: str, args: dict[str, Any]) -> bool:
        nonlocal calls
        calls += 1
        assert args["args"] == 1
        context.runtime.publish("target", 2)
        return calls == 2

    page.evaluate.side_effect = probe
    await wait_for_condition(
        context,
        {"all": [{"js": {"script": "value => value === 1", "args": "{{results.target}}"}}]},
        timeout=250,
        interval=1,
    )
    assert calls == 2 and context.runtime.snapshot_results()["target"] == 2


async def test_wait_in_nested_iteration_uses_current_bindings(context: StepContext) -> None:
    page = cast(MagicMock, context.page)
    await FlowExecutor()._execute_steps(
        [
            {
                "type": "foreach",
                "items": ["a", "b"],
                "steps": [
                    {
                        "type": "if",
                        "condition": {"exists": "{{item}}"},
                        "then": [
                            {
                                "type": "wait",
                                "condition": {"js": {"script": "item => true", "args": "{{item}}"}},
                                "timeout": 250,
                            },
                        ],
                    },
                ],
            }
        ],
        context,
    )
    assert [json.loads(call.kwargs["arg"]["args"]) for call in page.wait_for_function.await_args_list] == ["a", "b"]
