"""Steps module.

This module provides step classes for flow execution.
All steps are automatically registered via the @register_step decorator.
"""

# Import all step modules to trigger registration
from pomelo_pw.steps import (
    check,
    click,
    evaluate,
    fill,
    hover,
    navigate,
    press,
    screenshot,
    scroll,
    select,
    set_viewport,
    type,
    uncheck,
    wait,
)
from pomelo_pw.steps.base import (
    BaseStep,
    StepContext,
    StepResult,
    StepSpec,
    get_step,
    list_steps,
    register_step,
)

__all__ = [
    "BaseStep",
    "StepContext",
    "StepResult",
    "StepSpec",
    "get_step",
    "list_steps",
    "register_step",
    "check",
    "click",
    "evaluate",
    "fill",
    "hover",
    "navigate",
    "press",
    "scroll",
    "screenshot",
    "select",
    "set_viewport",
    "type",
    "uncheck",
    "wait",
]
