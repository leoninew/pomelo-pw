# Pomelo PW Skill

Run browser automation flows using Pomelo PW.

## Usage

This skill allows you to execute UI automation flows defined in YAML files.

## Commands

- `pomelo-pw run <flow-file>` - Execute a flow
- `pomelo-pw run <flow-file> -v` - Execute with verbose output
- `pomelo-pw run <flow-file> --var key=value` - Override variables
- `pomelo-pw validate <flow-file>` - Validate flow syntax
- `pomelo-pw steps` - List available steps
- `pomelo-pw spec <step>` - Show step specification

## Flow File Format

```yaml
name: flow-name
description: Flow description

variables:
  var1: "value1"
  var2: "value2"

steps:
  - type: navigate
    url: "${var1}"

  - type: screenshot
    file: "output.png"
```

## Available Steps

- `navigate` - Navigate to URL
- `screenshot` - Take screenshot
- `click` - Click element
- `fill` - Fill form field
- `type` - Type text character by character
- `press` - Press keyboard key
- `wait` - Wait for conditions or fixed delay
  - Use `selector` with `timeout` to wait for element
  - Use `url` with `timeout` to wait for URL
  - Use `delay` for fixed delay (milliseconds)
- `scroll` - Scroll page
- `hover` - Hover over element
- `select` - Select dropdown option
- `check` / `uncheck` - Toggle checkbox
- `evaluate` - Execute JavaScript
  - Supports function expressions: `() => { ... }`
  - Supports direct code (auto-wrapped): `return document.title`
- `set-viewport` - Set viewport size

## Examples

### Basic Navigation and Screenshot

```yaml
name: capture-homepage
steps:
  - type: navigate
    url: "https://example.com"
  - type: screenshot
    file: "homepage.png"
```

### Form Filling

```yaml
name: login-flow
variables:
  username: "user@example.com"
  password: "secret"

steps:
  - type: navigate
    url: "https://example.com/login"

  - type: fill
    selector: "input[name='email']"
    value: "${username}"

  - type: fill
    selector: "input[name='password']"
    value: "${password}"

  - type: click
    selector: "button[type='submit']"

  - type: wait
    url: "/dashboard"

  - type: screenshot
    file: "logged-in.png"
```

### Scrolling and Interaction

```yaml
name: scroll-and-capture
steps:
  - type: navigate
    url: "https://example.com"

  - type: scroll
    direction: down
    distance: 500

  - type: hover
    selector: ".menu-item"

  - type: screenshot
    file: "scrolled.png"
```

## Tips

- Use `${variable}` syntax for dynamic values
- Screenshots are saved to `output/` directory by default
- Use `-v` flag for detailed execution logs
- Validate flows before running with `validate` command
- Override variables at runtime with `--var` flag
