# Pomelo PW

Flow-based UI automation tool powered by Playwright. Define your browser automation workflows in declarative YAML files with type-safe step validation and flexible variable substitution.

## Features

- **Declarative YAML flows**: Define UI automation workflows in simple, readable YAML
- **Type-safe steps**: Built-in validation for all step parameters
- **Variable substitution**: Support for `${var}` syntax with multi-level priority
- **Extensible architecture**: Easy to add custom steps
- **Development mode**: Automatically uses system Chrome when running from source (no slow downloads)
- **Rich step library**: Navigate, click, fill, type, screenshot, scroll, and more

## Installation

```bash
# Install Playwright browsers (one-time setup)
uvx pomelo-pw install

# Or for development
uv sync
uv run pomelo-pw install
```

## Quick Start

Create a flow file `my-flow.yaml`:

```yaml
name: example-flow
description: Navigate and capture screenshots

variables:
  base_url: "https://example.com"

steps:
  - type: navigate
    url: "${base_url}"

  - type: screenshot
    file: "homepage.png"

  - type: scroll
    direction: down
    distance: 500

  - type: screenshot
    file: "scrolled.png"
```

Run the flow:

```bash
uvx pomelo-pw run my-flow.yaml
```

## Usage

### Basic Commands

```bash
# Run a flow (screenshots saved to ./flow/ directory, named after the flow file)
pomelo-pw run flow.yaml

# Run with verbose output
pomelo-pw run flow.yaml -v

# Specify custom output directory
pomelo-pw run flow.yaml -o /custom/path

# Note: Output directory name is derived from flow filename, regardless of path
# Example: flows/my-test.yaml → ./my-test/

# Override variables
pomelo-pw run flow.yaml --var base_url=https://prod.example.com

# Output as JSON
pomelo-pw run flow.yaml --json

# Validate a flow without running
pomelo-pw validate flow.yaml

# List all available steps
pomelo-pw steps

# Show step specification
pomelo-pw spec navigate
```

### Available Steps

| Step | Required Params | Description |
|------|----------------|-------------|
| `navigate` | `url` | Navigate to a URL |
| `screenshot` | `file` | Take a screenshot |
| `click` | `selector` | Click an element |
| `fill` | `selector`, `value` | Fill a form field |
| `type` | `selector`, `value` | Type text character by character |
| `press` | `key` | Press a keyboard key |
| `wait` | - | Wait for conditions (selector, url, timeout) |
| `scroll` | - | Scroll the page |
| `hover` | `selector` | Hover over an element |
| `select` | `selector`, `value` | Select dropdown option |
| `check` | `selector` | Check a checkbox |
| `uncheck` | `selector` | Uncheck a checkbox |
| `evaluate` | `script` | Execute JavaScript |
| `set-viewport` | - | Set viewport size |

Run `pomelo-pw spec <step>` for detailed parameter information.

## Flow File Format

```yaml
name: flow-name
description: Flow description

variables:
  var1: "value1"
  var2: "value2"

steps:
  - type: step-type
    param1: "${var1}"
    param2: "literal value"
```

### Variable Substitution

Variables use `${var}` syntax with three-level priority:

1. CLI arguments (`--var`)
2. Step-level variables
3. Flow-level variables

## Development

```bash
# Install dependencies
make install

# Run tests
make test

# Run code quality checks (format + lint + type check)
make check

# Run example flow
make example
```

### Development Mode

When running from source, Pomelo PW automatically detects development mode and uses your system Chrome instead of downloading Playwright's Chromium. This significantly speeds up the setup process.

## Project Structure

```
pomelo-pw/
├── src/pomelo_pw/
│   ├── cli.py              # CLI entry point
│   ├── executor.py         # Flow execution engine
│   ├── substitution.py     # Variable substitution
│   ├── config/             # Configuration management
│   └── steps/              # Step implementations
├── tests/                  # Unit tests
├── flows/                  # Example flows
└── docs/                   # Documentation
```

## License

MIT