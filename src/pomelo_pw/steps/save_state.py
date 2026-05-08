"""Save state step."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pomelo_pw.steps.base import BaseStep, StepContext, StepResult, StepSpec, register_step


@register_step
class SaveStateStep(BaseStep):
    """Save browser state (cookies, localStorage, sessionStorage)."""

    spec = StepSpec(
        name="save-state",
        description="Save browser state to a file for later reuse",
        required_params=["file"],
        optional_params={},
        aliases=["save-storage", "save-session"],
    )

    async def execute(self, context: StepContext, params: dict[str, Any]) -> StepResult:
        """Execute save-state step."""
        file_path_str = params["file"]
        
        # Resolve file path relative to output directory
        if not file_path_str.startswith("/") and not file_path_str.startswith("\\"):
            file_path = context.output_dir / file_path_str
        else:
            file_path = Path(file_path_str)
        
        # Ensure parent directory exists
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save storage state
        storage_state = await context.page.context.storage_state(path=str(file_path))
        
        return StepResult(
            success=True,
            message=f"Browser state saved to: {file_path}",
            data={"file": str(file_path), "cookies_count": len(storage_state.get("cookies", []))},
        )
