# 统一 Playwright 浏览器生命周期
最后修改时间: 2026-07-11 15:01:12

Review status: Accepted

## Background

`run`、`explore` 和 `record` 分别创建 Playwright browser/context。`explorer` 的局部修复仅部分复用了启动配置；`recorder` 未使用共享配置；资源关闭路径也不一致。

## Goal

让三个浏览器入口通过同一配置驱动的组件创建 Chromium 和 browser context，并保证 browser/context 在成功、受控失败和意外异常时可靠释放。

## Non-goal

- 不改变 CLI 命令、参数或默认可见浏览器行为。
- 不启用 `PlaywrightConfig.headless` 作为 CLI 默认值。
- 不修改配置模型、浏览器类型、导航策略、重试策略或页面默认超时语义。

## User scenarios

- 使用 `pomelo-pw run` 执行 flow 时，启动参数和 viewport 与全局 Playwright 配置一致。
- 使用 `pomelo-pw explore` 或 `pomelo-pw record` 时，同样使用配置的 executable path、timeout、slow motion 和 viewport。
- 用户中断交互命令或页面初始化失败时，context 和 browser 都会按 context → browser 顺序释放。

## Acceptance

- `run`、`explore`、`record` 复用统一的 browser/context 创建逻辑。
- 统一传递显式 `headless`、`timeout`、`slow_mo`，且只在配置存在时传递 `executable_path`。
- 每个入口使用配置 viewport 创建 context。
- 现有命令契约保持不变：未传 `--headless` 时浏览器可见。
- 覆盖共享配置、交互入口清理、CLI 分发与 executor 异常清理的回归测试通过。

## Open questions

不适用。

## Decisions

- 使用窄职责的 `BrowserLifecycle`，只承担 Chromium launch 和 context creation；业务流程、UI overlay 与 Click 命令仍由原模块负责。
- 保留 `FlowExecutor._launch_browser()` 作为委托包装层，以保持既有测试 patch seam。
- 在调用方使用 `finally` 管理资源，避免以新的执行框架替换既有控制流。

## Risk

- `git diff --check` 会将 `explorer.py`、`recorder.py` 的新增 CRLF 行报告为 trailing whitespace；Ruff 格式检查已通过，属于仓库换行符差异而非代码行末空格。
- 未进行真实浏览器手工 smoke test；自动化测试使用 mock 验证配置传递与清理语义。
