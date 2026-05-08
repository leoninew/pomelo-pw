# Pomelo PW Flow Templates

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
    condition: "element_visible: .cookie-banner"
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
    condition: "url_contains: /login"
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
    while: "element_visible: .load-more-button"
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
    condition: "element_exists: .error-banner"
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
