"""HTTP requests sharing the current browser context's cookie storage."""

from __future__ import annotations

import asyncio
import json
import math
from typing import Any
from urllib.parse import urljoin, urlsplit

from playwright.async_api import APIResponse
from playwright.async_api import Error as PlaywrightError
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from pomelo_pw.runtime import snapshot_json, validate_json
from pomelo_pw.steps.base import BaseStep, StepContext, StepResult, StepSpec, register_step
from pomelo_pw.substitution import REFERENCE, validate_reference

METHODS = {"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"}


class RequestNetworkError(RuntimeError):
    """The HTTP request did not receive a response."""


class RequestTimeoutError(TimeoutError):
    """The request or response read exceeded its time budget."""


class RequestStatusError(RuntimeError):
    """The final HTTP status did not match the declared expectation."""


class RequestResponseError(RuntimeError):
    """The response could not be read as the declared JSON or text type."""


_pending_requests: set[asyncio.Task[StepResult]] = set()


def _finish_request(task: asyncio.Task[StepResult]) -> None:
    _pending_requests.discard(task)
    if not task.cancelled():
        task.exception()


def _is_reference(value: Any) -> bool:
    try:
        validate_reference(value)
        return True
    except ValueError:
        return False


def _resolve_url(url: str, page_url: str) -> str:
    parts = urlsplit(url)
    if not parts.scheme:
        base = urlsplit(page_url)
        if base.scheme not in {"http", "https"} or not base.hostname:
            raise ValueError("Relative request URL requires a current HTTP(S) page; use an absolute URL instead")
        url = urljoin(page_url, url)
        parts = urlsplit(url)
    if parts.scheme not in {"http", "https"} or not parts.hostname:
        raise ValueError("Request URL must resolve to an absolute HTTP(S) URL")
    # Accessing port also validates malformed authority values before sending.
    _ = parts.port
    return url


