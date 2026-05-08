# Changelog

All notable changes to Pomelo PW will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

[0.2.0]: https://github.com/yourusername/pomelo-pw/compare/v0.1.1...v0.2.0
[0.1.1]: https://github.com/yourusername/pomelo-pw/releases/tag/v0.1.1
