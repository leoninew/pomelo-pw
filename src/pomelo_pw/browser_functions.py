"""Shared browser function invocation with JSON arguments and return values."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from pomelo_pw.runtime import NO_OUTPUT, JsonValue, snapshot_json

if TYPE_CHECKING:
    from playwright.async_api import Page

CALL_FUNCTION = """async ({script, hasArgs, args}) => {
    const fn = (0, eval)('(' + script + '\\n)');
    if (typeof fn !== 'function') {
        throw new Error('script must be a function expression');
    }
    const result = hasArgs ? await fn(args) : await fn();
    const ancestors = new Set();
    const validate = (value, path) => {
        if (value === null || typeof value === 'string' || typeof value === 'boolean') return;
        if (typeof value === 'number' && Number.isFinite(value)) return;
        if (typeof value !== 'object') throw new Error(path + ': unsupported JSON value');
        if (!Array.isArray(value) && Object.getPrototypeOf(value) !== Object.prototype
            && Object.getPrototypeOf(value) !== null) throw new Error(path + ': expected a JSON object');
        if (ancestors.has(value)) throw new Error(path + ': circular data is not supported');
        if (Object.getOwnPropertySymbols(value).length) throw new Error(path + ': symbol keys are not supported');
        ancestors.add(value);
        if (Array.isArray(value)) {
            for (let i = 0; i < value.length; i++) validate(value[i], path + '[' + i + ']');
        } else {
            for (const key of Object.keys(value)) validate(value[key], path + '.' + key);
        }
        ancestors.delete(value);
    };
    validate(result, 'output');
    return result;
}"""

# Playwright polls synchronously; promises must settle into state before returning true.
WAIT_FOR_BOOLEAN = """payload => {
    const state = payload.waitState ??= {pending: false, ready: false, error: null};
    if (state.error !== null) throw state.error;
    if (state.ready) return true;
    if (state.pending) return false;
    const fn = (0, eval)('(' + payload.script + '\\n)');
    if (typeof fn !== 'function') throw new Error('script must be a function expression');
    const check = value => {
        if (typeof value !== 'boolean') throw new Error('JS predicate must return a boolean');
        return value;
    };
    const result = payload.hasArgs ? fn(JSON.parse(payload.args)) : fn();
    if (result === null || result === undefined || typeof result.then !== 'function') {
        return check(result);
    }
    state.pending = true;
    Promise.resolve(result).then(value => {
        state.ready = check(value);
        state.pending = false;
    }).catch(error => {
        state.error = error instanceof Error ? error : new Error(String(error));
        state.pending = false;
    });
    return false;
}"""


def _function_payload(script: str, args: Any) -> dict[str, Any]:
    return {
        "script": script.strip(),
        "hasArgs": args is not NO_OUTPUT,
        "args": snapshot_json(None if args is NO_OUTPUT else args),
    }


async def call_browser_function(page: Page, script: str, args: Any = NO_OUTPUT) -> JsonValue:
    return snapshot_json(await page.evaluate(CALL_FUNCTION, _function_payload(script, args)))


async def wait_for_browser_function(
    page: Page, script: str, args: Any = NO_OUTPUT, *, timeout: float, interval: float
) -> None:
    """Wait for a strict boolean predicate using Playwright's navigation-aware task."""
    payload = _function_payload(script, args)
    # The wait API recursively removes None from dictionaries before serializing them.
    payload["args"] = json.dumps(payload["args"], ensure_ascii=False)
    handle = await page.wait_for_function(WAIT_FOR_BOOLEAN, arg=payload, timeout=timeout, polling=interval)
    await handle.dispose()
