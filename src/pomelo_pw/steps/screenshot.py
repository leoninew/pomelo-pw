"""Screenshot step."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import click

from pomelo_pw.steps.base import BaseStep, StepContext, StepResult, StepSpec, register_step


@register_step
class ScreenshotStep(BaseStep):
    """Capture screenshot with optional baseline comparison."""

    spec = StepSpec(
        name="screenshot",
        description="Capture a screenshot of the current page with optional baseline comparison",
        required_params=["file"],
        optional_params={
            "full_page": False,
            "selector": None,
            "baseline": None,
            "threshold": 0.1,  # 10% difference allowed
            "diff_output": None,
            "fail_on_diff": False,
        },
        aliases=["capture", "snap"],
    )

    async def execute(self, context: StepContext, params: dict[str, Any]) -> StepResult:
        """Execute screenshot step."""
        file_name = params["file"]
        full_page = params.get("full_page", self.spec.optional_params["full_page"])
        selector = params.get("selector", self.spec.optional_params["selector"])
        baseline = params.get("baseline")
        threshold = params.get("threshold", self.spec.optional_params["threshold"])
        diff_output = params.get("diff_output")
        fail_on_diff = params.get("fail_on_diff", self.spec.optional_params["fail_on_diff"])

        file_path = context.output_dir / file_name
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Take screenshot
        if selector:
            element = await context.page.query_selector(selector)
            if element is None:
                return StepResult(
                    success=False,
                    message=f"Element not found: {selector}",
                )
            await element.screenshot(path=str(file_path))
        else:
            await context.page.screenshot(path=str(file_path), full_page=full_page)

        context.screenshots.append(str(file_path))
        
        try:
            rel_path = file_path.relative_to(Path.cwd())
        except ValueError:
            rel_path = file_path
        
        # Baseline comparison if specified
        if baseline:
            baseline_path = context.output_dir / baseline if not Path(baseline).is_absolute() else Path(baseline)
            
            if not baseline_path.exists():
                click.echo(f"Screenshot saved: {rel_path}", err=True)
                click.echo(f"  Warning: Baseline not found: {baseline_path}", err=True)
                return StepResult(
                    success=True,
                    message=f"Screenshot saved (baseline not found): {rel_path}",
                    data={"file": str(file_path), "baseline_missing": True},
                )
            
            # Perform comparison
            diff_result = self._compare_images(
                actual_path=file_path,
                baseline_path=baseline_path,
                threshold=threshold,
                diff_output_path=context.output_dir / diff_output if diff_output else None,
            )
            
            diff_percentage = diff_result["diff_percentage"]
            match = diff_result["match"]
            
            click.echo(f"Screenshot saved: {rel_path}")
            click.echo(f"  Baseline comparison: {diff_percentage:.2f}% difference (threshold: {threshold * 100:.1f}%)")
            
            if not match:
                click.echo(f"  ⚠ Screenshots differ by {diff_percentage:.2f}%", err=True)
                if diff_result.get("diff_image"):
                    click.echo(f"  Diff image saved: {diff_result['diff_image']}", err=True)
                
                if fail_on_diff:
                    return StepResult(
                        success=False,
                        message=f"Screenshot differs from baseline by {diff_percentage:.2f}% (threshold: {threshold * 100:.1f}%)",
                        data=diff_result,
                    )
            else:
                click.echo(f"  ✓ Screenshots match within threshold")
            
            return StepResult(
                success=True,
                message=f"Screenshot saved and compared: {diff_percentage:.2f}% difference",
                data=diff_result,
            )
        
        # No baseline comparison
        click.echo(f"Screenshot saved: {rel_path}")
        return StepResult(success=True, message=f"Screenshot saved: {rel_path}")

    def _compare_images(
        self,
        actual_path: Path,
        baseline_path: Path,
        threshold: float,
        diff_output_path: Path | None = None,
    ) -> dict[str, Any]:
        """Compare two images and return difference metrics.
        
        Args:
            actual_path: Path to actual screenshot
            baseline_path: Path to baseline screenshot
            threshold: Allowed difference percentage (0.0 to 1.0)
            diff_output_path: Optional path to save diff image
            
        Returns:
            Dictionary with comparison results
        """
        try:
            from PIL import Image, ImageChops, ImageDraw  # type: ignore
        except ImportError:
            return {
                "match": False,
                "diff_percentage": 100.0,
                "error": "PIL (Pillow) not installed. Install with: pip install pillow",
            }
        
        # Load images
        actual = Image.open(actual_path).convert("RGB")
        baseline = Image.open(baseline_path).convert("RGB")
        
        # Check if dimensions match
        if actual.size != baseline.size:
            return {
                "match": False,
                "diff_percentage": 100.0,
                "error": f"Image dimensions don't match: {actual.size} vs {baseline.size}",
                "actual_size": actual.size,
                "baseline_size": baseline.size,
            }
        
        # Calculate pixel difference
        diff = ImageChops.difference(actual, baseline)
        
        # Calculate difference percentage
        diff_data = diff.getdata()
        total_pixels = len(diff_data)
        different_pixels = sum(1 for pixel in diff_data if sum(pixel) > 0)
        diff_percentage = (different_pixels / total_pixels) * 100
        
        # Check if within threshold
        match = diff_percentage <= (threshold * 100)
        
        result = {
            "match": match,
            "diff_percentage": diff_percentage,
            "threshold_percentage": threshold * 100,
            "different_pixels": different_pixels,
            "total_pixels": total_pixels,
            "actual_file": str(actual_path),
            "baseline_file": str(baseline_path),
        }
        
        # Generate diff image if requested
        if diff_output_path and not match:
            diff_output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create a visual diff image (highlight differences in red)
            diff_visual = Image.new("RGB", actual.size)
            actual_pixels = actual.load()
            baseline_pixels = baseline.load()
            diff_pixels = diff_visual.load()
            
            for y in range(actual.size[1]):
                for x in range(actual.size[0]):
                    if actual_pixels[x, y] != baseline_pixels[x, y]:
                        # Highlight difference in red
                        diff_pixels[x, y] = (255, 0, 0)
                    else:
                        # Keep original pixel (dimmed)
                        r, g, b = actual_pixels[x, y]
                        diff_pixels[x, y] = (r // 2, g // 2, b // 2)
            
            diff_visual.save(diff_output_path)
            result["diff_image"] = str(diff_output_path)
        
        return result
