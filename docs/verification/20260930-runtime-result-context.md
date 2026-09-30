# T01 运行时结果与类型化数据引用验证
最后修改时间: 2026-09-30 16:05:52

## Review status

Accepted

## Flow mode and stage

标准模式 / standard，验证阶段 / Verification 已接受。用户已明确“T01 测试都已经通过了”，并要求推进下一个任务。

## Basis

- [Intent](../intent/20260930-runtime-result-context.md)：Accepted。
- [Plan](../plan/20260930-runtime-result-context.md)：Accepted。
- 本任务不创建 Spec 文档；标准模式按 Intent 和 Plan 核对。
- 本次验证限定 T01 与用户追加的教材脚本迁移，未运行真实教材解析。验收通过后由 T02 独立继续。

## Verification scope

核对实际 diff、验收标准、已有测试及质量检查，并运行代表性 example。浏览器产物存放在 `output/verification-t01/20260930140734`，不覆盖示例既有产物。

以下结果归档自 T01 已执行的检查，本次文档收尾不重复运行产品测试。用户追加“只进行针对性的测试，不进行全量测试”后，仅执行 CLI 聚焦回归、离线浏览器契约检查及相关文件的质量检查。

## Intent, spec and plan alignment

- Intent 对齐：JSON 结果保存、类型化引用、嵌套作用域、数据行隔离和结构化脚本参数已交付；旧接口直接移除，仓库调用同步迁移。
- Spec 对齐：不适用，标准模式未创建 Spec。
- Plan 对齐：按计划建立数据底座，未提前增加数据条件、集合遍历、等待、请求或报告能力。
- 用户追加范围：生成 `dist/material-parse-all-p0.yaml`，使用 T01 契约迁移现有教材脚本。分页、业务规则和轮询仍使用函数脚本，等待后续能力替换。

## Actual diff and scope

代码交付已包含在本地提交 `1af83db`（`feat(runtime): add typed inputs and step results`）中。本记录不执行暂存或提交。

| 范围 | 预期与实际 |
| --- | --- |
| `runtime.py`、`substitution.py`、`executor.py`、`steps/base.py` | 按计划实现运行时快照、统一引用、作用域、延迟子步骤解析和递归校验 |
| `steps/evaluate.py` | 按计划改为函数接口、原文源码和结构化 args，移除模块脚本适配 |
| 条件、循环、截图及状态步骤 | 按计划迁移 control/diagnostics，未扩展其产品能力 |
| 单元测试、README、DESIGN、example、插件说明 | 按计划迁移相关契约和示例 |
| `tests/test_browser.py` | 必要追加：迁移私有 `_run_once` 调用签名 |
| `src/pomelo_pw/cli.py`、`tests/test_cli.py` | 验证发现 data-driven 成功后汇总抛出 `KeyError: 'steps_executed'`，追加按行汇总的最小修复与回归 |
| `dist/material-parse-all-p0.yaml` | 用户追加的迁移产物，位于 Git 忽略目录；原文件保留 |

未修改依赖、锁文件、浏览器配置、发布入口或相邻业务仓库。

## Acceptance checklist

- [x] JSON 标量、对象和数组保留类型；无输出与 null 区分，非法 JSON 返回值被拒绝。
- [x] 完整引用、字段和下标遵循统一规则；缺失和非法路径报错，结果中的模板文本保持数据原样。
- [x] 成功结果可读取和覆盖；失败使旧绑定失效，重试只发布最终成功输出。
- [x] 输入优先级、局部作用域和嵌套执行保持一致，子步骤读取前一步刚产生的结果。
- [x] data-driven 行隔离运行结果，三行真实示例及 CLI 汇总通过。
- [x] 同步和 async 函数通过 args 接收结构化数据；未提供 args 与显式 null 区分。
- [x] 旧裸模块脚本不再适配；监听器在成功与失败时均清理。
- [x] 递归校验定位嵌套步骤，启动前 output_dir 不允许引用结果。
- [x] 用户已确认 T01 测试通过，可作为 T02 的前置依赖。

## Test results

| 检查 | 结果与适用范围 |
| --- | --- |
| 历史 `pytest` | 252 passed；执行于用户提出仅针对性测试及 CLI 汇总修复之前，不代表修复后的全量结果 |
| 历史 Ruff format / lint、mypy | 通过；format 检查 50 个文件，mypy 检查 51 个文件 |
| CLI 修复后 `pytest tests/test_cli.py` | 9 passed |
| CLI 修复后聚焦 Ruff / mypy | `src/pomelo_pw/cli.py`、`tests/test_cli.py` 共 2 个文件通过 |
| 离线真实 Chrome 契约检查 | 6 组检查通过，使用 `about:blank`，见下文 |
| YAML 静态校验 | 14 个 example 及教材 P0 文件，共 15 个通过 |
| 教材迁移离线浏览器 fixture | 正常、空清单和轮询耗尽场景通过；覆盖翻页、跳过、已有任务及瞬时失败重试 |
| 插件包 check | 已通过，未执行 plugin apply |
| 差异空白检查 | 使用 CRLF 感知的 `git diff --check` 通过 |

离线 Chrome 的 6 组检查覆盖：参数缺省与 null、async 参数及特殊字符、原文源码和 console、结果快照与不透明字符串、嵌套循环覆盖绑定、失败后重试发布，以及非法返回/旧脚本失败时绑定和监听器清理。部分相关行为合并在同一组检查中。

## Browser examples

13 个不同 example 已通过真实浏览器试跑；初次 data-driven 运行完成三行后出现 CLI 汇总错误，修复后的复跑通过。

| 产物目录 | 通过的 example |
| --- | --- |
| `basic` | `runtime-results`、`scripted-page-check`、`page-smoke` |
| `control`、`rows-recheck` | `conditional-content`、`scroll-loop`、`data-driven-pages` |
| `interactions` | `form-controls`、`hover-reveal`、`dynamic-content-retry` |
| `readiness` | `spa-readiness`、`incremental-content` |
| `state` | `save-browser-state`、`reuse-browser-state` |

`page-smoke` 通过变量覆盖使用 The Internet 公共测试站点。状态保存/加载共 5 个 Cookie、0 个 localStorage 条目；`runtime-results` 不生成截图，没有同名产物子目录是预期行为。已查看 `basic/scripted-page-check/evidence.png`，页面实际渲染正常。

## Risks and incomplete coverage

- 真实业务登录及教材批量解析未执行，离线 fixture 不能证明业务服务的实际状态与认证行为。
- `visual-regression.yaml` 仅静态校验；本机缺少可选 Pillow 依赖，未试跑图像比较，也未安装额外依赖。
- 控制体整体重试、循环耗尽和统一报告分别由 T03、T05、T08 处理，属于后续任务范围。
- 外部 flow 需按新数据和函数契约迁移，不提供兼容适配。

上述未覆盖项不阻塞 T01 验收；不得据此声称真实教材流程或整个 P0/P1 系列已验收。

## Conclusion and user review

T01 已达到可用状态，相关契约与示例验证通过。用户明确“T01 测试都已经通过了”，据此将 Verification 标记为 Accepted，后续进入 T02 Plan；不重复执行 T01 测试。
