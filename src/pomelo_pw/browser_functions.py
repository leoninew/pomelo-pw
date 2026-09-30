"""Shared browser function invocation with JSON arguments and return values."""

from __future__ import annotations

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


async def call_browser_function(page: Page, script: str, args: Any = NO_OUTPUT) -> JsonValue:
    payload = {
        "script": script.strip(),
        "hasArgs": args is not NO_OUTPUT,
        "args": snapshot_json(None if args is NO_OUTPUT else args),
    }
    return snapshot_json(await page.evaluate(CALL_FUNCTION, payload))
