# pomelo-pw Makefile 审查结果

最后修改时间: 2026-08-25 22:25:19

Review status: Accepted

## 结论

`FAIL`。当前 `install` 是 `.venv` 同步，`check` 默认修改源码，`release` 混合 plugin 同步和 pip editable 安装。

## 证据

- `Makefile:19-20` 使用 `uv sync --group dev`。
- `Makefile:25-28` 默认执行 `ruff check --fix` 和 `ruff format`。
- `Makefile:36-39` 在 release 中执行 plugin check、editable 安装、plugin apply。

## 目标规范

新增锁定依赖 `deps`；`install` 使用 `uv tool install --editable . --force` 并承载 agent plugin/skill 同步；`check [fix=1]` 直接执行只读/修正质量检查；`test [cov=1]` 组织覆盖率；`release` 只构建发布产物。
