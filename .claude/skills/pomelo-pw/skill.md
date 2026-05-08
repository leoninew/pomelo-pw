# Pomelo PW Skill

Run browser automation flows using Pomelo PW.

## Commands

### Interactive Tools

- `pomelo-pw explore <url>` - Launch interactive page explorer
  - Hover over elements to see selectors in real-time
  - Click to display all selector options in terminal
  - Selector priority: data-test > id > role > text > class > css > xpath

- `pomelo-pw record <url> <output.yaml>` - Record interactions to generate flow
  - Click elements → records click actions
  - Type in inputs → records fill actions
  - Press Enter → records key press
  - Ctrl+C to stop and save

### Flow Execution

- `pomelo-pw run <flow-file>` - Execute a flow
- `pomelo-pw run <flow-file> -v` - Verbose output
- `pomelo-pw run <flow-file> -o <dir>` - Custom output directory
- `pomelo-pw run <flow-file> --var key=value` - Override variables
- `pomelo-pw run <flow-file> --headless` - Headless mode
- `pomelo-pw validate <flow-file>` - Validate without running
- `pomelo-pw steps` - List all available steps
- `pomelo-pw spec <step>` - Show step parameters

## Flow File Format

```yaml
name: flow-name
description: Optional description

variables:
  base_url: "https://example.com"
  username: "admin"

steps:
  - type: navigate
    url: "{{base_url}}/login"
```

### Variable Syntax

Use `{{ }}` — doesn't conflict with JS/Shell template literals:
```yaml
- type: evaluate
  script: "const token = '{{api_token}}'; fetch(`/api?token=${token}`)"
```

Legacy `${ }` is still supported for backward compatibility.

### Output Directory

Screenshots save to `./<flow-name>/` by default (derived from filename).
- `flows/my-test.yaml` → `./my-test/`
- Override with `-o /custom/path`

## Available Steps

| Step | Key Params | Description |
|------|-----------|-------------|
| `navigate` | `url` | Navigate to URL |
| `screenshot` | `file` | Take screenshot |
| `click` | `selector` | Click element |
| `fill` | `selector`, `value` | Fill form field (clears first) |
| `type` | `selector`, `value` | Type character by character |
| `press` | `key` | Press keyboard key |
| `wait` | - | Wait for conditions |
| `scroll` | `direction`, `distance` | Scroll page |
| `hover` | `selector` | Hover over element |
| `select` | `selector`, `value` | Select dropdown option |
| `check` / `uncheck` | `selector` | Toggle checkbox |
| `evaluate` | `script` | Execute JavaScript |
| `set-viewport` | `width`, `height` | Set viewport size |
| `save-state` | `file` | Save cookies + localStorage |
| `load-state` | `file` | Restore saved auth state |
| `if` | `condition`, `then` | Conditional execution |
| `loop` | `steps`, `times`/`while` | Loop execution |

## Step Details

### wait — Enhanced SPA Support

```yaml
# Wait for element
- type: wait
  selector: ".dashboard"
  timeout: 5000

# Wait for URL
- type: wait
  url_contains: "/dashboard"

- type: wait
  url_pattern: "^/user/\\d+$"

# Wait for network/animation
- type: wait
  network_idle: true

- type: wait
  animation_stable: true

- type: wait
  route_stable: true
  duration: 500

# Fixed delay
- type: wait
  delay: 1000
```

### screenshot — Baseline Comparison

```yaml
# Take screenshot
- type: screenshot
  file: "page.png"
  full_page: true

# Compare with baseline
- type: screenshot
  file: "page-current.png"
  baseline: "page.png"
  threshold: 0.05        # 5% difference allowed
  diff_output: "diff.png"
  fail_on_diff: true
```

Requires Pillow: `pip install pomelo-pw[visual]`

### save-state / load-state — Auth Reuse

```yaml
# Save after login
- type: save-state
  file: "auth.json"

# Load in next flow (skip login)
- type: load-state
  file: "auth.json"
```

### if — Conditional Execution

```yaml
- type: if
  condition: "element_exists: .cookie-banner"
  then:
    - type: click
      selector: ".accept-cookies"
  else:
    - type: screenshot
      file: "no-banner.png"
```

Condition types:
- `element_exists: selector`
- `element_visible: selector`
- `element_hidden: selector`
- `url_contains: text`
- `url_matches: pattern`
- `text_contains: text`
- JavaScript expression: `document.title.length > 0`

### loop — Repeat Steps

```yaml
# Fixed count
- type: loop
  times: 5
  steps:
    - type: scroll
      direction: down
      distance: 300

# While condition
- type: loop
  while: "element_visible: .load-more"
  max_iterations: 20
  steps:
    - type: click
      selector: ".load-more"
    - type: wait
      network_idle: true
```

### Step-Level Retry

Any step supports retry parameters:
```yaml
- type: click
  selector: ".flaky-button"
  retry: 3
  retry_delay: 1000
  retry_on:
    - "timeout"
    - "element_not_found"
```

## Data-Driven Testing

Run the same flow with multiple data sets:

```yaml
name: multi-user-test
variables:
  base_url: "https://example.com"

data:
  - _label: "user-alice"
    username: "alice@example.com"
    password: "pass1"
  - _label: "user-bob"
    username: "bob@example.com"
    password: "pass2"

on_error: continue   # or "stop" (default)

steps:
  - type: navigate
    url: "{{base_url}}/login"
  - type: fill
    selector: "#email"
    value: "{{username}}"
  - type: screenshot
    file: "result-{{username}}.png"
```

- Each row runs all steps independently
- Output goes to `<output>/<_label>/` or `<output>/row-N/`
- Row variables override `variables`
- Result includes `rows_total`, `rows_passed`, `rows_failed`

## Error Context

On failure, automatically collects:
- Current URL
- Error screenshot (`error-step-N.png`)
- HTML snapshot (`error-step-N.html`)
- Console errors and network failures

## Tips

- Use `pomelo-pw explore` first to find reliable selectors
- Prefer `role=` and `text=` selectors over CSS classes
- Use `save-state` / `load-state` to avoid repeated logins
- Use `data:` field for parameterized runs across multiple users/environments
- Use `if` to handle optional UI elements (cookie banners, modals)
- Use `loop` + `while: element_visible: .load-more` to paginate
- Use `retry: 3` on flaky steps instead of adding fixed delays
