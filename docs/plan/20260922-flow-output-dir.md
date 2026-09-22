# Flow YAML 输出目录支持实施计划
最后修改时间: 2026-09-22 10:38:14

## Review status

Accepted

## Implementation steps

1. 在执行器校验 flow 顶层 `output_dir`，并在合并 flow 变量与 CLI 变量后统一解析输出根目录。
2. 调整 CLI：仅在用户传入 `-o/--output` 时传递显式目录，避免默认值覆盖 YAML 声明。
3. 添加聚焦测试，覆盖 YAML 路径、变量替换、CLI 优先级和非法值校验。
4. 更新中英文 README、内置 skill 与设计文档，说明 YAML 写法、优先级和相对路径规则。

## Files to change

- `src/pomelo_pw/cli.py`
- `src/pomelo_pw/executor.py`
- `tests/test_cli.py`
- `tests/test_executor.py`
- `README.md`
- `README_CN.md`
- `plugins/pomelo-pw/skills/pomelo-pw/SKILL.md`
- `docs/DESIGN.md`

## Verification plan

验证阶段经用户明确授权后，运行聚焦 pytest、Ruff format/check 与 mypy，并检查 CLI `validate` 对 `output_dir` 的校验结果。

## Assumptions

`output_dir` 是 flow 顶层字段；其变量替换使用现有 `{{name}}` 规则，CLI `--var` 覆盖 flow `variables` 中的同名值。

## Risks

相对路径以 `work_dir` 解析，不会以 YAML 文件所在目录解析；该规则与现有 CLI 相对 `-o` 目录一致。

## Rollback

移除 YAML `output_dir` 解析和相关文档后，CLI 可恢复为始终传递基于 flow 文件名的默认输出目录。

## User review notes

用户明确要求先完成 Pomelo PW 实现，以便后续业务 flow 将产物输出到指定目录。
