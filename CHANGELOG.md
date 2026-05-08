# Changelog

All notable changes to Pomelo PW will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.2] - 2025-01-XX

### Added
- **Enhanced SPA wait capabilities**: Multiple new wait conditions for modern web applications
  - `url_contains`: Wait for URL to contain a substring
  - `url_pattern`: Wait for URL to match a regex pattern
  - `network_idle`: Wait for network to be idle
  - `animation_stable`: Wait for CSS animations/transitions to complete
  - `route_stable`: Wait for URL to remain stable for a duration
  - `state` parameter for selector wait (visible, attached, detached, hidden)
- **Step-level retry**: Automatic retry mechanism for any step
  - `retry`: Number of retry attempts
  - `retry_delay`: Delay between retries in milliseconds
  - `retry_on`: List of error types to retry on (optional filter)
  - Detailed retry logging in verbose mode
- **Authentication state reuse**: Save and load browser state
  - `save-state`: Save cookies and localStorage to file
  - `load-state`: Load saved state to skip login
  - Useful for avoiding repeated logins across flows
- **Visual regression testing**: Screenshot baseline comparison
  - `baseline`: Compare screenshot with baseline image
  - `threshold`: Allowed difference percentage
  - `diff_output`: Save visual diff image (highlights differences in red)
  - `fail_on_diff`: Fail step if difference exceeds threshold
  - Requires Pillow (install with `pip install pomelo-pw[visual]`)

### Changed
- `wait` step now supports more flexible conditions for SPA applications
- All steps can now use retry parameters for improved reliability
- `screenshot` step now supports baseline comparison for visual regression testing

### Examples
```yaml
# Enhanced wait
- type: wait
  url_contains: "/dashboard"
  network_idle: true

# Step retry
- type: click
  selector: ".button"
  retry: 3
  retry_delay: 1000

# Save/load authentication
- type: save-state
  file: "auth.json"
- type: load-state
  file: "auth.json"

# Visual regression testing
- type: screenshot
  file: "page.png"
  baseline: "baseline.png"
  threshold: 0.05
  diff_output: "diff.png"
```

## [0.2.1] - 2025-01-XX

### Changed
- Default output directory from `./output/` to `./<flow-name>/`

## [0.2.0] - 2025-01-XX

### Added
- **Variable substitution with `{{ }}` syntax**: New recommended syntax that doesn't conflict with JavaScript template strings, shell variables, etc.
  - `{{ var }}` for flow variables (recommended)
  - `${ var }` still supported for backward compatibility
  - Smart strategy: if string contains `{{ }}`, only `{{ }}` is processed
- **Rich error context collection**: Automatic debugging information when steps fail
  - Error screenshot saved to `./flow/error-step-N.png`
  - HTML snapshot saved to `./flow/error-step-N.html`
  - Console errors (browser console messages)
  - Network errors (failed HTTP requests)
  - Current URL and visible page text
  - Full context available in JSON output

### Changed
- Default output directory changed from `./output/` to `./<flow-name>/`
  - Example: `my-flow.yaml` → `./my-flow/`
  - Output directory name derived from flow filename, not path
- CLI help text updated to show new default output behavior

### Fixed
- Variable substitution no longer conflicts with JavaScript template strings in `evaluate` step

## [0.1.1] - 2025-01-XX

### Added
- Initial release with core functionality
- 15+ built-in steps (navigate, screenshot, click, fill, type, etc.)
- YAML-based flow definition
- Variable substitution with `${ }` syntax
- Type-safe step validation
- Development mode with system Chrome detection

[0.2.2]: https://github.com/yourusername/pomelo-pw/compare/v0.2.1...v0.2.2
[0.2.1]: https://github.com/yourusername/pomelo-pw/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/yourusername/pomelo-pw/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/yourusername/pomelo-pw/releases/tag/v0.1.1