@register_step
class RequestStep(BaseStep):
    spec = StepSpec(
        name="request",
        description="Send an HTTP request with browser cookies and JSON or text output",
        required_params=["url"],
        optional_params={
            "method": "GET",
            "query": {},
            "headers": {},
            "json": None,
            "response": "json",
            "expected_status": None,
            "timeout": 30000,
        },
        produces_output=True,
    )

    @classmethod
    def _validate_fields(cls, params: dict[str, Any], *, resolved: bool) -> list[str]:
        errors: list[str] = []

        def deferred(value: Any) -> bool:
            return not resolved and _is_reference(value)

        if "url" in params:
            url = params["url"]
            if not isinstance(url, str) or not url.strip():
                errors.append("url must be a non-empty string")
            elif resolved or not any(match.group(1) is not None for match in REFERENCE.finditer(url)):
                try:
                    _resolve_url(url, "https://validation.invalid/page")
                except ValueError as error:
                    errors.append(f"url: {error}")

        for key, choices in (("method", METHODS), ("response", {"json", "text"})):
            if key in params and not deferred(params[key]):
                value = params[key]
                if not isinstance(value, str) or value not in choices:
                    errors.append(f"{key} must be one of: {', '.join(sorted(choices))}")

        for key in ("headers", "query"):
            if key not in params or deferred(params[key]):
                continue
            mapping = params[key]
            if not isinstance(mapping, dict):
                errors.append(f"{key} must be an object")
                continue
            for name, value in mapping.items():
                if not isinstance(name, str) or not name.strip():
                    errors.append(f"{key} keys must be non-empty strings")
                if deferred(value):
                    continue
                valid = isinstance(value, str) or (
                    key == "query" and isinstance(value, (bool, int, float)) and math.isfinite(value)
                )
                if not valid:
                    kind = "a string" if key == "headers" else "a string, finite number or boolean"
                    errors.append(f"{key}.{name} must be {kind}")

        if "json" in params:
            try:
                validate_json(params["json"], "json")
            except ValueError as error:
                errors.append(str(error))
            method = params.get("method", "GET")
            if isinstance(method, str) and method in {"GET", "HEAD"}:
                errors.append("json is not allowed with GET or HEAD")

        if "expected_status" in params and not deferred(params["expected_status"]):
            expected = params["expected_status"]
            statuses = expected if isinstance(expected, list) else [expected]
            if not statuses or any(
                not deferred(status) and (type(status) is not int or not 100 <= status <= 599) for status in statuses
            ):
                errors.append("expected_status must be an HTTP status integer (100-599) or a non-empty list of them")

        if "timeout" in params and not deferred(params["timeout"]):
            timeout = params["timeout"]
            if (
                isinstance(timeout, bool)
                or not isinstance(timeout, (int, float))
                or not math.isfinite(timeout)
                or timeout <= 0
            ):
                errors.append("timeout must be a finite positive number or a complete reference")
        return errors

    @classmethod
    def validate_params(cls, params: dict[str, Any]) -> list[str]:
        return [*super().validate_params(params), *cls._validate_fields(params, resolved=False)]

    @classmethod
    def validate_resolved_params(cls, params: dict[str, Any]) -> list[str]:
        return [*super().validate_params(params), *cls._validate_fields(params, resolved=True)]

    async def execute(self, context: StepContext, params: dict[str, Any]) -> StepResult:
        errors = self.validate_resolved_params(params)
        if errors:
            return StepResult(success=False, message="; ".join(errors))

        url = _resolve_url(params["url"], context.page.url)
        method = params.get("method", "GET")
        timeout = params.get("timeout", 30000)
        mode = params.get("response", "json")
        headers = dict(params.get("headers", {}))
        options: dict[str, Any] = {
            "method": method,
            "params": {
                key: json.dumps(value) if isinstance(value, bool) else value
                for key, value in params.get("query", {}).items()
            },
            "headers": headers,
            "timeout": timeout,
            "fail_on_status_code": False,
        }
        if "json" in params:
            options["data"] = json.dumps(params["json"], ensure_ascii=False, allow_nan=False)
            if not any(name.lower() == "content-type" for name in headers):
                headers["Content-Type"] = "application/json"

        deadline = asyncio.get_running_loop().time() + timeout / 1000

        async def read_response() -> StepResult:
            response: APIResponse | None = None
            try:
                try:
                    response = await context.page.context.request.fetch(url, **options)
                except PlaywrightTimeoutError:
                    raise
                except PlaywrightError as error:
                    raise RequestNetworkError(f"HTTP network failure for {method} {url}: {error}") from error

                if asyncio.get_running_loop().time() >= deadline:
                    raise TimeoutError
                expected = params.get("expected_status")
                statuses = expected if isinstance(expected, list) else [expected]
                accepted = 200 <= response.status < 300 if expected is None else response.status in statuses
                if not accepted:
                    expectation = "200-299" if expected is None else str(expected)
                    raise RequestStatusError(
                        f"Unexpected HTTP status {response.status} for {method} {response.url}; expected {expectation}"
                    )

                try:
                    body = await response.json() if mode == "json" else await response.text()
                    output = snapshot_json(
                        {"url": response.url, "status": response.status, "headers": response.headers, "body": body}
                    )
                except (ValueError, PlaywrightError) as error:
                    raise RequestResponseError(
                        f"Invalid {mode} response for {method} {response.url} (HTTP {response.status}): {error}"
                    ) from error
                if asyncio.get_running_loop().time() >= deadline:
                    raise TimeoutError
                return StepResult(
                    success=True, message=f"HTTP {method} {response.url}: {response.status}", output=output
                )
            finally:
                if response is not None:
                    await response.dispose()

        # Keep native protocol calls alive so late responses are released and errors consumed.
        task = asyncio.create_task(read_response())
        _pending_requests.add(task)
        task.add_done_callback(_finish_request)
        try:
            async with asyncio.timeout_at(deadline):
                return await asyncio.shield(task)
        except (TimeoutError, PlaywrightTimeoutError) as error:
            raise RequestTimeoutError(f"HTTP request timed out after {timeout:g}ms for {method} {url}") from error
