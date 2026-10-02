# Pomelo PW

[![CI](https://github.com/leoninew/pomelo-pw/actions/workflows/ci.yml/badge.svg)](https://github.com/leoninew/pomelo-pw/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/pomelo-pw)](https://pypi.org/project/pomelo-pw/)
[![GitHub Release](https://img.shields.io/github/v/release/leoninew/pomelo-pw)](https://github.com/leoninew/pomelo-pw/releases)

[English](README.md) | [简体中文](README_CN.md)

Pomelo PW is a Playwright-powered CLI for browser automation. It runs declarative YAML flows, so browser checks can live alongside application code without requiring a custom test harness.

It is intended for repeatable UI checks, scripted workflows, visual comparisons, and agent-assisted browser tasks. Flows validate their parameters before execution and collect screenshots, page snapshots, console errors, and network failures when a step fails.

## What It Provides

- YAML flows with `{{variable}}` substitution and CLI overrides
- Browser steps for navigation, forms, waits, screenshots, state reuse, conditions, and loops
- Interactive explorer and recorder for finding selectors and creating starting flows
- Step-level retries, data-driven runs, and screenshot baseline comparison
- Native plugin packaging for Claude Code, Codex, and Grok Build

## Install

Pomelo PW requires Python 3.12+ and [uv](https://docs.astral.sh/uv/).

The Python package is available on [PyPI](https://pypi.org/project/pomelo-pw/). Standalone Windows, macOS, and Linux executables are available from [GitHub Releases](https://github.com/leoninew/pomelo-pw/releases).

```bash
# Install the published CLI, then install its browser
uv tool install pomelo-pw
pomelo-pw install

# Or invoke the published package once without installing the CLI
uvx pomelo-pw install

# Work from a source checkout
uv sync --all-groups --locked
uv run pomelo-pw install
```

The `install` command downloads Playwright Chromium for package installations. When run from a source checkout or the standalone binary, Pomelo PW uses an installed system Chrome or Chromium when it can find one.

Install visual comparison support only when flows use screenshot baselines:

```bash
uv pip install pillow
```

## Quick Start

Create `smoke.yaml`:

```yaml
name: example-smoke
output_dir: "output"
headless: false
variables:
  base_url: "https://the-internet.herokuapp.com"
  run_id: "local"

steps:
  - type: navigate
    url: "{{base_url}}"
  - type: screenshot
    file: "homepage.png"
  - type: scroll
    direction: down
    distance: 500
  - type: screenshot
    file: "scrolled.png"
```

Run and validate it:

```bash
uvx pomelo-pw validate smoke.yaml
uvx pomelo-pw run smoke.yaml --headless
```

Screenshots and failure artifacts are written to `./smoke/` by default. A flow can set a top-level `output_dir`, including `{{variable}}` references; relative paths are resolved from the command working directory. Flows can also set a top-level boolean `headless`; it defaults to `false`. Use `-o <directory>` or `--headless` to override either setting for one run.

## Use Pomelo PW

### Find Selectors and Create Flows

```bash
# Inspect a page and copy a selector from the interactive overlay
pomelo-pw explore https://the-internet.herokuapp.com

# Record clicks, fills, and Enter presses into a YAML flow
pomelo-pw record https://the-internet.herokuapp.com recorded-flow.yaml
```

Prefer selectors based on stable semantics, such as `role=button[name="Continue"]`, over presentation-oriented CSS classes.

### Run Flows

```bash
# Run visibly with step progress
pomelo-pw run flow.yaml -v

# Run headlessly and emit the result as JSON
pomelo-pw run flow.yaml --headless --json

# Override a flow variable for this run
pomelo-pw run flow.yaml --var base_url=https://staging.example.com

# Override the flow output_dir for this run
pomelo-pw run flow.yaml -o .pomelo-pw/artifacts/manual-run

# Validate YAML and step parameters without launching a browser
pomelo-pw validate flow.yaml
```

Input precedence is CLI/API overrides > current step variables > enclosing step variables > data row > flow variables. `--var key=value` remains a text input. `inputs` and `results` are reserved input names.

### Runtime Data

Complete references preserve JSON types: `{{name}}`, `{{item.path}}`, `{{inputs.filter}}`, and `{{results.records[0].id}}`. References embedded in text accept scalars only (`false`, `0`, and `null` use JSON spelling); objects and arrays cannot be interpolated into text. Paths support identifier fields and nonnegative array indexes. Use `\{{` for a literal template opening; `${name}` stays untouched.

```yaml
steps:
  - type: evaluate
    script: "() => [{id: 'a', enabled: false}]"
    save_as: records
  - type: evaluate
    args: "{{results.records[0]}}"
    script: "async (record) => ({id: record.id, enabled: record.enabled})"
    save_as: selected
```

`evaluate.script` is a synchronous or async function expression, kept as literal source. Pass one JSON payload through `args`; omitted args calls the function with no arguments, while `args: null` passes one null argument. Return a JSON value explicitly (use `return null` when no data is needed). Unsupported values, nonfinite numbers, and circular data fail.

Only output-producing steps support `save_as` (currently `evaluate`, `extract`, `request` and `poll`). A successful step publishes a copied result; another successful write replaces it. During replacement, arguments can read the previous value, but a failed attempt leaves the binding absent. Results are shared by nested steps and isolated between data rows. Child parameters resolve when the child executes; child variables do not leak into siblings. Returned strings are data and are never reinterpreted as templates. `output_dir` resolves before execution and can only use inputs.

This is a breaking contract change with no compatibility adapters. Migrate bare module bodies to functions and source interpolation to `args`. Complete references no longer force values to strings. Python step implementations use `StepContext.runtime`/`inputs` and `StepResult.output`, `control`, and `diagnostics`; `variables` and `StepResult.data` are removed. See [the offline example](example/public/runtime-results.yaml).

### Structured Conditions

`if.condition` and `loop.while` use the same condition object, with exactly one operator per node:

```yaml
- type: if
  condition:
    all:
      - exists: "{{results.record.enabled}}"
      - eq: ["{{results.record.enabled}}", false]
      - in: ["{{results.record.status}}", [ready, completed]]
      - page: {element_visible: "#submit"}
  then:
    - type: click
      selector: "#submit"
```

`eq`/`ne` compare two JSON values recursively, without coercion: `1` equals `1.0`, but `false` differs from `0`. `in: [value, array]` uses the same equality rules. `exists` requires one complete reference and tests presence, so defined null, false, zero and empty values all exist. Other missing references fail. `all`/`any` take non-empty lists and short-circuit in order; `not` takes one condition object. Guard optional fields with `exists` before comparing them.

`page` supports `element_exists`, `element_visible`, `element_hidden`, `url_contains`, `url_matches` (Python regex search), and `text_contains` (Playwright DOM text matching). Visibility uses the first matching element; missing elements are hidden. These are immediate probes, without polling or waiting. Text matching uses Playwright whitespace normalization rather than searching HTML source.

For custom predicates, use `js: {script: "({flag}) => flag === false", args: {flag: "{{results.record.enabled}}"}}`. The synchronous or async function must return a boolean. Source stays literal and omitted args differs from null, as with evaluate. Each probe takes a fresh input/result snapshot, and `while` probes again before every iteration. Static validation checks the complete tree; runtime resolves only visited nodes. Old colon strings and bare JS expressions are rejected without adapters. See [the offline condition example](example/public/structured-conditions.yaml).

### Page Condition Waits

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

`wait.condition` uses the same condition tree and strict boolean JS contract as `if`/`while`. Already-satisfied conditions finish immediately; false conditions repeat within one deadline, including async probes. Predicate errors fail immediately. Single page/JS leaves use Playwright's native waits; combinations inspect live page state using fixed input/result/iteration snapshots. `interval` controls combinations and JS predicates; page leaves use Playwright's built-in polling. A URL change alone proves only the URL condition. See [the offline wait example](example/public/page-condition-wait.yaml).

Each wait must choose exactly one mode: `condition`, `delay`, `selector`, `url`, `url_contains`, `url_pattern`, `for`, `network_idle`, `animation_stable`, or `route_stable`. `interval` applies only to condition (default 100ms), `state` only to selector, and `route_stable_duration` only to route_stable. Timeout defaults to 30000ms; timing values must be finite and positive, except delay may be zero. Complete typed references are allowed; string numbers and booleans are rejected. Flag modes require true. Mixed modes fail validation without adapters. Animation stability observes active Web Animations rather than declared CSS durations.

### Bounded Step Polling

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

`poll` executes its non-empty body immediately, then checks `until` against fresh results. False waits `interval` after the round before the next query. Timeout defaults to 30000ms and interval to 1000ms; both must be finite positive numbers. Optional `max_attempts` is a positive integer; all bounds accept complete typed references. Timeout includes body steps, conditions, child retries and delays, and nested polls share the outer deadline. Exhaustion fails; a true condition on the final allowed round succeeds.

Declare retries on individual queries; poll rejects parent retry parameters. A terminal business failure can satisfy until and is handled by later branches. Optional `save_as` stores `{attempts, elapsed_ms, results}`, with the latest successful bindings produced by the body. Failures retain those results, condition, timing, phase and nested path under `failed_step.diagnostics.polls`. `on_error: continue` runs later steps but still reports a failed flow.

Keep submissions before poll. At timeout, no new steps or retries start and late results are discarded; already-issued browser operations may finish and their errors are consumed. Polling does not undo side effects. See [the offline polling example](example/public/bounded-step-polling.yaml).

### Browser Session HTTP Requests

```yaml
- type: request
  url: /api/tasks
  method: POST
  headers: {Authorization: "Bearer {{token}}"}
  json: {record_id: "{{record.id}}", enabled: false, metadata: null}
  expected_status: 201
  save_as: submitted
- type: request
  url: "/api/tasks/{{results.submitted.body.id}}"
  query: {details: true}
  save_as: task
```

`request` uses the current BrowserContext's API request client, sharing browser cookies and response Cookie updates. Relative URLs resolve against the current HTTP(S) page URL (not its HTML base tag); absolute HTTP(S) URLs also work on about:blank. These requests bypass page fetch, CORS, page route handlers and Service Workers. Playwright follows redirects; status checks and output refer to the final response. Extra authorization/CSRF headers must be supplied explicitly; localStorage tokens are not copied.

Defaults are `method: GET`, `timeout: 30000`ms, `response: json`, and any 2xx status. Methods are uppercase GET/HEAD/POST/PUT/PATCH/DELETE/OPTIONS. `query` maps non-empty string keys to strings, finite numbers or booleans (encoded as lowercase true/false); `headers` maps non-empty string keys to strings. Whole-object and nested typed references are supported and checked after resolution. `json` accepts any JSON value, including explicit null; omitting it sends no body. GET/HEAD reject json. Content-Type defaults to application/json for JSON bodies unless supplied explicitly.

Output is always `{url, status, headers, body}`. Read JSON fields with `{{results.task.body.status}}`; choose `response: text` for text or empty responses (including HEAD/204). Invalid or empty JSON fails without fallback. Optional `expected_status` is one HTTP status integer or a non-empty list (100-599); status is checked before parsing. HTTP success is separate from business success.

Request timeout covers network and response reading, and is tightened to the remaining poll budget. In-flight protocol calls may finish after timeout; late responses are released, late errors consumed and late output discarded. Responses are released after reading without disposing the shared client. Failures use `RequestNetworkError`, `RequestTimeoutError`, `RequestStatusError` and `RequestResponseError`. There are no implicit retries; explicit `retry` uses the existing single-step policy, with optional `retry_on` class-name filters. Write retries require caller-controlled idempotency. See [the local session HTTP example](example/public/session-http-request.yaml) and its [server setup](example/README.md#browser-session-http-requests).

### DOM Data Extraction

```yaml
- type: extract
  selector: table tbody tr
  mode: all
  fields:
    id: {read: attribute, attribute: data-id}
    name: {selector: .name}
    raw_href: {selector: a, read: attribute, attribute: href}
    url: {selector: a, read: url, attribute: href}
    status: {selector: .status, required: false, default: unknown}
  save_as: records
- type: extract
  selector: '#page-size'
  read: value
  save_as: page_size
```

`extract` takes one synchronous DOM snapshot without waiting or changing the page. Wait for readiness first. The root selector uses Playwright; each field selector is relative CSS, supports `:scope`, and stays within the row's DOM (no frame or Shadow DOM traversal). Omit a field selector to read the row itself. Field names are ASCII identifiers. Whole `fields` objects and configuration values accept typed references and are checked again at execution.

`mode: one` (default) returns a scalar or mapped object and rejects multiple roots; `mode: all` returns an array in DOM order, including `[]` for no roots. Without fields, read each root directly. `read: text` (default) uses textContent, including hidden text; `trim: true` only removes outer whitespace, and `trim: false` preserves it. `read: attribute` requires attribute and returns its raw string; `read: url` also requires attribute and resolves it against the element's baseURI, including HTML base. `read: value` returns the current input/textarea/select string; it does not convert numbers or checkbox state. Other element types fail. Do not combine fields with root read/attribute/trim, or use trim outside text mode.

Missing single roots, field elements or attributes fail by default. Use `required: false` for null, or add a JSON default (only allowed with required: false). Empty strings are valid values; false/0/null defaults are preserved. Multiple field matches always fail, with row and field locations. Root required/default never override mapped field settings; an empty all collection stays empty. Results bind directly for foreach/conditions/poll; retries are explicit and poll discards late snapshots. See [the offline extraction example](example/public/dom-data-extraction.yaml).

### Collection Iteration

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

`foreach` visits a snapshot of a JSON array in order; an empty array executes no children. `as` defaults to `item` and `index_as` to `index`, starting at zero. Names must be distinct, non-reserved ASCII identifiers. Iteration bindings take precedence over ordinary variables and CLI overrides, remain opaque data, and restore outer bindings after nested iterations. Rewriting the source result does not change an active traversal. See [the offline collection example](example/public/collection-iteration.yaml).

`loop` requires exactly one of `times` (a nonnegative integer) or `while`; `max_iterations` is a positive integer allowed only with `while`. Both counts support complete typed references. After the final allowed while iteration, the condition is checked again: false completes, true fails with exhaustion. Old `foreach` count/while calls must use `loop`; no successful-exhaustion adapter is provided. Parent `if`/`loop`/`foreach` retries cover only the parent's own probe or setup; child failures never replay completed bodies. Declare retries on the child operation that needs them. Nested errors include the step path and collection index.

### Author Flows

The following flow shows the common pattern: navigate, interact, wait for a meaningful result, then capture evidence.

```yaml
name: login-smoke
variables:
  base_url: "https://app.example.com"
  username: "user@example.com"
  password: "secret"

steps:
  - type: navigate
    url: "{{base_url}}/login"
  - type: fill
    selector: "input[name='email']"
    value: "{{username}}"
  - type: fill
    selector: "input[name='password']"
    value: "{{password}}"
  - type: click
    selector: "button[type='submit']"
  - type: wait
    url_contains: "/dashboard"
  - type: screenshot
    file: "dashboard.png"
```

| Step | Main parameters | Purpose |
| --- | --- | --- |
| `navigate` | `url` | Open a page |
| `click`, `hover`, `press` | `selector` or `key` | Interact with an element or keyboard |
| `fill`, `type` | `selector`, `value` | Enter text |
| `select` | `selector`, one of `value` / `label` / `index` | Choose an option by HTML value, visible text, or zero-based position |
| `wait` | selector, URL, network, or timing condition | Synchronize with dynamic UI |
| `screenshot` | `file` | Capture a page or element, optionally against a baseline |
| `check`, `uncheck` | `selector` | Control checkboxes |
| `save-state`, `load-state` | `file` | Reuse authenticated browser state |
| `if`, `loop` | condition or iteration settings | Model branches and repeated actions |
| `poll` | `until`, `steps` | Refresh results within a shared deadline |
| `foreach` | `items`, `steps`, optional `as` / `index_as` | Traverse an array with local item and index bindings |
| `evaluate` | `script`, optional `args` and `save_as` | Run a browser function and pass JSON data |
| `request` | `url`, optional method/query/headers/json/response | Share browser cookies and bind HTTP responses |
| `extract` | `selector`, optional mode/read/fields | Read a DOM value or array of mapped records |
| `scroll`, `set-viewport` | step-specific parameters | Adjust scroll position or viewport |

List the available steps or inspect any step's exact parameters before writing a flow:

```bash
pomelo-pw steps
pomelo-pw spec wait
pomelo-pw spec select
```

The [example/](example/) directory organizes runnable flows into public checks, browser interactions, and browser-state reuse. Its [README](example/README.md) describes each scenario, prerequisites, and variable overrides. The bundled [agent skill](plugins/pomelo-pw/skills/pomelo-pw/SKILL.md) contains agent-oriented guidance and reusable flow templates.

## Develop

Install the locked development environment:

```bash
uv sync --all-groups --locked
```

Run the normal quality gates directly with `uv`:

```bash
uv run --locked --no-sync ruff format --check src tests scripts
uv run --locked --no-sync ruff check src tests scripts
uv run --locked --no-sync mypy src tests scripts
uv run --locked --no-sync pytest
```

On systems with GNU Make and Bash, `make check` and `make test` wrap those commands. `make test cov=1` also writes an HTML coverage report.

### Refresh the Native Plugin

The repository packages the `pomelo-pw` skill as a native plugin. Validate the package first, then refresh the editable CLI and installed plugin for available agent clients:

```bash
uv run --locked python scripts/install.py plugin check
uv tool install --editable . --force
uv run --locked python scripts/install.py plugin apply
```

Restart the agent client after applying a plugin update so it loads the new skill.

### Build and Release

```bash
# Inspect the Git-derived release version
uv run --locked --no-sync python scripts/version_calc.py

# Apply the calculated version to pyproject.toml and uv.lock
uv run --locked --no-sync python scripts/version_calc.py --no-dry-run

# Build source and wheel distributions
uv build

# Upload existing distributions to PyPI
make pypi

# Build a standalone executable when GNU Make and Bash are available
make binary
```

`make pypi` loads `./.env` when it exists; otherwise, Twine uses the current environment, `.pypirc`, or keyring. For a PyPI API token, set `TWINE_USERNAME=__token__` and `TWINE_PASSWORD` to the token in the ignored `.env` file or in your shell environment. The target is non-interactive and will fail without usable credentials.

Release versions are derived from Git history. After reviewing the version-file changes, commit them and create the matching `vX.Y.Z` tag; GitHub Actions builds the wheel and platform binaries from that tag.

## Repository Layout

```text
src/pomelo_pw/       CLI, executor, configuration, and step implementations
tests/               Unit and integration-style tests
example/             Runnable YAML examples and usage guide
plugins/pomelo-pw/   Native plugin and agent skill
docs/                Architecture and process documentation
scripts/             Plugin synchronization and release helpers
```

## License

MIT
