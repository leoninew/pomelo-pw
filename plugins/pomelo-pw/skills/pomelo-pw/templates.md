# Pomelo PW Flow Templates

## Typed Runtime Results

```yaml
name: runtime-results
steps:
  - type: evaluate
    script: "() => [{id: 'a', enabled: false}]"
    save_as: records
  - type: evaluate
    args: "{{results.records[0]}}"
    script: "async (record) => ({id: record.id, enabled: record.enabled})"
    save_as: selected
```

Use args for input and result references; script source is literal and must be a function expression. Return a JSON value explicitly. Complete references retain native types, while text interpolation accepts only scalars. No bare-module or source-template compatibility path is available.

## Basic Templates

### 1. Simple Navigation and Screenshot

```yaml
name: quick-capture
variables:
  url: "https://example.com"

steps:
  - type: navigate
    url: "{{url}}"
  - type: screenshot
    file: "capture.png"
```

### 2. Login Flow

```yaml
name: login-test
variables:
  base_url: "https://example.com"
  username: "user@example.com"
  password: "password123"

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
    file: "logged-in.png"
```

### 3. Responsive Testing

```yaml
name: responsive-test
variables:
  url: "https://example.com"

steps:
  - type: navigate
    url: "{{url}}"
  - type: set-viewport
    width: 1920
    height: 1080
  - type: screenshot
    file: "desktop.png"
  - type: set-viewport
    width: 375
    height: 667
  - type: screenshot
    file: "mobile.png"
```

### 4. Form Submission

```yaml
name: form-submit
variables:
  form_url: "https://example.com/contact"

steps:
  - type: navigate
    url: "{{form_url}}"
  - type: fill
    selector: "#name"
    value: "John Doe"
  - type: fill
    selector: "#email"
    value: "john@example.com"
  - type: check
    selector: "#agree-terms"
  - type: click
    selector: "button[type='submit']"
  - type: wait
    selector: ".success-message"
  - type: screenshot
    file: "submitted.png"
```

---

## Auth State Reuse

### 5. Save Login State

```yaml
name: save-auth
variables:
  base_url: "https://example.com"

steps:
  - type: navigate
    url: "{{base_url}}/login"
  - type: fill
    selector: "#email"
    value: "admin@example.com"
  - type: fill
    selector: "#password"
    value: "secret"
  - type: click
    selector: "button[type='submit']"
  - type: wait
    url_contains: "/dashboard"
  - type: save-state
    file: "auth.json"
  - type: screenshot
    file: "logged-in.png"
```

### 6. Reuse Login State

```yaml
name: test-with-auth
variables:
  base_url: "https://example.com"

steps:
  - type: load-state
    file: "auth.json"
  - type: navigate
    url: "{{base_url}}/dashboard"
  - type: screenshot
    file: "dashboard.png"
```

---

## Conditional Execution

### 7. Handle Optional UI Elements

```yaml
name: handle-cookie-banner
variables:
  url: "https://example.com"

steps:
  - type: navigate
    url: "{{url}}"

  # Dismiss cookie banner if present
  - type: if
    condition:
      page: {element_visible: ".cookie-banner"}
    then:
      - type: click
        selector: ".accept-cookies"
      - type: wait
        animation_stable: true

  - type: screenshot
    file: "page-clean.png"
```

### 8. Branch on Page State

```yaml
name: conditional-flow
variables:
  base_url: "https://example.com"

steps:
  - type: navigate
    url: "{{base_url}}"

  - type: if
    condition:
      page: {url_contains: "/login"}
    then:
      - type: fill
        selector: "#email"
        value: "user@example.com"
      - type: click
        selector: "button[type='submit']"
    else:
      - type: screenshot
        file: "already-logged-in.png"

  - type: screenshot
    file: "final-state.png"
```

---

## Loop Execution

### 9. Scroll Through Page

```yaml
name: scroll-capture
variables:
  url: "https://example.com"

steps:
  - type: navigate
    url: "{{url}}"

  - type: loop
    times: 5
    steps:
      - type: scroll
        direction: down
        distance: 500
      - type: wait
        delay: 300

  - type: screenshot
    file: "bottom-of-page.png"
    full_page: true
```

### 10. Load More Pagination

```yaml
name: load-all-items
variables:
  url: "https://example.com/items"

steps:
  - type: navigate
    url: "{{url}}"

  - type: loop
    while:
      page: {element_visible: ".load-more-button"}
    max_iterations: 20
    steps:
      - type: click
        selector: ".load-more-button"
      - type: wait
        network_idle: true

  - type: screenshot
    file: "all-items.png"
    full_page: true
```

---

### Combined Page Readiness

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

Run after the navigation/click and record extraction. Only one wait mode is allowed; condition combinations do not submit operations or refresh runtime results.

### Collection Results

```yaml
name: collection-results
steps:
  - type: evaluate
    script: "() => [{id: 'a', enabled: true}, {id: 'b', enabled: false}]"
    save_as: records
  - type: foreach
    items: "{{results.records}}"
    as: record
    index_as: position
    steps:
      - type: if
        condition: {eq: ["{{record.enabled}}", true]}
        then:
          - type: evaluate
            args: {record: "{{record}}", index: "{{position}}"}
            script: "payload => payload"
```

Use child retries for individual operations; parent retries do not replay completed iterations.

### Bounded Task Polling

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

