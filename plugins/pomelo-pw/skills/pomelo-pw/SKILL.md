---
name: pomelo-pw
description: Run browser automation flows using Pomelo PW through the pomelo-pw CLI.
---

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
- `pomelo-pw run <flow-file> -o <dir>` - Override the flow output directory
- `pomelo-pw run <flow-file> --var key=value` - Override variables
- `pomelo-pw run <flow-file> --headless` - Headless mode
- `pomelo-pw validate <flow-file>` - Validate without running
- `pomelo-pw steps` - List all available steps
- `pomelo-pw spec <step>` - Show step parameters

## Flow File Format

```yaml
name: flow-name
description: Optional description
output_dir: "output"
headless: false

variables:
  base_url: "https://the-internet.herokuapp.com"
  run_id: "local"
  username: "admin"

steps:
  - type: navigate
    url: "{{base_url}}/login"
```

### Variable Syntax

Complete references preserve JSON types: `{{name}}`, `{{item.path}}`, `{{inputs.filter}}`, and `{{results.records[0].id}}`. Paths support identifier fields and nonnegative array indexes. Embedded references accept scalar text only. Use `\{{` for literal template openings. `inputs` and `results` are reserved input names.

Input precedence: CLI/API overrides > current step variables > enclosing variables > data row > flow variables. CLI `--var` values remain strings.

Pass data into browser functions through `args`; script source is literal:
```yaml
- type: evaluate
  args:
    token: "{{api_token}}"
  script: "async ({token}) => { const response = await fetch(`/api?token=${encodeURIComponent(token)}`); return await response.json(); }"
  save_as: response
```

`${ }` is reserved for host languages such as JavaScript and is not processed as flow variable syntax.

`save_as` binds successful public JSON output (currently supported by evaluate, request and poll); read it with `{{results.response}}`. Results are shared by nested steps and isolated between data rows. Child parameters resolve at execution; child local variables do not leak into siblings. Input definitions may reference other inputs; cycles fail. Results stay opaque, even if strings contain template syntax. Rebinding replaces a result; a failed write clears the old binding, while its arguments may read the previous snapshot.

`evaluate.script` must be a synchronous or async function expression and explicitly return JSON data; use `return null` for no data. Omitted args passes no arguments; explicit null passes one null. Unsupported values, nonfinite numbers, and circular data fail. Migrate bare module bodies to functions and source interpolation to args; no compatibility adapters are provided.

### Output Directory

Screenshots save to `./<flow-name>/` by default (derived from filename).
- `example/my-test.yaml` → `./my-test/`
- Set top-level `output_dir` in the flow; it supports `{{variable}}` substitution.
- `output_dir` resolves before execution and cannot read results.
- Relative `output_dir` values are resolved from the command working directory.
- Override a flow value with `-o /custom/path`.
- Set top-level boolean `headless` to run without a visible browser; it defaults to `false`.
- Override browser mode with `--headless`.

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
| `select` | `selector`, one of `value` / `label` / `index` | Select dropdown option |
| `check` / `uncheck` | `selector` | Toggle checkbox |
| `evaluate` | `script`, optional `args`, `save_as` | Execute a browser function with JSON input/output |
| `request` | `url`, optional method/query/headers/json/response | Share browser cookies and return HTTP response data |
| `set-viewport` | `width`, `height` | Set viewport size |
| `save-state` | `file` | Save cookies + localStorage |
| `load-state` | `file` | Restore saved auth state |
| `if` | `condition`, `then` | Conditional execution |
| `loop` | `steps`, `times`/`while` | Loop execution |
| `poll` | `until`, `steps` | Bounded query rounds with fresh results |
| `foreach` | `items`, `steps`, optional `as`, `index_as` | Serial array iteration with local bindings |

## Step Details

### select - Dropdown Options

Provide `selector` and exactly one option selector:

- `value`: the option's HTML `value` attribute
- `label`: the option's exact visible text
- `index`: the option's zero-based position

```yaml
# Prefer a stable option value when available
- type: select
  selector: "#country"
  value: "cn"

# Use the text shown to the user when no stable value is available
- type: select
  selector: "#country"
  label: "China"

# Use a zero-based position when the option value is created by an earlier UI step.
- type: select
  selector: "#course-adoption"
  index: 1
```

### wait — Enhanced SPA Support

Choose exactly one wait mode. For SPA readiness, combine observations under condition:

```yaml
- type: wait
  condition:
    all:
      - page: {url_contains: "/items?page=2"}
      - page: {element_visible: "table tbody tr"}
      - js:
          script: "({id}) => !document.querySelector('table').inert && document.querySelector('tr').dataset.id === id"
          args: {id: "{{record.id}}"}
  timeout: 5000
  interval: 100
```

The shared tree uses fixed runtime snapshots and live page state. Single page/JS conditions use native Playwright waits; combinations check within one deadline. JS must return a boolean, keeps source literal and uses structured args. False means keep waiting; errors fail immediately. interval only applies to condition, state only to selector, route_stable_duration only to route_stable. Timing values are finite positive numbers (delay may be zero); flag modes require true. Mixed modes and string numbers are rejected without adapters.

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
  route_stable_duration: 500

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
  condition:
    page: {element_exists: ".cookie-banner"}
  then:
    - type: click
      selector: ".accept-cookies"
  else:
    - type: screenshot
      file: "no-banner.png"
