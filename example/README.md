# Flow Examples

These flows are runnable starting points for common browser-automation work. They use the current Pomelo PW step set and write artifacts under `./output/`, which is ignored by Git.

Run a flow from the repository root:

```bash
pomelo-pw run example/public/page-smoke.yaml
```

Every example defaults to a visible browser. Add `--headless` for CI or unattended runs, and use `--base-url` or `--var key=value` to adapt variables without editing the YAML.

```bash
pomelo-pw run example/public/page-smoke.yaml --headless
pomelo-pw run example/public/page-smoke.yaml --base-url https://staging.example.com
pomelo-pw run example/public/data-driven-pages.yaml --var base_url=https://staging.example.com
```

## Public Checks

| Flow | Covers | Ready to run |
| --- | --- | --- |
| `public/page-smoke.yaml` | Navigation, viewport, scrolling, screenshots | Yes |
| `public/spa-readiness.yaml` | Selector, network, animation, and route waits | Yes |
| `public/conditional-content.yaml` | Conditional branches and content checks | Yes |
| `public/scroll-loop.yaml` | Bounded loops and fixed delays | Yes |
| `public/incremental-content.yaml` | Nested conditionals while loading more content | Yes, public demo site |
| `public/data-driven-pages.yaml` | Labeled data-driven runs | Yes |
| `public/scripted-page-check.yaml` | In-page JavaScript evaluation | Yes |
| `public/runtime-results.yaml` | Typed results, structured args, nested result references | Yes, offline |
| `public/structured-conditions.yaml` | Data/page/JS conditions, short circuits, fresh while results | Yes, offline |
| `public/collection-iteration.yaml` | Serial arrays, nested bindings, source snapshots, scope restoration | Yes, offline |
| `public/page-condition-wait.yaml` | Combined SPA readiness, native JS waits, structured args | Yes, offline |
| `public/bounded-step-polling.yaml` | Serial query rounds, fresh results, terminal outcomes and budgets | Yes, offline |
| `public/session-http-request.yaml` | Browser Cookie sharing, typed HTTP payloads, query polling and text output | Start the local fixture below |
| `public/dom-data-extraction.yaml` | DOM snapshots, field mapping, raw/absolute URLs, live values and foreach | Yes, offline |
| `public/flow-assertions-results.yaml` | Per-item collection, assertions, exports and bounded execution reports | Yes, offline |
| `public/flow-capability-example.yaml` | Paginated DOM inventory, restored Cookie sessions, serial tasks and business policy | Start the capability fixture below |
| `public/visual-regression.yaml` | Screenshot baseline comparison | Yes, with Pillow |

## Runtime Results

`public/runtime-results.yaml` uses `about:blank` and needs no external service. Run the workspace version to try the new result contract:

```bash
uv run --locked --no-sync pomelo-pw run example/public/runtime-results.yaml --headless -v
```

`evaluate.script` must be a synchronous or async function expression. Pass data through `args` and bind its JSON return value with `save_as`; script source is kept literal. Bare module bodies and template substitution inside script source must be migrated to this contract.

## Structured Conditions

`public/structured-conditions.yaml` creates a small DOM on `about:blank`, combines data and page probes, skips missing fields through short circuits, and increments a stored counter through a while loop. Its final branch checks both the loop results and JS argument rules, then writes `conditions.png`.

```bash
uv run --locked --no-sync pomelo-pw run example/public/structured-conditions.yaml --headless -v
```

Conditions are objects such as `eq: ["{{results.counter}}", 3]` or `page: {element_visible: "h1"}`. Use `all`, `any`, and `not` to combine them. Old condition strings must be migrated to objects; custom JS predicates use a function under `js.script` and structured `js.args`.

## Page Condition Waits

`public/page-condition-wait.yaml` changes the hash route immediately and refreshes a row after a short timer. It waits for the route, visible row and matching data together, then uses a native JS wait in a nested branch. Its final summary checks both pages and the omitted/null argument contract before capturing `ready.png`.

```bash
uv run --locked --no-sync pomelo-pw run example/public/page-condition-wait.yaml --headless -v
```

Use one mode per wait; combine observations under condition rather than mixing selector, URL and delay fields. Positive timeout/interval values are milliseconds. False conditions continue checking; predicate errors fail immediately.

