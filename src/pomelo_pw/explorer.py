"""Interactive page explorer for discovering selectors."""

import asyncio
import json
from pathlib import Path
from typing import Any

import click
from playwright.async_api import Page, async_playwright


class PageExplorer:
    """Interactive page explorer for discovering element selectors."""

    def __init__(self, page: Page) -> None:
        self.page = page

    async def inject_explorer_ui(self) -> None:
        """Inject explorer UI overlay into the page."""
        await self.page.add_script_tag(
            content="""
            window.__pomelo_explorer__ = {
                enabled: true,
                highlightedElement: null,
                
                init() {
                    // Create overlay container
                    const overlay = document.createElement('div');
                    overlay.id = 'pomelo-explorer-overlay';
                    overlay.style.cssText = `
                        position: fixed;
                        top: 10px;
                        right: 10px;
                        background: rgba(0, 0, 0, 0.9);
                        color: white;
                        padding: 15px;
                        border-radius: 8px;
                        font-family: monospace;
                        font-size: 12px;
                        z-index: 999999;
                        max-width: 400px;
                        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
                    `;
                    overlay.innerHTML = `
                        <div style="margin-bottom: 10px; font-weight: bold; color: #4CAF50;">
                            🔍 Pomelo Explorer
                        </div>
                        <div id="pomelo-selector-info" style="line-height: 1.6;">
                            Hover over elements to see selectors
                        </div>
                    `;
                    document.body.appendChild(overlay);
                    
                    // Add hover listener
                    document.addEventListener('mousemove', this.handleMouseMove.bind(this));
                    document.addEventListener('click', this.handleClick.bind(this), true);
                },
                
                handleMouseMove(e) {
                    if (!this.enabled) return;
                    
                    const element = e.target;
                    if (element.id === 'pomelo-explorer-overlay' || 
                        element.closest('#pomelo-explorer-overlay')) {
                        return;
                    }
                    
                    // Remove previous highlight
                    if (this.highlightedElement) {
                        this.highlightedElement.style.outline = '';
                    }
                    
                    // Highlight current element
                    element.style.outline = '2px solid #4CAF50';
                    this.highlightedElement = element;
                    
                    // Generate selectors
                    const selectors = this.generateSelectors(element);
                    this.displaySelectors(selectors);
                },
                
                handleClick(e) {
                    if (!this.enabled) return;
                    
                    const element = e.target;
                    if (element.id === 'pomelo-explorer-overlay' || 
                        element.closest('#pomelo-explorer-overlay')) {
                        return;
                    }
                    
                    e.preventDefault();
                    e.stopPropagation();
                    
                    const selectors = this.generateSelectors(element);
                    window.__pomelo_selected_selectors__ = selectors;
                },
                
                generateSelectors(element) {
                    const selectors = {};
                    
                    // ID selector
                    if (element.id) {
                        selectors.id = `#${element.id}`;
                    }
                    
                    // Class selector
                    if (element.className && typeof element.className === 'string') {
                        const classes = element.className.trim().split(/\\s+/).filter(c => c);
                        if (classes.length > 0) {
                            selectors.class = `.${classes.join('.')}`;
                        }
                    }
                    
                    // Text selector
                    const text = element.textContent?.trim();
                    if (text && text.length < 50 && text.length > 0) {
                        selectors.text = `text=${text}`;
                    }
                    
                    // Role selector
                    const role = element.getAttribute('role') || this.getImplicitRole(element);
                    if (role) {
                        const name = element.getAttribute('aria-label') || 
                                   element.getAttribute('title') || 
                                   text;
                        if (name && name.length < 50) {
                            selectors.role = `role=${role}[name="${name}"]`;
                        } else {
                            selectors.role = `role=${role}`;
                        }
                    }
                    
                    // Data attribute selector
                    for (const attr of element.attributes) {
                        if (attr.name.startsWith('data-test')) {
                            selectors.data_test = `[${attr.name}="${attr.value}"]`;
                            break;
                        }
                    }
                    
                    // CSS selector (tag + classes)
                    const tag = element.tagName.toLowerCase();
                    if (selectors.class) {
                        selectors.css = `${tag}${selectors.class}`;
                    } else {
                        selectors.css = tag;
                    }
                    
                    // XPath
                    selectors.xpath = this.getXPath(element);
                    
                    return selectors;
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
                        'h1': 'heading',
                        'h2': 'heading',
                        'h3': 'heading',
                        'h4': 'heading',
                        'h5': 'heading',
                        'h6': 'heading',
                        'img': 'img',
                        'nav': 'navigation',
                        'main': 'main',
                        'header': 'banner',
                        'footer': 'contentinfo',
                    };
                    return roleMap[tag] || null;
                },
                
                getXPath(element) {
                    if (element.id) {
                        return `//*[@id="${element.id}"]`;
                    }
                    
                    const parts = [];
                    while (element && element.nodeType === Node.ELEMENT_NODE) {
                        let index = 0;
                        let sibling = element.previousSibling;
                        while (sibling) {
                            if (sibling.nodeType === Node.ELEMENT_NODE && 
                                sibling.nodeName === element.nodeName) {
                                index++;
                            }
                            sibling = sibling.previousSibling;
                        }
                        
                        const tagName = element.nodeName.toLowerCase();
                        const part = index > 0 ? `${tagName}[${index + 1}]` : tagName;
                        parts.unshift(part);
                        
                        element = element.parentNode;
                    }
                    
                    return '/' + parts.join('/');
                },
                
                displaySelectors(selectors) {
                    const info = document.getElementById('pomelo-selector-info');
                    if (!info) return;
                    
                    const priority = ['data_test', 'id', 'role', 'text', 'class', 'css', 'xpath'];
                    const lines = [];
                    
                    for (const key of priority) {
                        if (selectors[key]) {
                            const label = key.replace('_', '-').toUpperCase();
                            const value = selectors[key];
                            const truncated = value.length > 60 ? value.substring(0, 57) + '...' : value;
                            lines.push(`<div style="margin: 5px 0;">
                                <span style="color: #FFC107;">${label}:</span><br/>
                                <span style="color: #E0E0E0; word-break: break-all;">${this.escapeHtml(truncated)}</span>
                            </div>`);
                        }
                    }
                    
                    info.innerHTML = lines.join('') || 'No selectors found';
                },
                
                escapeHtml(text) {
                    const div = document.createElement('div');
                    div.textContent = text;
                    return div.innerHTML;
                }
            };
            
            window.__pomelo_explorer__.init();
            """
        )

    async def get_selected_selectors(self) -> dict[str, str] | None:
        """Get selectors for the clicked element."""
        result = await self.page.evaluate("window.__pomelo_selected_selectors__")
        if result:
            # Clear the selection
            await self.page.evaluate("window.__pomelo_selected_selectors__ = null")
            return dict(result)
        return None

    async def wait_for_selection(self) -> dict[str, str]:
        """Wait for user to click an element."""
        while True:
            selectors = await self.get_selected_selectors()
            if selectors:
                return selectors
            await asyncio.sleep(0.1)


