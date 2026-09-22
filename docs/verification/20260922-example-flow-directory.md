# 示例 Flow 目录重组验证
最后修改时间: 2026-09-22 12:58:59

## Review status

Accepted

## Intent alignment

实现将仓库级示例目录从 `flows/` 重组为 `example/`，移除了故意失败和虚构选择器的测试式样例，并以真实公开站点上的业务场景替代。所有 13 份 YAML 使用 `output_dir: "output"` 和 `headless: false`。

## Spec alignment

不适用。本功能采用 standard 模式，未创建独立 Spec。

## Plan alignment

- `public/` 覆盖页面冒烟、等待、条件、循环、数据驱动、脚本执行和视觉对比。
- `interactions/` 覆盖重试、表单控件、悬停和键盘操作。
- `state/` 覆盖浏览器状态保存与复用。
- `example/README.md` 说明运行方式、前置条件、状态依赖和公开站点限制。
- CLI `list` 递归发现 `example/` 下的 YAML，并有对应单元测试。

## Actual diff summary

- 删除原 `flows/` 下的 13 份 YAML 和 explorer/recorder 说明文档。
- 新增 `example/` 分类目录、13 份场景化 flow 与使用说明。
- 更新 CLI、README、设计文档和内置 skill 的目录引用。
- 更新 `select` 的测试契约，覆盖零基 `index` 选择方式。

## Expected vs actual changed files

| 预期范围 | 实际结果 |
| --- | --- |
| `flows/` 迁移至 `example/` | 已完成，旧目录内容已删除并由分类示例替代 |
| `example/README.md` | 已新增 |
| CLI 目录发现与测试 | 已更新 `src/pomelo_pw/cli.py` 和 `tests/test_cli.py` |
| 当前文档与 skill 引用 | 已更新 README、README_CN、DESIGN 和 skill |
| flow 能力测试 | 补充 `tests/test_steps.py` 对 `select.index` 的验证与执行断言 |

## Acceptance criteria

- [x] `flows/` 被 `example/` 替代。
- [x] 13 份 YAML 按 `public/`、`interactions/`、`state/` 分类。
- [x] 所有 flow 使用 `output_dir: "output"` 和有头默认模式。
- [x] `example/README.md` 包含场景、前置条件、运行命令与状态依赖。
- [x] `pomelo-pw list` 递归列出嵌套示例。
- [x] 当前 README、设计文档和 skill 指向 `example/`。

## Test results

- `pomelo-pw run example/public/page-smoke.yaml`：有头模式成功，5 步、2 张截图。
- 其余 12 份 flow 已按有头模式批量运行；`incremental-content` 和 `hover-reveal` 初次运行暴露变量与选择器问题，修正后分别成功完成 3 步和 4 步。
- `pomelo-pw validate`：13/13 flow 通过。
- `pomelo-pw list`：递归列出 13 份示例。
- `uv run --locked --no-sync ruff format --check src tests scripts`：通过。
- `uv run --locked --no-sync ruff check src tests scripts`：通过。
- `uv run --locked --no-sync mypy src tests scripts`：通过。
- `uv run --locked --no-sync pytest`：162 通过。
- `git diff --check`：通过。

## Missed or expanded scope

为使新表单示例中的 `select.index` 有执行级覆盖，更新了原有 `tests/test_steps.py` 的错误文本断言，并添加了索引选择的调用断言。这与已有功能保持一致，不改变运行时语义。

## Risks

公开站点和其 DOM 由第三方维护，未来可能影响示例运行；生产 flow 应通过变量替换 URL 和选择器。视觉对比示例依赖 Pillow。

## Incomplete items

无。

## Conclusion

验证通过。示例目录、真实有头运行、CLI 发现与项目质量门禁均满足计划和验收要求。
