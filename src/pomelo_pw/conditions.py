"""Structured data, page and browser-function conditions."""

from __future__ import annotations

import asyncio
import math
import re
from copy import deepcopy
from typing import TYPE_CHECKING, Any

from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from pomelo_pw.browser_functions import call_browser_function, wait_for_browser_function
from pomelo_pw.runtime import NO_OUTPUT, JsonValue, snapshot_json, validate_json
from pomelo_pw.substitution import REFERENCE, UndefinedVariableError, substitute_vars, validate_reference

if TYPE_CHECKING:
    from pomelo_pw.steps.base import StepContext

PAGE_OPERATORS = frozenset(
    {"element_exists", "element_visible", "element_hidden", "url_contains", "url_matches", "text_contains"}
)


class ConditionEvaluationError(ValueError):
    """A condition could not be evaluated, with its node path attached."""


class ConditionWaitTimeout(TimeoutError):
    """A valid condition did not become true before its deadline."""


def _has_reference(value: Any) -> bool:
    return isinstance(value, str) and any(match.group(1) is not None for match in REFERENCE.finditer(value))


def _validate_operand(value: Any, path: str) -> list[str]:
    errors = []
    if isinstance(value, str):
        for match in REFERENCE.finditer(value):
            if match.group(1) is not None:
                try:
                    validate_reference(match.group())
                except ValueError as error:
                    errors.append(f"{path}: {error}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            errors.extend(_validate_operand(item, f"{path}[{index}]"))
    elif isinstance(value, dict):
        for key, item in value.items():
            errors.extend(_validate_operand(item, f"{path}.{key}"))
    return errors


def _validate_node(condition: Any, path: str) -> list[str]:
    if not isinstance(condition, dict) or len(condition) != 1:
        return [f"{path}: must be an object with exactly one operator"]
    operator, value = next(iter(condition.items()))
    location = f"{path}.{operator}"
    if operator in ("all", "any"):
        if not isinstance(value, list) or not value:
            return [f"{location}: must be a non-empty list of conditions"]
        return [error for index, item in enumerate(value) for error in _validate_node(item, f"{location}[{index}]")]
    if operator == "not":
        return _validate_node(value, location)
    if operator == "exists":
        try:
            validate_reference(value)
        except ValueError as error:
            return [f"{location}: {error}"]
        return []
    if operator in ("eq", "ne", "in"):
        if not isinstance(value, list) or len(value) != 2:
            return [f"{location}: must be a list of exactly two operands"]
        errors = _validate_operand(value, location)
        if operator == "in" and not isinstance(value[1], list) and not _has_reference(value[1]):
            errors.append(f"{location}[1]: collection must be an array")
        return errors
    if operator == "page":
        if not isinstance(value, dict) or len(value) != 1:
            return [f"{location}: must be an object with exactly one page operator"]
        page_operator, parameter = next(iter(value.items()))
        location = f"{location}.{page_operator}"
        if page_operator not in PAGE_OPERATORS:
            return [f"{location}: unsupported page operator"]
        if not isinstance(parameter, str) or not parameter.strip():
            return [f"{location}: must be a non-empty string"]
        errors = _validate_operand(parameter, location)
        if page_operator == "url_matches" and not _has_reference(parameter):
            try:
                re.compile(parameter)
            except re.error as error:
                errors.append(f"{location}: invalid regular expression: {error}")
        return errors
    if operator == "js":
        if not isinstance(value, dict):
            return [f"{location}: must be an object containing script and optional args"]
        errors = []
        for key in value.keys() - {"script", "args"}:
            errors.append(f"{location}.{key}: unknown parameter")
        script = value.get("script")
        if not isinstance(script, str) or not script.strip():
            errors.append(f"{location}.script: must be a non-empty function expression")
        if "args" in value:
            errors.extend(_validate_operand(value["args"], f"{location}.args"))
        return errors
    return [f"{location}: unsupported condition operator"]


def validate_condition(condition: Any, path: str = "condition") -> list[str]:
    """Validate the whole condition tree without executing or resolving it."""
    try:
        validate_json(condition, path)
    except ValueError as error:
        return [str(error)]
    return _validate_node(condition, path)


def _json_equal(left: JsonValue, right: JsonValue) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return type(left) is type(right) and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return left == right
    if left is None or right is None:
        return left is right
    if isinstance(left, str) and isinstance(right, str):
        return left == right
    if isinstance(left, list) and isinstance(right, list):
        return len(left) == len(right) and all(_json_equal(a, b) for a, b in zip(left, right, strict=True))
    if isinstance(left, dict) and isinstance(right, dict):
        return left.keys() == right.keys() and all(_json_equal(value, right[key]) for key, value in left.items())
    return False


class _ConditionEvaluator:
    def __init__(self, context: StepContext, observations: list[dict[str, Any]] | None = None) -> None:
        self.page = context.page
        self.inputs = context.inputs
        self.results = context.runtime.snapshot_results()
        self.bindings = deepcopy(context.bindings)
        self.observations = observations

    def _resolve(self, value: Any, path: str = "value") -> JsonValue:
        try:
            resolved = snapshot_json(
                substitute_vars({"value": value}, self.inputs, self.results, self.bindings)["value"]
            )
        except UndefinedVariableError:
            if self.observations is not None:
                self.observations.append({"path": path, "expression": snapshot_json(value), "missing": True})
            raise
        if self.observations is not None:
            self.observations.append({"path": path, "expression": snapshot_json(value), "value": resolved})
        return resolved

    def _page_parameter(self, value: Any, operator: str, path: str | None = None) -> str:
        parameter = self._resolve(value, path or operator)
        if not isinstance(parameter, str) or not parameter.strip():
            raise ValueError(f"{operator} must resolve to a non-empty string")
        return parameter

    async def wait_for_page(self, condition: dict[str, Any], timeout: float) -> None:
        operator, value = next(iter(condition.items()))
        parameter = self._page_parameter(value, operator)
        if operator == "url_contains":
            await self.page.wait_for_url(lambda url: parameter in url, timeout=timeout, wait_until="commit")
        elif operator == "url_matches":
            await self.page.wait_for_url(re.compile(parameter), timeout=timeout, wait_until="commit")
        elif operator == "text_contains":
            await self.page.get_by_text(parameter, exact=False).first.wait_for(state="attached", timeout=timeout)
        elif operator == "element_exists":
            await self.page.locator(parameter).first.wait_for(state="attached", timeout=timeout)
        elif operator == "element_visible":
            await self.page.locator(parameter).first.wait_for(state="visible", timeout=timeout)
        else:
            await self.page.locator(parameter).first.wait_for(state="hidden", timeout=timeout)

    async def evaluate(self, condition: dict[str, Any], path: str) -> bool:
        operator, value = next(iter(condition.items()))
        location = f"{path}.{operator}"
        try:
            result = await self._evaluate(operator, value, location)
            if self.observations is not None:
                self.observations.append({"path": location, "result": result})
            return result
        except ConditionEvaluationError:
            raise
        except Exception as error:
            raise ConditionEvaluationError(f"{location}: {error}") from error

    async def _evaluate(self, operator: str, value: Any, path: str) -> bool:
        if operator in ("all", "any"):
            for index, child in enumerate(value):
                result = await self.evaluate(child, f"{path}[{index}]")
                if operator == "all" and not result:
                    return False
                if operator == "any" and result:
                    return True
            return operator == "all"
        if operator == "not":
            return not await self.evaluate(value, path)
        if operator == "exists":
            try:
                self._resolve(value, path)
            except UndefinedVariableError:
                return False
            return True
        if operator in ("eq", "ne", "in"):
            left, right = self._resolve(value[0], f"{path}[0]"), self._resolve(value[1], f"{path}[1]")
            if operator == "in":
                if not isinstance(right, list):
                    raise ValueError("collection must resolve to an array")
                return any(_json_equal(left, item) for item in right)
            equal = _json_equal(left, right)
            return equal if operator == "eq" else not equal
        if operator == "page":
            page_operator, parameter = next(iter(value.items()))
            parameter = self._page_parameter(parameter, page_operator, f"{path}.{page_operator}")
            if page_operator == "url_contains":
                if self.observations is not None:
                    self.observations.append({"path": f"{path}.url", "value": self.page.url})
                return parameter in self.page.url
            if page_operator == "url_matches":
                if self.observations is not None:
                    self.observations.append({"path": f"{path}.url", "value": self.page.url})
                return re.search(parameter, self.page.url) is not None
            if page_operator == "text_contains":
                return await self.page.get_by_text(parameter, exact=False).count() > 0
            locator = self.page.locator(parameter)
            if page_operator == "element_exists":
                return await locator.count() > 0
            visible = await locator.first.is_visible()
            return visible if page_operator == "element_visible" else not visible
        args = self._resolve(value["args"], f"{path}.args") if "args" in value else NO_OUTPUT
        predicate_result = await call_browser_function(self.page, value["script"], args)
        if not isinstance(predicate_result, bool):
            raise ValueError("JS predicate must return a boolean")
        return predicate_result


async def evaluate_condition(
    context: StepContext, condition: Any, path: str = "condition", *, observations: list[dict[str, Any]] | None = None
) -> bool:
    """Evaluate visited nodes against one input/result snapshot and live page state."""
    errors = validate_condition(condition, path)
    if errors:
        raise ConditionEvaluationError("; ".join(errors))
    return await _ConditionEvaluator(context, observations).evaluate(condition, path)


def _navigation_destroyed_context(error: BaseException) -> bool:
    while error.__cause__ is not None:
        error = error.__cause__
    return isinstance(error, PlaywrightError) and any(
        message in error.message
        for message in (
            "Execution context was destroyed, most likely because of a navigation",
            "Cannot find context with specified id",
        )
    )


def _finish_cancelled_probe(task: asyncio.Task[bool]) -> None:
    if not task.cancelled():
        task.exception()


async def wait_for_condition(context: StepContext, condition: Any, *, timeout: float, interval: float = 100) -> None:
    """Wait against fixed runtime snapshots and live page state within one deadline."""
    for key, value in (("timeout", timeout), ("interval", interval)):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
            raise ValueError(f"{key} must be a finite positive number")
    errors = validate_condition(condition)
    if errors:
        raise ConditionEvaluationError("; ".join(errors))
    evaluator = _ConditionEvaluator(context)
    operator, value = next(iter(condition.items()))
    try:
        if operator == "page":
            await evaluator.wait_for_page(value, timeout)
            return
        if operator == "js":
            args = evaluator._resolve(value["args"]) if "args" in value else NO_OUTPUT
            await wait_for_browser_function(context.page, value["script"], args, timeout=timeout, interval=interval)
            return
        async with asyncio.timeout(timeout / 1000):
            while True:
                probe = asyncio.create_task(evaluator.evaluate(condition, "condition"))
                try:
                    # Let in-flight Playwright calls finish and consume late errors.
                    if await asyncio.shield(probe):
                        return
                except asyncio.CancelledError:
                    probe.add_done_callback(_finish_cancelled_probe)
                    raise
                except ConditionEvaluationError as error:
                    if not _navigation_destroyed_context(error):
                        raise
                await asyncio.sleep(interval / 1000)
    except (TimeoutError, PlaywrightTimeoutError) as error:
        raise ConditionWaitTimeout(f"Timeout after {timeout:g}ms waiting for condition {condition!r}") from error
    except ConditionEvaluationError:
        raise
    except Exception as error:
        raise ConditionEvaluationError(f"condition.{operator}: {error}") from error
