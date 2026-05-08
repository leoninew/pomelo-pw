# Explorer and Recorder Usage Examples

## Interactive Page Explorer

Discover element selectors without guessing:

```bash
# Launch explorer
pomelo-pw explore https://example.com

# Explore in headless mode (for debugging)
pomelo-pw explore https://example.com --headless
```

### What You'll See

1. **Visual Overlay**: A green-bordered overlay appears in the top-right corner
2. **Hover Preview**: As you move your mouse, elements are highlighted and selectors appear
3. **Click to Copy**: Click any element to display all available selectors in your terminal

### Selector Priority

The explorer shows selectors in order of reliability:

1. **DATA-TEST**: `[data-test-id="submit-btn"]` - Most reliable
2. **ID**: `#submit-button` - Very reliable
3. **ROLE**: `role=button[name="Submit"]` - Semantic and accessible
4. **TEXT**: `text=Submit` - Simple but can break with text changes
5. **CLASS**: `.btn-primary` - Less reliable (styling changes)
6. **CSS**: `button.btn-primary` - More specific CSS
7. **XPATH**: `/html/body/div[1]/button[2]` - Least reliable (structure changes)

### Example Output

```
============================================================
Selected Element Selectors:
============================================================
ID           #email-input
ROLE         role=textbox[name="Email address"]
CLASS        .form-control
CSS          input.form-control
XPATH        //*[@id="email-input"]
============================================================
```

## Flow Recorder

Generate YAML flows from manual testing:

```bash
# Record a flow
pomelo-pw record https://example.com login-flow.yaml

# Record in headless mode
pomelo-pw record https://example.com login-flow.yaml --headless
```

### Recorded Actions

- **Click**: Any element click is recorded
- **Fill**: Text input in form fields
- **Press**: Enter key presses

### Example Recording Session

1. Navigate to https://example.com
2. Click "Login" button
3. Type "user@example.com" in email field
4. Type "password123" in password field
5. Press Enter
6. Press Ctrl+C to stop

### Generated Flow

```yaml
name: login-flow
description: Recorded flow from https://example.com
steps:
  - type: navigate
    url: https://example.com
  - type: click
    selector: role=button[name="Login"]
  - type: fill
    selector: "#email"
    value: user@example.com
  - type: fill
    selector: "#password"
    value: password123
  - type: press
    selector: "#password"
    key: Enter
```

## Tips

### Best Practices

1. **Use Explorer First**: Discover the best selectors before writing flows
2. **Prefer Semantic Selectors**: Use role and text selectors when possible
3. **Record for Prototyping**: Use recorder to quickly generate flows, then refine
4. **Combine Tools**: Use explorer to verify selectors in recorded flows

### Selector Selection Guide

- **data-test attributes**: Best for test automation (add them to your app)
- **id**: Great if IDs are stable and meaningful
- **role with name**: Excellent for accessibility and stability
- **text**: Good for buttons and links with stable text
- **class**: Avoid unless classes are semantic (not styling-based)
- **xpath**: Last resort, very brittle

### Common Workflows

#### Workflow 1: Discover and Write
1. Use `pomelo-pw explore` to find selectors
2. Manually write YAML flow with discovered selectors
3. Run with `pomelo-pw run`

#### Workflow 2: Record and Refine
1. Use `pomelo-pw record` to generate initial flow
2. Edit YAML to add variables, waits, assertions
3. Use `pomelo-pw explore` to improve selectors
4. Run with `pomelo-pw run`

#### Workflow 3: Debug Existing Flow
1. Flow fails with "element not found"
2. Use `pomelo-pw explore` on the page
3. Find the correct selector
4. Update flow YAML
5. Run again

## Limitations

### Explorer
- Only shows selectors for visible elements
- Cannot record complex interactions (drag-drop, hover menus)
- Requires JavaScript-enabled browser

### Recorder
- Only records click, fill, and Enter key
- Cannot record:
  - Hover actions
  - Right-click
  - Drag and drop
  - File uploads
  - Complex keyboard shortcuts
- Generated flows may need manual refinement

### Solutions
- Use recorder for basic flow structure
- Manually add complex steps (scroll, wait, evaluate)
- Use explorer to find selectors for manual steps
- Add variables and error handling manually
