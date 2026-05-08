"""Interactive flow recorder for generating YAML flows."""

import asyncio
from pathlib import Path
from typing import Any

import click
import yaml
from playwright.async_api import Page, async_playwright


class FlowRecorder:
    """Records user interactions and generates YAML flow."""

    def __init__(self, page: Page, flow_name: str) -> None:
        self.page = page
        self.flow_name = flow_name
        self.steps: list[dict[str, Any]] = []
        self.variables: dict[str, str] = {}

    async def inject_recorder_ui(self) -> None:
        """Inject recorder UI overlay into the page."""
        await self.page.add_script_tag(
            content="""
            window.__pomelo_recorder__ = {
                enabled: true,
                recording: [],
                highlightedElement: null,
                
                init() {
                    // Create overlay container
                    const overlay = document.createElement('div');
                    overlay.id = 'pomelo-recorder-overlay';
                    overlay.style.cssText = `
                        position: fixed;
                        top: 10px;
                        right: 10px;
                        background: rgba(220, 38, 38, 0.95);
                        color: white;
                        padding: 15px;
                        border-radius: 8px;
                        font-family: monospace;
                        font-size: 12px;
                        z-index: 999999;
                        min-width: 300px;
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
                    `;
                    overlay.innerHTML = `
                        <div style="margin-bottom: 10px; font-weight: bold; display: flex; align-items: center;">
                            <span style="font-size: 16px; margin-right: 8px;">⏺</span>
                            <span>Recording...</span>
                        </div>
                        <div id="pomelo-recorder-info" style="line-height: 1.6; font-size: 11px; color: #FEE;">
                            Steps: <span id="pomelo-step-count">0</span>
                        </div>
                    `;
                    document.body.appendChild(overlay);
                    
                    // Add event listeners
                    document.addEventListener('click', this.handleClick.bind(this), true);
                    document.addEventListener('input', this.handleInput.bind(this), true);
                    document.addEventListener('keydown', this.handleKeydown.bind(this), true);
                    document.addEventListener('mousemove', this.handleMouseMove.bind(this));
                },
                
                handleMouseMove(e) {
                    if (!this.enabled) return;
                    
                    const element = e.target;
                    if (element.id === 'pomelo-recorder-overlay' || 
                        element.closest('#pomelo-recorder-overlay')) {
                        return;
                    }
                    
                    // Remove previous highlight
                    if (this.highlightedElement) {
                        this.highlightedElement.style.outline = '';
                    }
                    
                    // Highlight current element
                    element.style.outline = '2px solid #DC2626';
                    this.highlightedElement = element;
                },
                
                handleClick(e) {
                    if (!this.enabled) return;
                    
                    const element = e.target;
                    if (element.id === 'pomelo-recorder-overlay' || 
                        element.closest('#pomelo-recorder-overlay')) {
                        return;
                    }
                    
                    e.preventDefault();
                    e.stopPropagation();
                    
                    const selector = this.getBestSelector(element);
                    const step = {
                        type: 'click',
                        selector: selector,
                        timestamp: Date.now()
                    };
                    
                    this.recording.push(step);
                    this.updateStepCount();
                },
                
                handleInput(e) {
                    if (!this.enabled) return;
                    
                    const element = e.target;
                    if (element.id === 'pomelo-recorder-overlay' || 
                        element.closest('#pomelo-recorder-overlay')) {
                        return;
                    }
                    
                    const selector = this.getBestSelector(element);
                    const value = element.value;
                    
                    // Check if last step was input on same element
                    const lastStep = this.recording[this.recording.length - 1];
                    if (lastStep && lastStep.type === 'fill' && lastStep.selector === selector) {
                        // Update existing step
                        lastStep.value = value;
                        lastStep.timestamp = Date.now();
                    } else {
                        // Add new step
                        const step = {
                            type: 'fill',
                            selector: selector,
                            value: value,
                            timestamp: Date.now()
                        };
                        this.recording.push(step);
                        this.updateStepCount();
                    }
                },
                
                handleKeydown(e) {
                    if (!this.enabled) return;
                    
                    const element = e.target;
                    if (element.id === 'pomelo-recorder-overlay' || 
                        element.closest('#pomelo-recorder-overlay')) {
                        return;
                    }
                    
                    // Record Enter key press
                    if (e.key === 'Enter') {
                        const selector = this.getBestSelector(element);
                        const step = {
                            type: 'press',
                            selector: selector,
                            key: 'Enter',
                            timestamp: Date.now()
                        };
                        this.recording.push(step);
                        this.updateStepCount();
                    }
                },
                
                getBestSelector(element) {
                    // Priority: data-test > id > role > text > class
                    
                    // Data test attribute
                    for (const attr of element.attributes) {
                        if (attr.name.startsWith('data-test')) {
                            return `[${attr.name}="${attr.value}"]`;
                        }
                    }
                    
                    // ID
                    if (element.id) {
                        return `#${element.id}`;
                    }
                    
                    // Role with name
                    const role = element.getAttribute('role') || this.getImplicitRole(element);
                    if (role) {
                        const name = element.getAttribute('aria-label') || 
                                   element.getAttribute('title') || 
                                   element.textContent?.trim();
                        if (name && name.length < 50 && name.length > 0) {
                            return `role=${role}[name="${name}"]`;
                        }
                    }
                    
                    // Text content
                    const text = element.textContent?.trim();
                    if (text && text.length < 50 && text.length > 0 && 
                        element.children.length === 0) {
                        return `text=${text}`;
                    }
                    
                    // Class selector
                    if (element.className && typeof element.className === 'string') {
                        const classes = element.className.trim().split(/\\s+/).filter(c => c);
                        if (classes.length > 0) {
                            return `.${classes[0]}`;
                        }
                    }
                    
                    // Fallback to tag name
                    return element.tagName.toLowerCase();
                },
                
                getImplicitRole(element) {
                    const tag = element.tagName.toLowerCase();
                    const roleMap = {
                        'button': 'button',
                        'a': 'link',
                        'input': element.type === 'checkbox' ? 'checkbox' : 
                                element.type === 'radio' ? 'radio' : 'textbox',
                        'textarea': 'textbox',
                        'select': 'combobox',
                    };
                    return roleMap[tag] || null;
                },
                
                updateStepCount() {
                    const countEl = document.getElementById('pomelo-step-count');
                    if (countEl) {
                        countEl.textContent = this.recording.length;
                    }
                }
            };
            
            window.__pomelo_recorder__.init();
            """
        )

    async def get_recorded_steps(self) -> list[dict[str, Any]]:
        """Get all recorded steps."""
        result = await self.page.evaluate("window.__pomelo_recorder__.recording")
        return result or []

    async def wait_for_recording(self) -> None:
        """Wait for user to finish recording."""
        click.echo("\nRecording... Press Ctrl+C when done.\n")
        
        try:
            while True:
                await asyncio.sleep(1)
                steps = await self.get_recorded_steps()
                if steps:
                    # Show progress
                    click.echo(f"\rSteps recorded: {len(steps)}", nl=False)
        except KeyboardInterrupt:
            click.echo("\n\n⏹ Recording stopped")

    def generate_flow(self, steps: list[dict[str, Any]], start_url: str) -> dict[str, Any]:
        """Generate YAML flow from recorded steps."""
        # Clean up steps (remove timestamps, deduplicate)
        cleaned_steps = []
        for step in steps:
            clean_step = {k: v for k, v in step.items() if k != "timestamp"}
            cleaned_steps.append(clean_step)

        # Add navigate step at the beginning
        flow_steps = [{"type": "navigate", "url": start_url}]
        flow_steps.extend(cleaned_steps)

        flow = {
            "name": self.flow_name,
            "description": f"Recorded flow from {start_url}",
            "steps": flow_steps,
        }

        return flow

    def save_flow(self, flow: dict[str, Any], output_path: Path) -> None:
        """Save flow to YAML file."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            yaml.dump(flow, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        click.echo(f"\n✓ Flow saved to: {output_path}")


async def record_flow(url: str, output: str, headless: bool = False) -> None:
    """Launch interactive flow recorder."""
    flow_name = Path(output).stem
    
    click.echo(f"⏺ Recording flow: {flow_name}")
    click.echo(f"   Starting at: {url}")
    click.echo("━" * 60)
    click.echo("Instructions:")
    click.echo("  • Click elements to record click actions")
    click.echo("  • Type in inputs to record fill actions")
    click.echo("  • Press Enter to record key press")
    click.echo("  • Press Ctrl+C to stop and save")
    click.echo("━" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded")
            
            recorder = FlowRecorder(page, flow_name)
            await recorder.inject_recorder_ui()

            click.echo(f"\n✓ Recorder ready at: {url}")

            # Wait for recording
            await recorder.wait_for_recording()

            # Get recorded steps
            steps = await recorder.get_recorded_steps()
            
            if not steps:
                click.echo("\n⚠ No steps recorded")
                return

            # Generate and save flow
            flow = recorder.generate_flow(steps, url)
            recorder.save_flow(flow, Path(output))

            # Display summary
            click.echo("\n" + "=" * 60)
            click.echo("Flow Summary:")
            click.echo("=" * 60)
            click.echo(f"Steps: {len(steps)}")
            click.echo(f"Output: {output}")
            click.echo("=" * 60)

        except KeyboardInterrupt:
            click.echo("\n\n⏹ Recording cancelled")
        finally:
            await browser.close()
