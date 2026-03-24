"""Step base classes and registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from playwright.async_api import Page


@dataclass
class StepSpec:
    """步骤规范定义."""

    name: str
    description: str = ""
    required_params: list[str] = field(default_factory=list)
    optional_params: dict[str, Any] = field(default_factory=dict)
    aliases: list[str] = field(default_factory=list)


@dataclass
class StepContext:
    """步骤执行上下文."""

    page: Page
    variables: dict[str, Any]
    output_dir: Path
    screenshots: list[str]


@dataclass
class StepResult:
    """步骤执行结果."""

    success: bool
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)


# Step registry
_STEP_REGISTRY: dict[str, type[BaseStep]] = {}


def register_step(step_class: type[BaseStep]) -> type[BaseStep]:
    """装饰器：注册步骤类."""
    step_type = step_class.spec.name
    _STEP_REGISTRY[step_type] = step_class

    for alias in step_class.spec.aliases:
        _STEP_REGISTRY[alias] = step_class

    return step_class


def get_step(step_type: str) -> type[BaseStep] | None:
    """获取步骤类."""
    return _STEP_REGISTRY.get(step_type)


def list_steps() -> list[str]:
    """列出所有注册的步骤名称（不含别名）."""
    return [cls.spec.name for cls in set(_STEP_REGISTRY.values())]


class BaseStep(ABC):
    """步骤基类."""

    spec: ClassVar[StepSpec]

    @classmethod
    def validate_params(cls, params: dict[str, Any]) -> list[str]:
        """校验参数，返回错误列表."""
        errors = []

        for param in cls.spec.required_params:
            if param not in params:
                errors.append(f"Missing required parameter: {param}")

        all_params = set(cls.spec.required_params) | set(cls.spec.optional_params.keys())
        all_params.add("type")
        all_params.add("variables")

        for param in params:
            if param not in all_params:
                errors.append(f"Unknown parameter: {param}")

        return errors

    @classmethod
    def get_defaults(cls) -> dict[str, Any]:
        """获取可选参数默认值."""
        return cls.spec.optional_params.copy()

    @abstractmethod
    async def execute(self, context: StepContext, params: dict[str, Any]) -> StepResult:
        """执行步骤."""
        pass
