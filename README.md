# Pomelo PW

[中文](README.zh-CN.md) | English

Flow-based UI automation tool powered by Playwright. Define your browser automation workflows in declarative YAML files with type-safe step validation and flexible variable substitution.

## Features

- **Declarative YAML flows**: Define UI automation workflows in simple, readable YAML
- **Type-safe steps**: Built-in validation for all step parameters
- **Variable substitution**: Support for `{{ var }}` and `${ var }` syntax with multi-level priority
- **Rich error context**: Automatic screenshot, HTML snapshot, console/network errors on failure
- **Enhanced SPA support**: URL pattern matching, network idle, animation stable, route stable waits
- **Step-level retry**: Automatic retry with configurable delay and error type filtering
- **Visual regression testing**: Screenshot baseline comparison with diff highlighting
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

# Optional: Install visual regression testing support
pip install pomelo-pw[visual]
# or with uv
uv pip install pillow
```

## Quick Start

### Interactive Tools

```bash
# Explore a page interactively to discover selectors
pomelo-pw explore https://example.com

# Record user interactions to generate a flow
pomelo-pw record https://example.com output.yaml
```

### Create and Run Flows

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

### Interactive Tools

#### Page Explorer

Discover element selectors interactively:

```bash
# Launch explorer
pomelo-pw explore https://example.com

# Run in headless mode
pomelo-pw explore https://example.com --headless
```

**Features**:
- Hover over elements to see available selectors
- Click an element to display all selector options in terminal
- Selector priority: data-test > id > role > text > class > css > xpath
- Visual overlay shows selectors in real-time

**Use cases**:
- Find the best selector for an element
- Understand page structure
- Debug selector issues
- Learn Playwright selector syntax

#### Flow Recorder

Record user interactions to generate YAML flows:

```bash
# Record a flow
pomelo-pw record https://example.com output.yaml

# Run in headless mode
pomelo-pw record https://example.com output.yaml --headless
```

**Recorded actions**:
- Click: Automatically records click events
- Fill: Records text input in form fields
- Press: Records Enter key presses

**Features**:
- Real-time step counter
- Automatic selector generation (best selector chosen)
- Generates clean YAML flow file
- Press Ctrl+C to stop and save

**Example output**:
```yaml
name: output
description: Recorded flow from https://example.com
steps:
  - type: navigate
    url: https://example.com
  - type: click
    selector: role=button[name="Get started"]
  - type: fill
    selector: "#email"
    value: user@example.com
  - type: press
    selector: "#email"
    key: Enter
```

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

### Visual Regression Testing

Compare screenshots against baselines to detect visual changes:

```yaml
# First run: create baseline
- type: screenshot
  file: "homepage.png"

# Subsequent runs: compare with baseline
- type: screenshot
  file: "homepage-current.png"
  baseline: "homepage.png"
  threshold: 0.05  # Allow 5% difference
  diff_output: "homepage-diff.png"
  fail_on_diff: false  # Don't fail, just report

# Strict comparison (fail on difference)
- type: screenshot
  file: "critical-page.png"
  baseline: "critical-baseline.png"
  threshold: 0.01  # Only 1% difference allowed
  diff_output: "critical-diff.png"
  fail_on_diff: true  # Fail if difference exceeds threshold
```

**Parameters**:
- `baseline`: Path to baseline image (relative to output dir)
- `threshold`: Allowed difference as decimal (0.05 = 5%)
- `diff_output`: Path to save diff image (highlights differences in red)
- `fail_on_diff`: Whether to fail the step if difference exceeds threshold

**Requirements**: Install Pillow for visual comparison
```bash
pip install pomelo-pw[visual]
# or
uv pip install pillow
```

**Use cases**:
- Detect unintended UI changes
- Visual consistency checks across environments
- Style regression testing
- Component visual testing

### Conditional Execution

Execute steps based on conditions:

```yaml
# Check if element exists
- type: if
  condition: "element_exists: .login-button"
  then:
    - type: click
      selector: ".login-button"
  else:
    - type: screenshot
      file: "already-logged-in.png"