## Collection Iteration

`public/collection-iteration.yaml` fills three inputs from nested arrays on `about:blank`. It rewrites the source result after each outer iteration while preserving the original traversal, passes a literal template-shaped value unchanged, and checks that ordinary input values are restored after the loop.

```bash
uv run --locked --no-sync pomelo-pw run example/public/collection-iteration.yaml --headless -v
```

`foreach` accepts `items` and `steps`, with optional `as`/`index_as` aliases. It snapshots the array and provides isolated, zero-based bindings. Child retries do not restart the traversal; old foreach count/while calls must use `loop`.

## Bounded Step Polling

`public/bounded-step-polling.yaml` runs two offline tasks through foreach and poll. Each task reaches its terminal state on the third round; ready and failed both end polling, then the final summary counts their business outcomes and writes `tasks.png`.

```bash
uv run --locked --no-sync pomelo-pw run example/public/bounded-step-polling.yaml --headless -v
```

Poll requires a non-empty steps body and a structured until condition. The first round is immediate; interval is measured after each unsuccessful round. Timeout covers queries, conditions, retries and delays. Use child retries for reads and keep submissions outside poll. Successful save_as includes attempts, elapsed_ms and the body's latest successful bindings; exhausted limits fail. While also fails if its condition remains true after max_iterations.

## Browser Session HTTP Requests

`public/session-http-request.yaml` uses a loopback fixture, with no external site or real credentials. Start the fixture in one terminal, then run the flow in another:

```bash
uv run --locked --no-sync python example/support/session_http_server.py --port 8766
```

```bash
uv run --locked --no-sync pomelo-pw run example/public/session-http-request.yaml --headless -v
```

If the port is occupied, choose a different `--port` and pass the matching `--base-url http://127.0.0.1:PORT` to the flow. Stop the fixture with Ctrl+C afterward. The flow signs in through the page, sends typed query/header/JSON values, checks response Cookie updates, polls a task to ready on the second query, reads a text response and writes `session.png`.

Request defaults to GET/JSON/2xx with a finite 30000ms timeout. Relative URLs need a current HTTP(S) page. Read content through `results.NAME.body`; expected HTTP errors can be listed explicitly with expected_status. Empty or text responses require response: text. Only explicit retry replays a request; keep submissions outside poll and choose read retry_on filters when needed.

## DOM Data Extraction

`public/dom-data-extraction.yaml` creates an offline table on about:blank, waits for readiness, extracts two mapped records, and consumes the ready record through foreach/if and a nested extraction. It checks DOM order, text whitespace, raw attributes versus absolute URLs, live input values, optional null/false/0 defaults, empty strings and an empty collection, then writes `extracted.png`.

```bash
uv run --locked --no-sync pomelo-pw run example/public/dom-data-extraction.yaml --headless -v
```

Extract does not wait: use wait for page readiness first. Root selectors use Playwright, while field selectors use row-relative CSS (with :scope), without frame/Shadow DOM traversal. one is strict; all returns a possibly empty array. Missing required values and ambiguous field matches fail. Use required: false for null or an explicit JSON default; raw attributes, text and current form values remain strings. URL mode resolves against the element's baseURI.

## Assertions and Execution Reports

`public/flow-assertions-results.yaml` creates three offline records, extracts them, collects two processed and one skipped outcome, and exports those outcomes plus `{total: 3, processed: 2, skipped: 1, failed: 0}`. It asserts the summary and the first category, records nested step paths, and writes `outcomes.png`.

```bash
uv run --locked --no-sync pomelo-pw run example/public/flow-assertions-results.yaml --headless --json -v
```

stdout contains a single schema_version=1 JSON report, with logs on stderr. To exercise a controlled assertion failure and exit code 1, add `--var expected_first_category=unexpected`; outcomes/summary still export, and errors contain the visited values plus screenshot/HTML evidence. The successful path exits 0. Business outcome categories only affect execution status through explicit assertions.

Optional report.steps records bounded execution detail; include_outputs requires steps and is off by default. Explicit exports are complete. foreach collection limits fail rather than truncating data, with no partial collection binding.

## Integrated Flow Capabilities

