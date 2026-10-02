"""Assertions reuse typed conditions and only observe visited nodes."""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from pomelo_pw.conditions import ConditionEvaluationError
from pomelo_pw.executor import FlowExecutor
from pomelo_pw.runtime import RuntimeContext
from pomelo_pw.steps.assertion import AssertionFailed, AssertStep
from pomelo_pw.steps.base import StepContext


@pytest.fixture
def context(tmp_path: Path) -> StepContext:
    page = MagicMock(url="https://example.com/current")
    page.evaluate = AsyncMock(return_value=False)
    runtime = RuntimeContext({"expected": 0})
    runtime.publish("actual", False)
    return StepContext(page, runtime, tmp_path, [])


async def test_failure_preserves_typed_actual_and_short_circuits(context: StepContext) -> None:
    condition = {"all": [{"eq": ["{{results.actual}}", "{{expected}}"]}, {"exists": "{{missing}}"}]}
    with pytest.raises(AssertionFailed, match="Unexpected result") as raised:
        await FlowExecutor()._execute_step(
            {"type": "assert", "condition": condition, "message": "Unexpected result"}, context, "1", 1
        )
    details = raised.value.diagnostics["assertion"]
    assert details["condition"] == condition
    operands = [entry for entry in details["observed"] if "value" in entry]
    assert [entry["value"] for entry in operands] == [False, 0]
    assert type(operands[0]["value"]) is bool
    assert not any("missing" in str(entry) for entry in details["observed"])


async def test_js_predicate_runs_once_and_reports_result(context: StepContext) -> None:
    with pytest.raises(AssertionFailed) as raised:
        await AssertStep().execute(context, {"condition": {"js": {"script": "() => false"}}})
    context.page.evaluate.assert_awaited_once()  # type: ignore[attr-defined]
    assert raised.value.diagnostics["assertion"]["observed"] == [{"path": "condition.js", "result": False}]


async def test_condition_evaluation_error_is_not_an_assertion(context: StepContext) -> None:
    with pytest.raises(ConditionEvaluationError, match="missing"):
        await AssertStep().execute(context, {"condition": {"eq": ["{{missing}}", 1]}})


async def test_page_assertion_records_current_url(context: StepContext) -> None:
    with pytest.raises(AssertionFailed) as raised:
        await AssertStep().execute(context, {"condition": {"page": {"url_contains": "/expected"}}})
    assert {"path": "condition.page.url", "value": "https://example.com/current"} in (
        raised.value.diagnostics["assertion"]["observed"]
    )


@pytest.mark.parametrize("params", [{}, {"condition": "true"}, {"condition": {"eq": [1, 1]}, "message": ""}])
def test_assertion_validation(params: dict[str, Any]) -> None:
    assert AssertStep.validate_params(params)
