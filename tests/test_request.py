"""Focused HTTP step contracts and control-flow integration."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from pomelo_pw.executor import FlowExecutor
from pomelo_pw.polling import PollTimeoutError
from pomelo_pw.runtime import RuntimeContext
from pomelo_pw.steps import get_step
from pomelo_pw.steps.base import StepContext
from pomelo_pw.steps.request import (
    RequestNetworkError,
    RequestResponseError,
    RequestStatusError,
    RequestStep,
    RequestTimeoutError,
)


def response(body: Any, status: int = 200) -> MagicMock:
    result = MagicMock(status=status, url="https://example.com/api/tasks")
    result.headers = {"content-type": "application/json"}
    result.json = AsyncMock(return_value=body)
    result.text = AsyncMock(return_value="")
    result.dispose = AsyncMock()
    return result


@pytest.fixture
def context(tmp_path: Path) -> StepContext:
    page = MagicMock(url="https://example.com/app/index.html")
    page.context.request.fetch = AsyncMock(return_value=response({"id": 7, "enabled": False}))
    return StepContext(page, RuntimeContext(), tmp_path, [])


def test_registration_and_static_typed_references() -> None:
    assert get_step("request") is RequestStep
    assert not RequestStep.validate_params(
        {
            "type": "request",
            "url": "/api/{{item.id}}",
            "method": "{{method}}",
            "json": "{{payload}}",
            "query": "{{filters}}",
            "headers": {"Authorization": "Bearer {{token}}"},
            "expected_status": [200, "{{status}}"],
            "timeout": "{{duration}}",
            "save_as": "task",
        }
    )


@pytest.mark.parametrize(
    "params",
    [
        {"url": ""},
        {"url": "file:///tmp/file"},
        {"url": "https://example.com:bad/api"},
        {"method": "get"},
        {"json": None},
        {"method": "HEAD", "json": {}},
        {"query": {"ids": [1, 2]}},
        {"query": {"page": None}},
        {"query": {"page": float("inf")}},
        {"headers": {"X-Count": 1}},
        {"headers": None},
        {"response": "auto"},
        {"expected_status": None},
        {"expected_status": []},
        {"expected_status": [200, True]},
        {"timeout": 0},
        {"timeout": "1000"},
        {"body": {}},
    ],
)
def test_invalid_parameters(params: dict[str, Any]) -> None:
    assert RequestStep.validate_params({"type": "request", "url": "/api", **params})


def test_recursive_validation_locates_request() -> None:
    errors = FlowExecutor().validate_flow(
        {"steps": [{"type": "foreach", "items": [], "steps": [{"type": "request", "url": "/api", "timeout": 0}]}]}
    )
    assert any("steps[0].steps[0]" in error and "timeout" in error for error in errors)


async def test_relative_url_typed_payload_and_public_output(context: StepContext) -> None:
    context.runtime.flow_inputs.update({"payload": {"count": 0, "enabled": False, "value": None}})
    context.runtime.publish("auth", {"token": "demo"})
    await FlowExecutor()._execute_step(
        {
            "type": "request",
            "url": "../api/tasks",
            "method": "POST",
            "query": {"page": 0, "active": False},
            "headers": {"Authorization": "Bearer {{results.auth.token}}"},
            "json": "{{payload}}",
            "save_as": "task",
        },
        context,
        "1",
        1,
    )
    fetch = cast(AsyncMock, context.page.context.request.fetch)
    args, options = fetch.call_args
    assert args == ("https://example.com/api/tasks",)
    assert options["params"] == {"page": 0, "active": "false"}
    assert options["headers"] == {"Authorization": "Bearer demo", "Content-Type": "application/json"}
    assert options["data"] == '{"count": 0, "enabled": false, "value": null}'
    assert "max_retries" not in options
    assert context.runtime.snapshot_results()["task"] == {
        "url": "https://example.com/api/tasks",
        "status": 200,
        "headers": {"content-type": "application/json"},
        "body": {"id": 7, "enabled": False},
    }
    fetch.return_value.dispose.assert_awaited_once()


async def test_null_body_custom_content_type_and_text_response(context: StepContext) -> None:
    fetch = cast(AsyncMock, context.page.context.request.fetch)
    fetch.return_value = response(None, 204)
    result = await RequestStep().execute(
        context,
        {
            "url": "/api/tasks",
            "method": "POST",
            "json": None,
            "headers": {"content-type": "application/vnd.demo+json"},
            "response": "text",
            "expected_status": [202, 204],
        },
    )
    assert result.success
    assert fetch.call_args.kwargs["data"] == "null"
    assert fetch.call_args.kwargs["headers"] == {"content-type": "application/vnd.demo+json"}
    assert isinstance(result.output, dict) and result.output["body"] == ""
    fetch.return_value.json.assert_not_called()
    fetch.return_value.dispose.assert_awaited_once()


async def test_url_base_and_runtime_types_fail_before_network(context: StepContext) -> None:
    page = cast(MagicMock, context.page)
    page.url = "about:blank"
    with pytest.raises(ValueError, match="current HTTP"):
        await RequestStep().execute(context, {"url": "/api"})
    assert not RequestStep.validate_resolved_params({"url": "https://example.com/api"})
    await RequestStep().execute(context, {"url": "https://example.com/api"})
    page.context.request.fetch.reset_mock()
    context.runtime.flow_inputs["bad_header"] = 7
    with pytest.raises(ValueError, match="headers.X-Count"):
        await FlowExecutor()._execute_step(
            {"type": "request", "url": "/api", "headers": {"X-Count": "{{bad_header}}"}}, context, "1", 1
        )
    page.context.request.fetch.assert_not_called()


async def test_status_failure_precedes_parsing_and_clears_binding(context: StepContext) -> None:
    fetch = cast(AsyncMock, context.page.context.request.fetch)
    fetch.return_value = response({"error": "not found"}, 404)
    context.runtime.publish("task", {"body": "old"})
    with pytest.raises(RequestStatusError, match="404.*expected 200-299"):
        await FlowExecutor()._execute_step({"type": "request", "url": "/api", "save_as": "task"}, context, "1", 1)
    assert "task" not in context.runtime.snapshot_results()
    fetch.return_value.json.assert_not_called()
    fetch.return_value.dispose.assert_awaited_once()
    result = await RequestStep().execute(context, {"url": "/api", "expected_status": 404})
    assert result.success


@pytest.mark.parametrize("kind", ["syntax", "nonfinite"])
async def test_invalid_json_disposes_response(context: StepContext, kind: str) -> None:
    fetch = cast(AsyncMock, context.page.context.request.fetch)
    if kind == "syntax":
        fetch.return_value.json.side_effect = ValueError("invalid JSON")
    else:
        fetch.return_value.json.return_value = {"value": float("nan")}
    with pytest.raises(RequestResponseError, match="Invalid json response"):
        await RequestStep().execute(context, {"url": "/api"})
    fetch.return_value.dispose.assert_awaited_once()


async def test_network_failure_does_not_retry_write_by_default(context: StepContext) -> None:
    fetch = cast(AsyncMock, context.page.context.request.fetch)
    fetch.side_effect = PlaywrightError("connection refused")
    with pytest.raises(RequestNetworkError, match="connection refused"):
        await FlowExecutor()._execute_step({"type": "request", "url": "/api", "method": "POST"}, context, "1", 1)
    assert fetch.await_count == 1


@pytest.mark.parametrize("native", [True, False])
async def test_request_timeout_includes_body_read(context: StepContext, native: bool) -> None:
    fetch = cast(AsyncMock, context.page.context.request.fetch)
    release = asyncio.Event()
    if native:
        fetch.side_effect = PlaywrightTimeoutError("timeout")
    else:

        async def slow_body() -> None:
            await release.wait()

        fetch.return_value.json.side_effect = slow_body
    with pytest.raises(RequestTimeoutError, match="10ms"):
        await RequestStep().execute(context, {"url": "/api", "timeout": 10})
    if not native:
        release.set()
        await asyncio.sleep(0)
        await asyncio.sleep(0)
        fetch.return_value.dispose.assert_awaited_once()


async def test_foreach_branch_and_poll_use_fresh_request_results(context: StepContext) -> None:
    fetch = cast(AsyncMock, context.page.context.request.fetch)
    pending = response({"status": "pending"})
    ready = response({"status": "ready"})
    fetch.side_effect = [PlaywrightError("transient"), pending, ready, ready]
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
                                "type": "poll",
                                "until": {"eq": ["{{results.task.body.status}}", "ready"]},
                                "timeout": 1000,
                                "interval": 1,
                                "max_attempts": 2,
                                "steps": [
                                    {
                                        "type": "request",
                                        "url": "/api/tasks/{{item}}",
                                        "retry": 1,
                                        "retry_delay": 0,
                                        "retry_on": ["RequestNetworkError"],
                                        "save_as": "task",
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        ],
        context,
    )
    assert [call.args[0] for call in fetch.call_args_list] == [
        "https://example.com/api/tasks/a",
        "https://example.com/api/tasks/a",
        "https://example.com/api/tasks/a",
        "https://example.com/api/tasks/b",
    ]


async def test_poll_clamps_request_budget_and_never_publishes_late_output(context: StepContext) -> None:
    fetch = cast(AsyncMock, context.page.context.request.fetch)
    finished = asyncio.Event()
    ready = response({"status": "ready"})

    async def slow_fetch(*args: Any, **kwargs: Any) -> MagicMock:
        await asyncio.sleep(0.05)
        finished.set()
        return ready

    fetch.side_effect = slow_fetch
    with pytest.raises(PollTimeoutError):
        await FlowExecutor()._execute_step(
            {
                "type": "poll",
                "until": {"eq": ["{{results.task.body.status}}", "ready"]},
                "timeout": 15,
                "interval": 1,
                "steps": [{"type": "request", "url": "/api", "save_as": "task", "retry": 2}],
            },
            context,
            "1",
            1,
        )
    assert 0 < fetch.call_args.kwargs["timeout"] <= 15.001
    assert context.runtime.snapshot_results() == {}
    # In-flight calls finish, but late responses are released without publishing.
    await asyncio.wait_for(finished.wait(), 1)
    await asyncio.sleep(0)
    ready.dispose.assert_awaited_once()
    assert context.runtime.snapshot_results() == {}
    assert fetch.await_count == 1
