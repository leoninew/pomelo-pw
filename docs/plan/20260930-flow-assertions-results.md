# T08 断言与结构化执行结果实施计划
最后修改时间: 2026-10-02 12:13:51

## Review status

Accepted

## Flow mode and stage

标准模式 / standard，Intent/Plan 已接受，Implementation 已交付至可用状态。用户要求按顺序推进，沿用无未决事项时开始实现的授权。T07 已提交为 ee2b301，验收已接受；当前停止供用户自行测试，不自动进入正式 Verification 或 T09。

## Intent basis

依据 [T08 Intent](../intent/20260930-flow-assertions-results.md)，复用运行时 JSON、统一条件、foreach 和 poll 的预算及定位，不增加业务状态机或通用聚合语言。

## Proposed contracts

```yaml
outputs:
  outcomes: '{{results.collected.items}}'
  summary: '{{results.summary}}'
report:
  steps: true
  max_steps: 1000
  include_outputs: false
steps:
  - type: foreach
    items: '{{records}}'
    as: record
    collect: '{{results.outcome}}'
    max_collect_items: 1000
    max_collect_bytes: 1048576
    save_as: collected
    steps:
      - type: evaluate
        args: '{{record}}'
        script: 'record => ({id: record.id, category: record.category})'
        save_as: outcome
  - type: assert
    condition: {eq: ['{{results.summary.failed}}', 0]}
    message: 'Some records failed'
```

- assert 必需 condition，复用 T02 的静态校验、实时页面探测、JSON 类型比较与短路。message 为非空字符串，默认 Assertion failed，支持类型化引用；condition 保持原文，在执行时解析。仅条件 false 抛出 AssertionFailed；条件本身无法求值是执行错误。失败包含说明、条件及访问过的引用/操作数值；不重新访问短路节点或重跑谓词，不增加等待或隐式重试。
- 条件 evaluator 只在断言请求时收集观察值，用同一份输入/结果快照；现有 if/while/wait 行为保持原契约。
- foreach 新增可选 collect JSON 表达值，循环体完整成功后在该项作用域中解析；每项恰好收集一次。省略 collect 只遍历，不保存逐项业务数据。输出统一为 {iterations, items}，可 save_as；items 为显式收集的有序数组，空循环为 []。失败不发布部分集合。
- max_collect_items 默认 1000，max_collect_bytes 默认 1048576，均为正整数且只用于 collect。条数上限在下一项开始前检查，字节上限在该项完成后按 JSON UTF-8 字节检查；超过上限明确失败，不截断业务数据，不重放已经完成的循环体。collect 保持原文以延迟解析，引用数据不再解释为模板。
- flow.outputs 为 ASCII 标识符键的 JSON 对象，在步骤结束后使用固定运行时快照逐项解析，仅导出明确声明的值。缺失或非法引用作为 output 错误记录并使运行失败，其他可导出字段仍保留；不自动导出所有 inputs/results 或 data 行输入。
- run/API 采用唯一新结构：schema_version=1、status=passed/failed、flow、duration_ms、outputs、steps={total,executed,completed}、trace、errors、errors_dropped、artifacts={screenshots}、rows、row_summary。steps 为顶层执行计数，trace 用于嵌套细节；status 是执行状态，与输出中的业务分类无隐式关系。
- 错误统一包含 path/type/kind/error_type/message/diagnostics/evidence，从异常因果链保留最深步骤位置；assertion、timeout、exhausted、poll_failure、collection_limit、output 和普通 step 错误可区分。continue 保留多次失败，后续成功不覆盖失败状态。截图/HTML 证据归入 evidence，截图列表归入 artifacts；不保留 success/failed_step/steps_executed 等旧字段副本。
- data-driven 每行输出同样的运行报告，并带 label/index；rows 数组保留实际执行行，row_summary 为 total/executed/passed/failed。顶层 steps/artifacts/errors 汇总行事实，命名 outputs 在各行独立导出，不自动合并业务数据或公开 row_data。
- report 为静态配置：steps 默认 false；max_steps 默认 1000；include_outputs 默认 false，开启需 steps=true；max_value_bytes 默认 16384；max_errors 默认 100。详细 trace 记录 path/type/status/duration_ms，默认不含操作输出；达到条数上限继续执行并统计 dropped。大输出/诊断明确标记省略及字节数，不无条件保存每轮响应。错误信息及数量亦有边界，丢弃详情不改变失败状态。显式业务 exports 不静默截断，集合由自身上限约束。
- 顶层、分支、foreach、loop 和 poll 使用现有路径规则（index-N/iter-N/attempt-N），trace 按开始顺序记录，控制步骤覆盖整个控制体耗时。重试只记录单次逻辑步骤的最终状态，继续使用现有重试边界；poll 迟到操作不发布结果或完成记录。
- CLI run --json 将执行日志和 console 消息写到 stderr，stdout 仅含一个可直接 JSON 解析的报告。成功退出 0，失败退出 1；加载/校验/启动错误也使用新报告。普通文本摘要读取新结构，validate --json 保留独立的 valid/errors 校验契约。
- 不实现旧输出适配、追加写入全局结果的 step、通用汇总语言或报告平台；业务分类与成功政策仍由 flow 显式定义和断言。

