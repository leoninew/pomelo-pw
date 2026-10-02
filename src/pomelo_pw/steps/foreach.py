"""Serial collection iteration step."""

from __future__ import annotations

from typing import Any

from pomelo_pw.runtime import IDENTIFIER, RESERVED_INPUT_NAMES, snapshot_json, validate_json
from pomelo_pw.steps.base import BaseStep, StepContext, StepResult, StepSpec, register_step
from pomelo_pw.substitution import validate_reference


@register_step
class ForeachStep(BaseStep):
    """Iterate over a fixed JSON array with local item and index bindings."""

    spec = StepSpec(
        name="foreach",
        description="Execute steps serially for each array item",
        required_params=["items", "steps"],
        optional_params={
            "as": "item",
            "index_as": "index",
            "collect": None,
            "max_collect_items": 1000,
            "max_collect_bytes": 1048576,
        },
        child_step_params=("steps",),
        literal_params=("as", "index_as", "collect"),
        produces_output=True,
    )

    @classmethod
    def validate_params(cls, params: dict[str, Any]) -> list[str]:
        errors = super().validate_params(params)
        names = [params.get(key, cls.spec.optional_params[key]) for key in ("as", "index_as")]
        for key, name in zip(("as", "index_as"), names, strict=True):
            if not isinstance(name, str) or not IDENTIFIER.fullmatch(name) or name in RESERVED_INPUT_NAMES:
                errors.append(f"{key} must be a non-reserved ASCII identifier")
        if names[0] == names[1]:
            errors.append("as and index_as must be different")
        if "items" in params:
            items = params["items"]
            if isinstance(items, str):
                try:
                    validate_reference(items)
                except ValueError:
                    errors.append("items must be an array or a complete {{...}} reference")
            elif not isinstance(items, list):
                errors.append("items must be an array or a complete {{...}} reference")
            else:
                try:
                    snapshot_json(items)
                except ValueError as error:
                    errors.append(f"items: {error}")
        if "steps" in params and not isinstance(params["steps"], list):
            errors.append("steps must be a list of steps")
        if "collect" in params:
            try:
                validate_json(params["collect"], "collect")
            except ValueError as error:
                errors.append(str(error))
        for key in ("max_collect_items", "max_collect_bytes"):
            if key not in params:
                continue
            if "collect" not in params:
                errors.append(f"{key} requires collect")
            value = params[key]
            if isinstance(value, str):
                try:
                    validate_reference(value)
                except ValueError:
                    errors.append(f"{key} must be a positive integer or a complete reference")
            elif type(value) is not int or value <= 0:
                errors.append(f"{key} must be a positive integer")
        return errors

    @classmethod
    def validate_resolved_params(cls, params: dict[str, Any]) -> list[str]:
        errors = super().validate_resolved_params(params)
        if "items" in params and not isinstance(params["items"], list):
            errors.append("items must resolve to an array")
        for key in ("max_collect_items", "max_collect_bytes"):
            if key in params and (type(params[key]) is not int or params[key] <= 0):
                errors.append(f"{key} must resolve to a positive integer")
        return errors

    async def execute(self, context: StepContext, params: dict[str, Any]) -> StepResult:
        errors = self.validate_resolved_params(params)
        if errors:
            return StepResult(success=False, message="; ".join(errors))
        items = snapshot_json(params["items"])
        return StepResult(
            success=True,
            message=f"Foreach: {len(params['items'])} items",
            control={
                "type": "foreach",
                "items": items,
                "as": params.get("as", "item"),
                "index_as": params.get("index_as", "index"),
                "steps": params["steps"],
                **({"collect": params["collect"]} if "collect" in params else {}),
                "max_collect_items": params.get("max_collect_items", 1000),
                "max_collect_bytes": params.get("max_collect_bytes", 1048576),
            },
        )
