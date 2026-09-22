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
| `public/visual-regression.yaml` | Screenshot baseline comparison | Yes, with Pillow |

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