## Implementation steps

1. 添加断言步骤，并给共享条件入口增加可选观察值收集，不改变非断言调用语义。
2. 实现 foreach 的延迟 collect、数量/字节边界与公开输出。
3. 添加有界执行报告模块，接入各层 StepContext/执行器、导出、异常定位、数据行汇总及 CLI 新结构。
4. 迁移仓库内 CLI/API 报告消费者与说明，增加针对性结果/断言/收集回归和离线示例。
5. 只运行相关测试、变更 Python 文件静态检查、离线最小 CLI 集成；达到可用状态后记录交付并停止。

## Files to change

- src/pomelo_pw/reporting.py、conditions.py、executor.py、cli.py。
- steps/assertion.py、steps/base.py、steps/foreach.py、steps/__init__.py。
- tests/test_assertion.py、tests/test_reporting.py；现有 CLI/data-driven/poll/foreach 及受影响执行器/条件测试按新契约迁移。
- example/public/flow-assertions-results.yaml、example/README.md。
- README.md、README_CN.md、docs/DESIGN.md、本地插件 SKILL.md/templates.md。
- T08 Intent/Plan、系列入口及 T07 Intent/Plan/Verification 接受记录。

## Verification plan

开发阶段仅针对性回归：断言布尔类型、短路与观察值、嵌套失败定位；逐项收集作用域/快照/边界/不重放；命名导出与缺失失败；有界轨迹与 continue 多错误；poll 成功/超时/读取失败；行隔离与汇总；CLI stdout 单一 JSON、stderr 日志、成功/失败退出码和失败证据。离线示例与少量受控失败场景作为最小集成，不执行全量或真实业务。

正式 Verification 在用户查看本次交付后决定，不由开发检查自动替代。

## Blockers and assumptions

暂无必须由用户决定的未决事项。新结构为明确破坏性变更；仓库消费者随本项迁移，外部调用方按文档迁移。业务结果只在 collect/outputs 声明后保留，用户负责选择导出字段与允许的失败政策。

## Risks

- 报告接入跨多个执行控制入口，需回归原有重试、作用域、poll 预算与失败清除，避免结果记录造成操作重放。
- 导出在结束时读取；失败后某些绑定可能缺失，导出会追加明确 output 错误，不能将该错误误认为初始原因。
- 轨迹与诊断受限，必要业务数据应显式收集/导出；业务集合达到上限会失败，已经完成的副作用无法撤销。
- 新报告及纯 stdout JSON 需要外部消费者迁移，不提供旧字段或混合日志的适配。

## Rollback

按本项 diff 移除断言、收集及报告接入，恢复相关仓库消费者；不新增旧契约兼容分支，不执行 Git 写操作。

## Implementation handoff

- 新增 assertion.py/reporting.py：断言复用类型化条件与短路，失败保留访问值及节点结果；报告包含唯一新结构、错误因果链定位、预算和省略标记。
- foreach 在每项完整成功后延迟 collect，输出 {iterations,items}；数量/UTF-8 字节超限明确失败，不重试控制体、不发布部分集合。
- 执行器记录逻辑步骤最终状态、完整控制体耗时、continue 多错误与失败证据，最后以固定快照逐项导出；data 行独立报告，顶层有界合并并保留行定位。
- CLI/API 使用 schema_version=1 与 status，不保留旧字段；run --json 的日志和 console 写 stderr，stdout 为唯一 JSON，成功/失败退出 0/1。缺失文件也进入统一加载错误报告。validate --json 保持独立契约。
- 仓库内报告消费者、英文/中文 README、DESIGN、本地插件说明和模板已迁移；新增离线 example/public/flow-assertions-results.yaml。没有修改 dist 材料脚本或用户级插件。
- 8 个相关测试文件 250 项通过：assertion/reporting/foreach/poll/CLI/data-driven/executor control/conditions。收尾修正 poll 因果链错误类型后，只重跑报告模块 15 项，全部通过；未跑全量或覆盖率。
- 14 个变更 Python 文件 ruff lint/format/mypy 通过；报告模块收尾后另做 2 文件 mypy。新 YAML validate --json 通过。
- 本机 Chrome 真实 CLI 最小集成通过：成功 6/6 顶层步骤、12 条轨迹，导出 3 条结果及 total=3/processed=2/skipped=1/failed=0；受控断言失败退出 1，保留完整 exports、访问值、截图和 HTML，顶层 executed=5/completed=4；缺失文件失败退出 1。各场景 stdout 均可直接 JSON 解析，日志在 stderr。
- 试跑发现示例的 about:blank 导航不满足既有 navigate 的 HTTP(S) 契约；移除多余导航，直接在新页面构建离线 DOM 后重跑通过。没有扩展 navigate 范围。
- 当前无必须修复的遗留问题。外部消费者需要迁移新报告结构，显式集合达到上限会失败且已完成操作不能撤销。未测试真实材料业务，未正式 Verification、暂存/提交或推进 T09；当前停止供用户自行测试。

## User review notes

- 用户要求按顺序推进，沿用无未决事项时开始实现与不做兼容适配的授权。
- 可用后停止供用户自行测试；仅针对性回归与最小集成，不自动提交、进入 Verification 或推进 T09。