async def explore_page(url: str, headless: bool = False) -> None:
    """Launch interactive page explorer."""
    click.echo(f"🔍 Launching explorer for: {url}")
    click.echo("━" * 60)
    click.echo("Instructions:")
    click.echo("  • Hover over elements to see available selectors")
    click.echo("  • Click an element to copy its selectors")
    click.echo("  • Press Ctrl+C to exit")
    click.echo("━" * 60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            await page.goto(url, wait_until="domcontentloaded")
            
            explorer = PageExplorer(page)
            await explorer.inject_explorer_ui()

            click.echo(f"\n✓ Explorer ready at: {url}\n")

            # Keep the browser open and wait for selections
            while True:
                selectors = await explorer.wait_for_selection()
                
                click.echo("\n" + "=" * 60)
                click.echo("Selected Element Selectors:")
                click.echo("=" * 60)
                
                # Display in priority order
                priority = ["data_test", "id", "role", "text", "class", "css", "xpath"]
                for key in priority:
                    if key in selectors:
                        label = key.replace("_", "-").upper()
                        value = selectors[key]
                        click.echo(f"{label:12} {value}")
                
                click.echo("=" * 60 + "\n")

        except KeyboardInterrupt:
            click.echo("\n\n👋 Explorer closed")
        finally:
            await browser.close()
