# 统一 Playwright 浏览器生命周期验证
最后修改时间: 2026-07-11 15:01:12

Review status: Accepted

## Requirement alignment

已按 `docs/requirement/20260711-unify-playwright-browser-lifecycle.md` 核对。共享 browser/context 创建、三入口配置一致性、显式资源清理和 CLI 兼容性均已实现。

## Spec alignment

不适用（light / 轻量模式未创建 Spec）。

## Plan alignment

不适用（light / 轻量模式按 Requirement 实现）。

## Actual diff summary

- 新增 `src/pomelo_pw/browser.py`，提供 `BrowserLifecycle`，统一 Chromium launch options 与 viewport context 创建。
- `src/pomelo_pw/executor.py` 改为委托共享生命周期；browser 和 context 均在 `finally` 中释放，且保留 `_launch_browser()` 测试 seam。
- `src/pomelo_pw/explorer.py`、`src/pomelo_pw/recorder.py` 改为复用共享配置与生命周期，并显式按 context → browser 清理。
- 新增共享组件、交互入口、CLI 分发和异常清理的 mock 回归测试。

## Expected vs actual changed files

| 预期文件 | 实际结果 |
| --- | --- |
| `src/pomelo_pw/browser.py` | 已新增 |
| `src/pomelo_pw/executor.py` | 已修改 |
| `src/pomelo_pw/explorer.py` | 已修改 |
| `src/pomelo_pw/recorder.py` | 已修改 |
| `tests/test_browser.py` | 已新增 |
| `tests/test_explorer.py` | 已新增 |
| `tests/test_recorder.py` | 已新增 |
| `tests/test_cli.py` | 已新增 |
| `tests/test_data_driven.py` | 未修改；保留现有 patch seam，验证通过 |

## Acceptance checklist

- [x] 三个浏览器入口复用统一 launch/context 创建逻辑。
- [x] `headless`、`timeout`、`slow_mo` 被统一传递；`executable_path` 仅在存在时传递。
- [x] 三个入口均使用配置 viewport。
- [x] 未传 `--headless` 时仍保持可见浏览器默认行为。
- [x] 成功、无录制步骤、KeyboardInterrupt、页面初始化失败和 executor page 创建失败路径均覆盖资源清理。

## Test results

| 命令 | 结果 |
| --- | --- |
| `uv run pytest tests/test_browser.py tests/test_explorer.py tests/test_recorder.py tests/test_cli.py tests/test_data_driven.py` | 17 passed |
| `uv run pytest` | 134 passed |
| `uv run ruff check src tests` | passed |
| `uv run ruff format --check src tests` | passed |
| `uv run mypy src` | passed |

## Scope deviation

无。未修改 CLI 语法、配置 schema 或业务步骤行为。

## Risks

- `git diff --check` 对 `explorer.py`、`recorder.py` 的新增 CRLF 行报告 trailing whitespace；Ruff format 检查已通过，说明为换行符差异而非代码格式问题。
- 未执行真实 Playwright 浏览器手工 smoke test；自动化 mock 测试已覆盖配置传递和关键资源释放路径。

## Incomplete items

无。

## Conclusion

交付满足 Requirement 的范围和验收标准。自动化测试、lint、format 和类型检查全部通过；可以进入人工浏览器 smoke test 或代码审阅。
