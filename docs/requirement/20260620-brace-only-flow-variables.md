# 统一 Flow 变量语法为双花括号
最后修改时间: 2026-06-20 22:43:18

Review status: Accepted

## Background

Pomelo PW 当前同时支持 `{{ var }}` 和 `${var}` 两种 flow 变量替换语法。`${var}` 与 JavaScript template literal、Shell 变量等语法冲突，尤其在 `type: evaluate` 的 JavaScript 脚本中容易把 `${last}`、`${userId}` 等 JS 运行时变量误识别为 flow 变量。

## Goal

- 将 flow 变量语法统一为 `{{ var }}`。
- 移除 `${var}` 兼容逻辑，不做向后兼容。
- 让 JavaScript 中的 template literal `${...}` 可以自然使用，不被 Pomelo PW 变量替换处理。

## Non-goal

- 不保留 `${var}` 的兼容 fallback。
- 不为旧语法提供迁移 shim 或 warning-only 模式。
- 不修改 evaluate 顶层 await 的既有实现目标。

## User scenarios

- 用户在 flow 中写 `{{ api_token }}`，Pomelo PW 替换为对应 flow 变量值。
- 用户在 evaluate 脚本中写 `` `/api/users/${userId}` ``，`${userId}` 保持为 JavaScript 代码的一部分。
- 旧 flow 中的 `${api_token}` 不再被 Pomelo PW 替换。

## Acceptance

- 变量替换只处理 `{{ var }}` 语法。
- `${var}` 在任意字符串中保持原样。
- 相关测试覆盖 `{{ var }}` 替换和 `${var}` 保留行为。
- 文档或示例不再推荐 `${var}` 作为变量语法。

## Open questions

暂无需要用户确认的未决事项。

## Decisions

- 用户明确要求：实现该要求，不向后兼容。
- 本次采用轻量模式 / light，Requirement 直接标记为 Accepted 并进入 Implementation。

## Risk

- 旧 flow 如果仍使用 `${var}`，升级后不会再替换，需要迁移到 `{{ var }}`。
