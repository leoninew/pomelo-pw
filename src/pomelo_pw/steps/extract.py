"""Read scalar values or mapped records in one synchronous DOM snapshot."""

from __future__ import annotations

import json
from typing import Any

from playwright.async_api import Error as PlaywrightError

from pomelo_pw.runtime import IDENTIFIER, snapshot_json, validate_json
from pomelo_pw.steps.base import BaseStep, StepContext, StepResult, StepSpec, register_step
from pomelo_pw.substitution import validate_reference

READ_PARAMS = {"selector", "read", "attribute", "trim", "required", "default"}

_EXTRACT_SNAPSHOT = r"""(elements, encodedOptions) => {
    const options = JSON.parse(encodedOptions);
    const fail = (path, message) => { throw new Error(`extract ${path}: ${message}`); };
    const missing = (config, path, reason) => {
        if (config.required !== false) fail(path, reason);
        return Object.hasOwn(config, 'default') ? config.default : null;
    };
    const read = (root, config, path) => {
        let element = root;
        if (config.selector !== undefined) {
            let matches;
            try { matches = root.querySelectorAll(config.selector); }
            catch (error) { fail(path, `invalid field CSS selector: ${error.message}`); }
            if (matches.length > 1) fail(path, `expected one field element, found ${matches.length}`);
            element = matches[0];
        }
        if (!element) return missing(config, path, 'element is missing');
        const kind = config.read ?? 'text';
        if (kind === 'text') {
            const text = element.textContent ?? '';
            return config.trim === false ? text : text.trim();
        }
        if (kind === 'value') {
            if (!['INPUT', 'TEXTAREA', 'SELECT'].includes(element.tagName)) {
                fail(path, 'read: value requires an input, textarea or select');
            }
            return element.value;
        }
        const raw = element.getAttribute(config.attribute);
        if (raw === null) return missing(config, path, `attribute '${config.attribute}' is missing`);
        if (kind === 'attribute') return raw;
        try { return new URL(raw, element.baseURI).href; }
        catch { fail(path, `attribute '${config.attribute}' is not a valid URL`); }
    };
    if ((options.mode ?? 'one') === 'one') {
        if (elements.length > 1) fail('selector', `expected one element, found ${elements.length}`);
        if (elements.length === 0) return missing(options, 'selector', 'element is missing');
    }
    const rows = elements.map((element, index) => {
        const path = `rows[${index}]`;
        if (!Object.hasOwn(options, 'fields')) return read(element, options, path);
        return Object.fromEntries(Object.entries(options.fields).map(([name, config]) =>
            [name, read(element, config, `${path}.fields.${name}`)]));
    });
    return options.mode === 'all' ? rows : rows[0];
}"""


class ExtractError(RuntimeError):
    """A DOM snapshot could not satisfy the declared extraction contract."""


def _is_reference(value: Any) -> bool:
    try:
        validate_reference(value)
        return True
    except ValueError:
        return False


@register_step
class ExtractStep(BaseStep):
    spec = StepSpec(
        name="extract",
        description="Read DOM text, attributes, URLs, form values or mapped records",
        required_params=["selector"],
        optional_params={
            "mode": "one",
            "read": "text",
            "attribute": None,
            "trim": True,
            "fields": None,
            "required": True,
            "default": None,
        },
        produces_output=True,
    )

    @classmethod
    def _validate_fields(cls, params: dict[str, Any], *, resolved: bool) -> list[str]:
        errors: list[str] = []

        def deferred(value: Any) -> bool:
            return not resolved and _is_reference(value)

        def validate_read(config: dict[str, Any], path: str) -> None:
            for key in ("selector", "attribute"):
                if key in config and (not isinstance(config[key], str) or not config[key].strip()):
                    errors.append(f"{path}.{key} must be a non-empty string")
            kind = config.get("read", "text")
            if not deferred(kind):
                if not isinstance(kind, str) or kind not in {"text", "attribute", "url", "value"}:
                    errors.append(f"{path}.read must be text, attribute, url or value")
                elif kind in {"attribute", "url"} and "attribute" not in config:
                    errors.append(f"{path}.attribute is required with read: {kind}")
                elif kind not in {"attribute", "url"} and "attribute" in config:
                    errors.append(f"{path}.attribute is only allowed with read: attribute or url")
                if kind != "text" and "trim" in config:
                    errors.append(f"{path}.trim is only allowed with read: text")
            for key in ("trim", "required"):
                if key in config and not deferred(config[key]) and type(config[key]) is not bool:
                    errors.append(f"{path}.{key} must be a boolean")
            if "default" in config:
                required = config.get("required", True)
                if not deferred(required) and required is not False:
                    errors.append(f"{path}.default requires required: false")
                try:
                    validate_json(config["default"], f"{path}.default")
                except ValueError as error:
                    errors.append(str(error))

        mode = params.get("mode", "one")
        if not deferred(mode) and (not isinstance(mode, str) or mode not in {"one", "all"}):
            errors.append("mode must be one or all")

        validate_read(params, "extract")
        if "fields" in params:
            if any(key in params for key in ("read", "attribute", "trim")):
                errors.append("fields cannot be combined with read, attribute or trim")
            fields = params["fields"]
            if not deferred(fields):
                if not isinstance(fields, dict) or not fields:
                    errors.append("fields must be a non-empty object or a complete reference")
                else:
                    for name, config in fields.items():
                        path = f"fields.{name}"
                        if not isinstance(name, str) or not IDENTIFIER.fullmatch(name):
                            errors.append("fields keys must be ASCII identifiers")
                        if deferred(config):
                            continue
                        if not isinstance(config, dict):
                            errors.append(f"{path} must be a read configuration object")
                            continue
                        for key in config.keys() - READ_PARAMS:
                            errors.append(f"{path}: unknown parameter: {key}")
                        validate_read(config, path)
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

        options = {
            key: value for key, value in params.items() if key in (READ_PARAMS - {"selector"}) | {"mode", "fields"}
        }
        # Playwright's parameter filtering recursively omits None in object arguments.
        encoded_options = json.dumps(options, ensure_ascii=False, allow_nan=False)
        try:
            output = snapshot_json(
                await context.page.locator(params["selector"]).evaluate_all(_EXTRACT_SNAPSHOT, encoded_options)
            )
        except PlaywrightError as error:
            raise ExtractError(str(error)) from error
        count = len(output) if params.get("mode", "one") == "all" and isinstance(output, list) else 1
        return StepResult(success=True, message=f"Extracted {count} item(s) from {params['selector']}", output=output)