Submit before this step. The first query is immediate; timeout includes child retries and intervals. Both ready and failed end polling, so handle the business result afterward. Exhaustion fails, and save_as records attempts, elapsed_ms and the latest successful body bindings.

### Browser Session HTTP Submission

```yaml
- type: request
  url: /api/tasks
  method: POST
  headers: {Authorization: "Bearer {{token}}"}
  json: {record_id: "{{record.id}}", metadata: null}
  expected_status: 201
  save_as: submitted
- type: request
  url: "/api/tasks/{{results.submitted.body.id}}"
  query: {details: true}
  save_as: task
```

Navigate or sign in first for relative URLs and browser cookies. Response content is under body; status and headers remain separate. Extra authentication headers are explicit. Use response: text for non-JSON or empty responses, and keep submissions outside poll. Retry is opt-in and may replay writes; read retries can filter RequestNetworkError and RequestTimeoutError.

### DOM Records and Form Values

```yaml
- type: wait
  condition: {page: {element_visible: 'table tbody tr'}}
  timeout: 5000
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
- type: foreach
  items: '{{results.records}}'
  as: record
  steps:
    - type: evaluate
      args: '{{record}}'
      script: 'record => record'
```

Extraction is immediate. Root selectors use Playwright; fields use row-relative CSS, with no frame/Shadow DOM traversal. one rejects multiple roots; all may be empty. Missing fields fail unless required: false (null or explicit JSON default). Field ambiguity always fails. Text trims outer whitespace only; form values stay strings. Attribute mode preserves raw href; URL mode resolves against the element's baseURI, including HTML base.

## Data-Driven Testing

### 11. Multi-User Test

```yaml
name: multi-user-login
variables:
  base_url: "https://example.com"

data:
  - _label: "admin-user"
    username: "admin@example.com"
    password: "admin123"
    expected_page: "/admin"
  - _label: "regular-user"
    username: "user@example.com"
    password: "user123"
    expected_page: "/dashboard"

steps:
  - type: navigate
    url: "{{base_url}}/login"
  - type: fill
    selector: "#email"
    value: "{{username}}"
  - type: fill
    selector: "#password"
    value: "{{password}}"
  - type: click
    selector: "button[type='submit']"
  - type: wait
    url_contains: "{{expected_page}}"
  - type: screenshot
    file: "result.png"
```

### 12. Multi-Environment Check

```yaml
name: cross-env-check
data:
  - _label: "staging"
    base_url: "https://staging.example.com"
  - _label: "production"
    base_url: "https://example.com"

on_error: continue

steps:
  - type: navigate
    url: "{{base_url}}"
  - type: screenshot
    file: "homepage.png"
  - type: if
    condition:
      page: {element_exists: ".error-banner"}
    then:
      - type: screenshot
        file: "error-state.png"
```

---

## Visual Regression

### 13. Baseline Comparison

```yaml
name: visual-regression
variables:
  url: "https://example.com"

steps:
  - type: navigate
    url: "{{url}}"

  # First run: creates baseline
  # Subsequent runs: compares against it
  - type: screenshot
    file: "homepage-current.png"
    baseline: "homepage-baseline.png"
    threshold: 0.02
    diff_output: "homepage-diff.png"
    fail_on_diff: true
```

---

## SPA / Dynamic Content

### 14. SPA Navigation Wait

```yaml
name: spa-test
variables:
  base_url: "https://app.example.com"

steps:
  - type: navigate
    url: "{{base_url}}"

  - type: click
    selector: "nav a[href='/dashboard']"

  - type: wait
    url_contains: "/dashboard"

  - type: wait
    network_idle: true

  - type: wait
    animation_stable: true

  - type: screenshot
    file: "dashboard.png"
```

### 15. Flaky Element with Retry

```yaml
name: retry-example
variables:
  url: "https://example.com"

steps:
  - type: navigate
    url: "{{url}}"

  - type: click
    selector: ".async-button"
    retry: 3
    retry_delay: 1000

  - type: wait
    selector: ".result"
    timeout: 10000
    retry: 2

  - type: screenshot
    file: "result.png"
```

---

## Collected Outcomes and Assertions

```yaml
name: collected-outcomes
variables:
  records: [{id: a}, {id: b}]
outputs:
  outcomes: '{{results.collected.items}}'
report:
  steps: true
steps:
  - type: foreach
    items: '{{records}}'
    as: record
    collect: '{{results.outcome}}'
    save_as: collected
    steps:
      - type: evaluate
        args: '{{record}}'
        script: 'record => ({id: record.id, category: "processed"})'
        save_as: outcome
  - type: assert
    condition: {eq: ['{{results.collected.iterations}}', 2]}
    message: Unexpected collection size
```

Run with --json for a single structured report on stdout (logs on stderr). Collection and export are explicit; failed business classifications require an assertion to fail execution. Detailed trace outputs are opt-in and bounded; explicit exports remain complete.

## Common Selector Patterns

```yaml
# By ID
selector: "#submit-button"

# By role (most reliable for interactive elements)
selector: "role=button[name='Submit']"
selector: "role=textbox[name='Email']"
selector: "role=link[name='Sign in']"

# By text
selector: "text=Accept all cookies"

# By data-test attribute (best for test automation)
selector: "[data-testid='submit-btn']"
selector: "[data-test='login-form']"

# By CSS
selector: "button[type='submit']"
selector: "input[name='email']"
selector: ".modal .close-button"
```