```

Each condition is an object with exactly one operator:

- `eq: [left, right]` / `ne: [left, right]`: recursive JSON equality, with no coercion; numbers share a type, but `false` differs from `0`.
- `in: [value, array]`: array membership using the same equality rules.
- `exists: "{{results.record.field}}"`: a complete reference; defined null/false/zero/empty values exist. Other operators fail on missing references.
- `all: [condition, ...]` / `any: [condition, ...]`: non-empty lists, evaluated in order with short circuits; `not: condition` negates one object.
- `page: {element_exists: selector}`: also supports `element_visible`, `element_hidden`, `url_contains`, `url_matches` (Python regex search), and `text_contains` (Playwright DOM text matching).
- `js: {script: "({record}) => record.enabled === false", args: {record: "{{results.record}}"}}`: a synchronous or async function returning a boolean; source stays literal.

Guard optional data with exists before accessing its fields. Static validation checks the whole tree, while runtime resolves only visited nodes. Page probes are immediate; visibility uses the first match and absent elements are hidden. Text probes use Playwright whitespace normalization, not HTML source. JS uses structured args and distinguishes omitted args from null. Old colon strings and bare JS expressions are rejected without compatibility adapters.

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
  while:
    page: {element_visible: ".load-more"}
  max_iterations: 20
  steps:
    - type: click
      selector: ".load-more"
    - type: wait
      network_idle: true
```

### foreach - Array Iteration

```yaml
- type: foreach
  items: "{{results.records}}"
  as: record
  index_as: position
  steps:
    - type: evaluate
      args: {record: "{{record}}", index: "{{position}}"}
      script: "payload => payload"
```

Arrays are snapshotted on entry and traversed serially; empty arrays execute no children. Default names are `item`/`index`, with a zero-based index. Aliases must be distinct, non-reserved ASCII identifiers. Bindings override ordinary variables and CLI overrides, stay opaque, and are restored after nested loops. Old foreach times/while calls must use loop; loop requires exactly one mode, integer counts, and max_iterations only with while.

While checks its condition again after the last allowed iteration: false completes, true fails with exhaustion. There is no adapter for the old successful-exhaustion behavior.

### poll - Bounded Queries

```yaml
- type: poll
  until: {in: ["{{results.task.body.status}}", [ready, failed]]}
  timeout: 30000
  interval: 1000
  max_attempts: 20
  save_as: polling
  steps:
    - type: request
      url: "/api/tasks/{{results.submitted.body.id}}"
      save_as: task
      retry: 2
      retry_delay: 250
```

The non-empty body runs immediately, then until reads fresh results. False waits interval after the round. Timeout (default 30000ms) includes body, condition, retries and delays; interval defaults to 1000ms. Both are finite positive numbers; optional max_attempts is a positive integer. All bounds support complete typed references. Nested polls cannot extend the parent's deadline. Exhaustion fails; a true condition on the final round succeeds. Keep writes before poll and declare read retries on children; poll rejects parent retry parameters.

Successful output is `{attempts, elapsed_ms, results}` with the body's latest successful bindings. Terminal business failures may satisfy until; handle outcomes in later branches. Failure details live in failed_step.diagnostics.polls, including nested paths and prior successful values even after a failed rebind. At timeout no new operations start and late results are discarded; in-flight browser operations may finish, with late errors consumed. on_error=continue still reports an unsuccessful flow if any step failed.

### request - Browser Session HTTP

```yaml
- type: request
  url: /api/tasks
  method: POST
  headers: {Authorization: "Bearer {{token}}"}
  json: {id: "{{record.id}}", enabled: false, metadata: null}
  expected_status: 201
  save_as: submitted
```

Prefer request for HTTP queries instead of generic fetch scripts. It shares the current BrowserContext Cookie storage, including response updates. Relative URLs use the current HTTP(S) page URL, not HTML base; absolute HTTP(S) URLs also work on about:blank. It bypasses page fetch, CORS, route handlers and Service Workers. Extra authentication headers are explicit; localStorage tokens are not copied. Redirects follow Playwright behavior, and checks apply to the final response.

Defaults are GET, 30000ms, response: json and any 2xx status. Uppercase methods: GET/HEAD/POST/PUT/PATCH/DELETE/OPTIONS. query values are strings, finite numbers or booleans (encoded as lowercase true/false); headers values are strings. Both use non-empty string keys, and objects and nested fields accept typed references. json may be any JSON value, including null, and is forbidden with GET/HEAD; absent json sends no body. JSON Content-Type defaults to application/json unless supplied explicitly. expected_status accepts an integer or a non-empty integer list (100-599).

Output is `{url, status, headers, body}`; use `{{results.task.body.status}}`. response: text reads text or empty responses; JSON errors never fall back to text. HTTP success does not imply business success. The finite request timeout also covers response reading and is clamped by poll's remaining budget. In-flight calls may finish after timeout; late responses are released, errors consumed and output discarded. There are no implicit retries; explicit retry may repeat writes, so callers own idempotency. retry_on filters RequestNetworkError/RequestTimeoutError/RequestStatusError/RequestResponseError. API responses are released without disposing the shared client. See the local fixture setup in example/README.md.

### Step-Level Retry

Operation steps and if/loop/foreach support retry parameters; poll requires retries on its children:

Retries on if/loop/foreach only cover the parent's own probe or setup. A child failure never replays completed branches or iterations; put retries on the individual operation. Nested errors include the step path and array index.

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
  base_url: "https://the-internet.herokuapp.com"

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
- Row variables override flow `variables`; CLI/API overrides remain highest priority
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
- Use `loop` + `while: {page: {element_visible: ".load-more"}}` to paginate; conditions read fresh results before each iteration
- Use `retry: 3` on flaky steps instead of adding fixed delays
