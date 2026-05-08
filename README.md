# Pomelo PW

Flow-based UI automation tool powered by Playwright. Define your browser automation workflows in declarative YAML files with type-safe step validation and flexible variable substitution.

## Features

- **Declarative YAML flows**: Define UI automation workflows in simple, readable YAML
- **Type-safe steps**: Built-in validation for all step parameters
- **Variable substitution**: Support for `{{ var }}` and `${ var }` syntax with multi-level priority
- **Rich error context**: Automatic screenshot, HTML snapshot, console/network errors on failure
- **Enhanced SPA support**: URL pattern matching, network idle, animation stable, route stable waits
- **Step-level retry**: Automatic retry with configurable delay and error type filtering
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
| `wait` | - | Wait for conditions (selector, URL, network idle, animations, etc.) |
| `scroll` | - | Scroll the page |
| `hover` | `selector` | Hover over an element |
| `select` | `selector`, `value` | Select dropdown option |
| `check` | `selector` | Check a checkbox |
| `uncheck` | `selector` | Uncheck a checkbox |
| `evaluate` | `script` | Execute JavaScript |
| `set-viewport` | - | Set viewport size |
| `save-state` | `file` | Save browser state (cookies, localStorage) |
| `load-state` | `file` | Load browser state from file |

Run `pomelo-pw spec <step>` for detailed parameter information.

### Enhanced Wait Step

The `wait` step supports multiple conditions for SPA applications:

```yaml
# Wait for selector with state
- type: wait
  selector: ".content"
  state: "visible"  # visible, attached, detached, hidden

# Wait for URL to contain substring
- type: wait
  url_contains: "/dashboard"

# Wait for URL pattern (regex)
- type: wait
  url_pattern: "^/user/\\d+$"

# Wait for network idle
- type: wait
  network_idle: true

# Wait for animations to stabilize
- type: wait
  animation_stable: true

# Wait for route to stabilize (URL doesn't change)
- type: wait
  route_stable: true
  route_stable_duration: 500  # ms

# Fixed delay
- type: wait
  delay: 2000  # ms
```

### Step-Level Retry

Any step can be retried automatically on failure:

```yaml
# Retry 3 times with 1 second delay
- type: click
  selector: ".flaky-button"
  retry: 3
  retry_delay: 1000

# Retry only on specific error types
- type: fill
  selector: "input"
  value: "test"
  retry: 2
  retry_on:
    - "timeout"
    - "element_not_found"
```

### Authentication State Reuse

Save and reuse browser state (cookies, localStorage) to avoid repeated logins:

```yaml
# Flow 1: Login and save state
name: login-flow
steps:
  - type: navigate
    url: "https://example.com/login"
  
  - type: fill
    selector: "input[name='username']"
    value: "{{username}}"
  
  - type: fill
    selector: "input[name='password']"
    value: "{{password}}"
  
  - type: click
    selector: "button[type='submit']"
  
  - type: wait
    url_contains: "/dashboard"
  
  # Save authentication state
  - type: save-state
    file: "auth-state.json"

# Flow 2: Reuse saved state (no login needed)
name: use-saved-auth
steps:
  - type: navigate
    url: "https://example.com"
  
  # Load saved authentication
  - type: load-state
    file: "auth-state.json"
  
  # Now you're logged in!
  - type: navigate
    url: "https://example.com/dashboard"
```

**Benefits**:
- Skip login in subsequent flows
- Faster test execution
- Reduce load on authentication servers
- Share authentication across multiple flows

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

Variables use two syntax options:

**Recommended: `{{ }}` syntax** (doesn't conflict with JS/Shell)
```yaml
variables:
  api_token: "abc123"

steps:
  - type: evaluate
    script: "const token = '{{api_token}}'; fetch(`/api?token=${token}`)"
    # {{api_token}} is replaced, ${token} is preserved as JS template string
```

**Legacy: `${ }` syntax** (backward compatible, but avoid in scripts)
```yaml
variables:
  base_url: "https://example.com"

steps:
  - type: navigate
    url: "${base_url}/login"
```

**Important**: If a string contains `{{ }}`, only `{{ }}` will be processed. This prevents conflicts with JavaScript template strings, shell variables, etc.

Variable priority (three levels):

1. CLI arguments (`--var`)
2. Step-level variables
3. Flow-level variables

## Error Handling

When a step fails, Pomelo PW automatically collects rich error context:

- **Error screenshot**: `./flow/error-step-N.png`
- **HTML snapshot**: `./flow/error-step-N.html`
- **Console errors**: Browser console messages (errors and warnings)
- **Network errors**: Failed HTTP requests (4xx, 5xx)
- **Current URL**: Page URL at the time of failure
- **Visible text**: First 500 characters of page text

**Example error output**:
```
[3/5] click FAILED: Element not found: .submit-btn
  Screenshot saved: ./my-flow/error-step-3.png
  HTML snapshot saved: ./my-flow/error-step-3.html
  Console errors: 2
  Network errors: 1
  Current URL: https://example.com/login
```

**JSON output** includes full error context:
```json
{
  "success": false,
  "failed_step": {
    "index": 2,
    "type": "click",
    "error": "Element not found: .submit-btn",
    "context": {
      "url": "https://example.com/login",
      "screenshot": "./my-flow/error-step-3.png",
      "html_snapshot": "./my-flow/error-step-3.html",
      "console_errors": ["[ERROR] Failed to load resource"],
      "network_errors": [{"url": "/api/user", "status": 500}],
      "visible_text": "Login failed. Please try again.",
      "step_index": 2,
      "step_type": "click"
    }
  }
}
```

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