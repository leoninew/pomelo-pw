# Pomelo PW Flow Templates

## Quick Templates

### 1. Simple Navigation and Screenshot

```yaml
name: quick-capture
description: Navigate to a URL and take a screenshot

variables:
  url: "https://example.com"

steps:
  - type: navigate
    url: "${url}"

  - type: screenshot
    file: "capture.png"
```

### 2. Login Flow

```yaml
name: login-test
description: Test login functionality

variables:
  base_url: "https://example.com"
  username: "user@example.com"
  password: "password123"

steps:
  - type: navigate
    url: "${base_url}/login"

  - type: screenshot
    file: "01-login-page.png"

  - type: fill
    selector: "input[name='email']"
    value: "${username}"

  - type: fill
    selector: "input[name='password']"
    value: "${password}"

  - type: click
    selector: "button[type='submit']"

  - type: wait
    selector: ".dashboard"
    timeout: 5000

  - type: screenshot
    file: "02-logged-in.png"
```

### 3. Form Submission

```yaml
name: form-submit
description: Fill and submit a form

variables:
  form_url: "https://example.com/contact"

steps:
  - type: navigate
    url: "${form_url}"

  - type: fill
    selector: "#name"
    value: "John Doe"

  - type: fill
    selector: "#email"
    value: "john@example.com"

  - type: fill
    selector: "#message"
    value: "This is a test message"

  - type: check
    selector: "#agree-terms"

  - type: click
    selector: "button[type='submit']"

  - type: wait
    selector: ".success-message"

  - type: screenshot
    file: "form-submitted.png"
```

### 4. Multi-page Navigation

```yaml
name: multi-page-test
description: Navigate through multiple pages

variables:
  base_url: "https://example.com"

steps:
  - type: navigate
    url: "${base_url}"

  - type: screenshot
    file: "01-home.png"

  - type: click
    selector: "a[href='/about']"

  - type: wait
    url: "/about"

  - type: screenshot
    file: "02-about.png"

  - type: click
    selector: "a[href='/contact']"

  - type: wait
    url: "/contact"

  - type: screenshot
    file: "03-contact.png"
```

### 5. Responsive Testing

```yaml
name: responsive-test
description: Test responsive design at different viewport sizes

variables:
  url: "https://example.com"

steps:
  - type: navigate
    url: "${url}"

  - type: set-viewport
    width: 1920
    height: 1080

  - type: screenshot
    file: "desktop.png"

  - type: set-viewport
    width: 768
    height: 1024

  - type: screenshot
    file: "tablet.png"

  - type: set-viewport
    width: 375
    height: 667

  - type: screenshot
    file: "mobile.png"
```

### 6. Scroll and Capture

```yaml
name: scroll-capture
description: Scroll through page and capture sections

variables:
  url: "https://example.com"

steps:
  - type: navigate
    url: "${url}"

  - type: screenshot
    file: "01-top.png"

  - type: scroll
    direction: down
    distance: 500

  - type: screenshot
    file: "02-middle.png"

  - type: scroll
    direction: down
    distance: 500

  - type: screenshot
    file: "03-bottom.png"
```

### 7. Dropdown and Selection

```yaml
name: dropdown-test
description: Test dropdown selections

variables:
  url: "https://example.com/form"

steps:
  - type: navigate
    url: "${url}"

  - type: select
    selector: "#country"
    value: "United States"

  - type: select
    selector: "#state"
    value: "California"

  - type: screenshot
    file: "selections.png"
```

### 8. JavaScript Evaluation

```yaml
name: js-eval-test
description: Execute JavaScript on the page

variables:
  url: "https://example.com"

steps:
  - type: navigate
    url: "${url}"

  # Direct code (auto-wrapped)
  - type: evaluate
    script: "document.body.style.backgroundColor = 'lightblue'"

  - type: screenshot
    file: "modified-page.png"

  # Function expression
  - type: evaluate
    script: |
      () => {
        const title = document.title;
        const url = window.location.href;
        return { title, url };
      }

  # Direct code with return
  - type: evaluate
    script: "return document.title"
```

### 9. Wait Step Examples

```yaml
name: wait-examples
description: Different ways to use the wait step

steps:
  - type: navigate
    url: "https://example.com"

  # Wait for element to appear (with timeout)
  - type: wait
    selector: ".loading-spinner"
    timeout: 5000

  # Wait for URL change (with timeout)
  - type: wait
    url: "/dashboard"
    timeout: 10000

  # Fixed delay (use sparingly)
  - type: wait
    delay: 2000

  # Wait for page load
  - type: wait
    for: "load"

  # Wait for network idle
  - type: wait
    for: "networkidle"
```

## Usage Tips

1. **Copy a template** that matches your use case
2. **Modify variables** to match your target site
3. **Adjust selectors** to match your HTML structure
4. **Save as YAML** file (e.g., `my-flow.yaml`)
5. **Run with**: `pomelo-pw run my-flow.yaml`

## Wait Step Parameters

- `timeout`: Maximum time to wait for a condition (default: 30000ms)
  - Used with `selector`, `url`, or `for` parameters
- `delay`: Fixed delay in milliseconds
  - Use only when necessary (prefer condition-based waits)

## Common Selectors

- By ID: `#element-id`
- By class: `.class-name`
- By attribute: `[name='field-name']`
- By type: `button[type='submit']`
- By text: `text=Click me`
- By role: `role=button[name='Submit']`
