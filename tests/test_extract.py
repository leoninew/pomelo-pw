"""Focused extraction schema and executor integration contracts."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest
from playwright.async_api import Error as PlaywrightError

from pomelo_pw.executor import FlowExecutor
from pomelo_pw.polling import PollTimeoutError
from pomelo_pw.runtime import RuntimeContext
from pomelo_pw.steps import get_step
from pomelo_pw.steps.base import StepContext
from pomelo_pw.steps.extract import ExtractError, ExtractStep


@pytest.fixture
def context(tmp_path: Path) -> StepContext:
    page = MagicMock()
    page.locator.return_value.evaluate_all = AsyncMock(return_value=[{"id": "a"}, {"id": "b"}])
    return StepContext(page, RuntimeContext(), tmp_path, [])


def test_registration_and_deferred_schema() -> None:
    assert get_step("extract") is ExtractStep
    assert not ExtractStep.validate_params(
        {
            "selector": "#{{record.id}}",
            "mode": "{{mode}}",
            "fields": {
                "id": {"read": "attribute", "attribute": "data-id"},
                "note": {"selector": ".note", "required": "{{required}}", "default": "{{fallback}}"},
                "name": "{{name_config}}",
            },
            "save_as": "records",
        }
    )
    assert not ExtractStep.validate_params({"selector": "tr", "fields": "{{mapping}}"})


@pytest.mark.parametrize(
    "params, location",
    [
        ({"selector": ""}, "selector"),
        ({"mode": "first"}, "mode"),
        ({"read": "html"}, "read"),
        ({"read": "url"}, "attribute"),
        ({"attribute": "href"}, "attribute"),
        ({"read": "value", "trim": True}, "trim"),
        ({"required": "false"}, "required"),
        ({"default": 0}, "default"),
        ({"required": False, "default": float("nan")}, "default"),
        ({"fields": {}}, "fields"),
        ({"fields": {"invalid-key": {}}}, "fields keys"),
        ({"fields": {"name": ".name"}}, "fields.name"),
        ({"fields": {"name": {"selector": "", "first": True}}}, "fields.name"),
        ({"fields": {"name": {}}, "read": "text"}, "fields cannot"),
    ],
)
def test_invalid_schema(params: dict[str, Any], location: str) -> None:
    errors = ExtractStep.validate_params({"selector": "tr", **params})
    assert any(location in error for error in errors)


def test_recursive_validation_locates_field() -> None:
    errors = FlowExecutor().validate_flow(
        {
            "steps": [
                {
                    "type": "if",
                    "condition": {"eq": [1, 1]},
                    "then": [{"type": "extract", "selector": "tr", "fields": {"link": {"read": "url"}}}],
                }
            ]
        }
    )
    assert any("steps[0].then[0]" in error and "fields.link.attribute" in error for error in errors)


async def test_structured_transport_and_result_binding(context: StepContext) -> None:
    context.runtime.flow_inputs["mapping"] = {
        "note": {"selector": ".note", "required": False, "default": {"flag": False, "count": 0, "meta": None}}
    }
    await FlowExecutor()._execute_step(
        {"type": "extract", "selector": "tr", "mode": "all", "fields": "{{mapping}}", "save_as": "records"},
        context,
        "1",
        1,
    )
    page = cast(MagicMock, context.page)
    page.locator.assert_called_once_with("tr")
    args = page.locator.return_value.evaluate_all.call_args.args
    assert isinstance(args[1], str)
    assert json.loads(args[1]) == {"mode": "all", "fields": context.runtime.flow_inputs["mapping"]}
    assert context.runtime.snapshot_results()["records"] == [{"id": "a"}, {"id": "b"}]


async def test_invalid_resolved_schema_fails_before_browser(context: StepContext) -> None:
    context.runtime.flow_inputs["mapping"] = {"name": {"required": "false"}}
    with pytest.raises(ValueError, match="fields.name.required"):
        await FlowExecutor()._execute_step(
            {"type": "extract", "selector": "tr", "fields": "{{mapping}}"}, context, "1", 1
        )
    cast(MagicMock, context.page).locator.assert_not_called()


async def test_extracted_collection_and_nested_late_resolution(context: StepContext) -> None:
    read = cast(AsyncMock, cast(MagicMock, context.page).locator.return_value.evaluate_all)
    read.side_effect = [[{"id": "a"}, {"id": "b"}], {"name": "{{literal}}"}, {"name": "Beta"}]
    context.runtime.flow_inputs["config"] = {"read": "text", "trim": False}
    await FlowExecutor()._execute_steps(
        [
            {"type": "extract", "selector": "tr", "mode": "all", "save_as": "records"},
            {
                "type": "foreach",
                "items": "{{results.records}}",
                "as": "record",
                "steps": [
                    {
                        "type": "if",
                        "condition": {"in": ["{{record.id}}", ["a", "b"]]},
                        "then": [
                            {
                                "type": "extract",
                                "selector": "#{{record.id}}",
                                "fields": {"name": "{{config}}"},
                                "save_as": "selected",
                            }
                        ],
                    }
                ],
            },
        ],
        context,
    )
    page = cast(MagicMock, context.page)
    assert [call.args[0] for call in page.locator.call_args_list] == ["tr", "#a", "#b"]
    assert json.loads(read.call_args_list[1].args[1]) == {"fields": {"name": {"read": "text", "trim": False}}}
    assert context.runtime.snapshot_results()["selected"] == {"name": "Beta"}
    assert "record" not in context.inputs


async def test_error_keeps_field_location_and_invalidates_old_result(context: StepContext) -> None:
    read = cast(AsyncMock, cast(MagicMock, context.page).locator.return_value.evaluate_all)
    read.side_effect = PlaywrightError("extract rows[1].fields.name: element is missing")
    context.runtime.publish("records", ["old"])
    with pytest.raises(ExtractError, match=r"rows\[1\].fields.name"):
        await FlowExecutor()._execute_step(
            {"type": "extract", "selector": "tr", "mode": "all", "save_as": "records"}, context, "1", 1
        )
    assert "records" not in context.runtime.snapshot_results()


async def test_poll_discards_late_extraction(context: StepContext) -> None:
    async def slow_snapshot(*args: Any) -> list[str]:
        await asyncio.sleep(0.03)
        return ["late"]

    cast(AsyncMock, cast(MagicMock, context.page).locator.return_value.evaluate_all).side_effect = slow_snapshot
    with pytest.raises(PollTimeoutError):
        await FlowExecutor()._execute_step(
            {
                "type": "poll",
                "until": {"eq": [1, 1]},
                "timeout": 10,
                "steps": [{"type": "extract", "selector": "tr", "mode": "all", "save_as": "records"}],
            },
            context,
            "1",
            1,
        )
    await asyncio.sleep(0.04)
    assert "records" not in context.runtime.snapshot_results()
