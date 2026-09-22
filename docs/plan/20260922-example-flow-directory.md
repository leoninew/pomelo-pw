# 示例 Flow 目录重组计划
最后修改时间: 2026-09-22 12:38:38

## Review status

Accepted

## Implementation steps

1. 将 `flows/` 下的示例迁移为 `example/`，以业务场景重新命名并归入 `public/`、`interactions/` 和 `state/`。
2. 用公开页面流程覆盖导航、等待、条件、循环、数据驱动、脚本执行和视觉基线；用公开演示站点覆盖下拉、勾选、输入、键盘和重试。
3. 新增 `example/README.md`，列出每个 flow 的能力、是否可直接运行、依赖关系和命令示例。
4. 更新 `pomelo-pw list` 以递归展示 `example/` 目录，并添加针对嵌套 flow 的 CLI 测试。
5. 更新当前 README、设计文档和 agent skill 的目录引用。

## Files to change

- `flows/` 迁移至 `example/`
- `example/README.md`
- `src/pomelo_pw/cli.py`
- `tests/test_cli.py`
- `README.md`
- `README_CN.md`
- `docs/DESIGN.md`
- `plugins/pomelo-pw/skills/pomelo-pw/SKILL.md`

## Verification plan

- 对 `example/` 下每份 YAML 运行 `pomelo-pw validate`。
- 运行 CLI 目录发现测试。
- 运行项目既有的格式、lint、类型检查与单元测试。

## Assumptions

`example/` 是仓库级示例目录，不影响用户自行在任意路径运行 flow 的能力；`pomelo-pw list` 的递归列举仅覆盖该示例目录。

## Risks

- 重命名会使外部引用旧 `flows/` 路径的用户需要更新调用命令。
- 公共页面 DOM 可能变化，因此业务模板必须通过 CLI 变量和选择器变量适配。

## Rollback

将 `example/` 恢复为 `flows/` 并撤销 `pomelo-pw list`、文档链接和目录引用修改。