# Check if element is visible
- type: if
  condition: "element_visible: .error-message"
  then:
    - type: screenshot
      file: "error-state.png"

# Check URL
- type: if
  condition: "url_contains: /dashboard"
  then:
    - type: screenshot
      file: "dashboard.png"

# JavaScript expression
- type: if
  condition: "document.querySelectorAll('.item').length > 5"
  then:
    - type: screenshot
      file: "many-items.png"
```

**Condition types**:
- `element_exists: selector` - Element exists in DOM
- `element_visible: selector` - Element is visible
- `element_hidden: selector` - Element is hidden or doesn't exist
- `url_contains: text` - URL contains text
- `url_matches: pattern` - URL matches regex pattern
- `text_contains: text` - Page content contains text
- JavaScript expression - Any valid JS that returns boolean

**Use cases**:
- Handle different page states
- Skip steps based on conditions
- Implement branching logic
- Adapt to dynamic content

### Loop Execution

Repeat steps multiple times:

```yaml
# Fixed iteration count
- type: loop
  times: 5
  steps:
    - type: scroll
      direction: down
      distance: 500
    - type: wait
      duration: 300

# Conditional loop (while)
- type: loop
  while: "element_visible: .load-more-button"
  max_iterations: 10
  steps:
    - type: click
      selector: ".load-more-button"
    - type: wait
      network_idle: true

# Nested loops
- type: loop
  times: 3
  steps:
    - type: loop
      times: 2
      steps:
        - type: screenshot
          file: "nested-{{outer}}-{{inner}}.png"
```

**Parameters**:
- `times`: Number of iterations (fixed count)
- `while`: Condition to check before each iteration
- `max_iterations`: Safety limit for while loops (default: 100)
- `steps`: Steps to execute in each iteration

**Use cases**:
- Scroll through paginated content
- Click "Load More" buttons repeatedly
- Test repeated interactions
- Generate multiple screenshots

### Combined Patterns

Combine conditionals and loops for complex workflows:

```yaml
# Loop with conditional inside
- type: loop
  times: 5
  steps:
    - type: if
      condition: "element_exists: .next-page"
      then:
        - type: click
          selector: ".next-page"
        - type: wait
          duration: 1000
      else:
        - type: screenshot
          file: "last-page.png"

# Conditional with loop inside
- type: if
  condition: "element_visible: .gallery"
  then:
    - type: loop
      times: 10
      steps:
        - type: scroll
          direction: down
          distance: 300
```

### Data-Driven Testing

Run the same flow with multiple data sets:

```yaml
name: login-test
variables:
  base_url: "https://example.com"

data:
  - _label: "user-alice"
    username: "alice@example.com"
    password: "pass1"
  - _label: "user-bob"
    username: "bob@example.com"
    password: "pass2"

steps:
  - type: navigate
    url: "{{base_url}}/login"
  - type: fill
    selector: "#email"
    value: "{{username}}"
  - type: fill
    selector: "#password"
    value: "{{password}}"
  - type: screenshot
    file: "login-{{username}}.png"
```

**How it works**:
- Each row in `data` runs all steps independently
- Row variables override `variables` on conflict
- Each row outputs to its own subdirectory: `_label` value or `row-N`
- `on_error: continue` keeps running remaining rows on failure (default: `stop`)

**Result structure**:
```json
{
  "success": true,
  "data_driven": true,
  "rows_total": 2,
  "rows_passed": 2,
  "rows_failed": 0,
  "row_results": [
    {"row": "user-alice", "success": true, ...},
    {"row": "user-bob",   "success": true, ...}
  ]
}
```

**Use cases**:
- Test multiple user accounts
- Verify behavior across different locales or environments
- Run the same visual check on multiple pages
- Parameterized regression testing

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