Start the dedicated loopback fixture, then run the flow from another terminal:

```bash
uv run --locked --no-sync python example/support/flow_capability_server.py --port 8767
```

```bash
uv run --locked --no-sync pomelo-pw run example/public/flow-capability-example.yaml --headless --json -v
```

The default mixed scenario collects seven materials across two asynchronously loaded pages. It saves the signed-in Cookie, removes it through the fixture's logout endpoint, observes HTTP 401, and restores it with load-state before requesting data. It then skips missing/unsupported/previously failed files, resumes an existing task, and submits two new tasks serially. Final summary: total=7, ready=3, skipped=3, failed=1, submitted=2, resumed=1. inventory, outcomes, summary and the server's independent audit are explicitly exported.

| Options appended to the run command | Expected execution result |
| --- | --- |
| None | Passed, exit 0; business failure appears in the summary |
| `--var failure_policy=fail` | Assertion failure, exit 1; complete outputs retained |
| `--var scenario=empty` | Passed, exit 0; empty inventory/outcomes and zero counts |
| `--var scenario=read-error` | HTTP 503 while querying the first new task, exit 1 |
| `--var scenario=timeout` | First new task stays pending until poll timeout, exit 1 |

For read-error/timeout, inventory remains available, while the incomplete foreach collection and later summary/audit are not published; unresolved declared outputs add explicit output errors. The first error retains the nested item/operation path, polling diagnostics and screenshot/HTML evidence. Already submitted tasks are not replayed, and the next material is not submitted. Business classifications only become execution failures through the explicit policy assertion.

Each page waits for matching route, page number and ready marker before extract. The few evaluate functions only flatten snapshots, project business outcomes, count categories and render the summary; pagination, branching, submission and polling use public steps. The audit records visited pages and submit/terminal ordering, and rejects duplicate or overlapping submissions. Repeated runs create fresh sessions. This fixture's logout clears the client Cookie without revoking the simulated server session, allowing state restoration to be checked.

If port 8767 is occupied, choose another `--port` and pass the matching `--base-url http://127.0.0.1:PORT`. Stop the fixture with Ctrl+C. JSON stdout can be redirected independently from stderr logs. No external business service or real credentials are used.

The focused regression file runs two fast checks by default. Enable its five real browser CLI scenarios explicitly (PowerShell):

```powershell
$env:POMELO_PW_INTEGRATION = '1'
uv run --locked --no-sync pytest tests/test_flow_capability_example.py -q
Remove-Item Env:POMELO_PW_INTEGRATION
```

Those checks start and stop their own fixture on a temporary port. A usable system Chrome/Chromium or installed Playwright browser is required; no browser mock replaces the integration checks.

## Browser Interactions

| Flow | Covers | Ready to run |
| --- | --- | --- |
| `interactions/dynamic-content-retry.yaml` | Click and wait retries | Yes, public demo site |
| `interactions/form-controls.yaml` | Select by index, check, uncheck, fill, type, and press | Yes, public demo site |
| `interactions/hover-reveal.yaml` | Hover and visibility waits | Yes, public demo site |

The interaction flows use `https://the-internet.herokuapp.com`, a public training site. Treat its selectors as examples rather than production contracts.

## Browser State

Run the state flows in order from the same working directory because both use `output/browser-state.json`:

```bash
pomelo-pw run example/state/save-browser-state.yaml
pomelo-pw run example/state/reuse-browser-state.yaml
```

The state examples intentionally save an anonymous public-page session. For an authenticated application, replace the URL and add your own login steps; keep credentials outside the flow file, for example with `--var` values supplied by your CI secret store.

## Visual Comparison

`public/visual-regression.yaml` first captures `baseline.png` and then compares a second capture in the same run. Install the optional image dependency before using it:

```bash
uv pip install "pomelo-pw[visual]"
```

## Discover and Record

Use the interactive tools before adapting a flow to your application:

```bash
pomelo-pw explore https://the-internet.herokuapp.com
pomelo-pw record https://the-internet.herokuapp.com my-flow.yaml
```

Prefer `data-test`, ID, role, and stable text selectors over CSS classes. Validate a flow before running it:

```bash
pomelo-pw validate example/interactions/form-controls.yaml
```
