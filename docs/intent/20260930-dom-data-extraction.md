# T07 DOM 集合与字段提取
最后修改时间: 2026-10-02 11:31:14

## Review status

Accepted

## Task metadata

- 流程：标准模式 / standard，Intent/Plan 已接受，Implementation 已交付并经用户自行试跑通过；Verification 检查完成且技术结论通过，文档 Draft 待用户审阅。
- 优先级：P1；依赖：[T01](20260930-runtime-result-context.md)；工作量：2-3 人日。
- 系列入口：[P0/P1 流程能力任务系列](20260930-p0-p1-flow-capabilities.md)。

## Background

material-parse-all 使用 querySelectorAll、行内查找和 textContent 组装记录对象。常见文本、属性及集合采集本可作为步骤输出，不应每个 flow 都重复编写 DOM 遍历。

## Goals

- 提取单元素文本、属性及元素集合的数据。
- 对行或重复项使用相对选择器映射字段，生成对象数组并绑定为运行时结果。
- 明确多匹配、缺失字段、空集合、文本清理和属性值的行为。

## Non-goals

- 不提供自动识别表头、业务字段或分页的万能采集器。
- 不增加复杂转换语言；格式转换和特殊计算可用短 evaluate 表达。
- 不同时点击或修改被提取的元素。

## User scenarios

- 从 table tbody tr 提取每条记录的名称、链接、文件与状态。
- 从分页页脚或输入框提取总数与页大小，供条件及遍历消费。

## Acceptance

- 支持文本、属性以及必要的表单值读取，输出类型和文本清理规则明确。
- 多元素提取按 DOM 顺序返回，字段映射在每个匹配元素内部执行。
- 必需字段缺失明确失败，可选字段使用明确的默认或 null 规则，不静默丢弃整条记录。
- 空集合可返回空数组；单元素模式的零匹配或多匹配行为可校验和说明。
- 原始 href 属性与解析后的绝对 URL 不混淆，输出模式明确。
- 结果可以直接被 T03 遍历，或被 T02/T08 检查，不需要 sessionStorage 中转。
- 提取与页面等待各有责任，调用方可先用 T04 等待稳定条件再取快照。

## Open questions

暂无必须由用户决定的未决事项。提取模式、字段映射语法及缺失值策略在 Plan 中确定，第一版限定为上述常见读取需求。

## Decisions

- 使用现有 Playwright 选择器与 Locator 能力，按调用方明确的字段映射读取数据。
- 专用分页封装不属于本系列；普通翻页通过提取、条件、循环和 click 组合表达。
- 采用唯一的新提取与输出契约，不提供旧 DOM 采集脚本的自动转换或结果格式适配。

## Risks

异步更新可能导致不同字段取自不同时刻的数据。集合提取需要可解释的快照边界，同时保留明确的页面等待契约。

## User review notes

- 用户要求提交当前任务并推进下一步，T06 已提交为 89eb7ef。沿用“没有未决事项就开始实现”，接受本项 Intent/Plan，开始实现。
- 第一版根选择器使用 Playwright Locator，字段为行内 CSS；同步快照读取，不自动等待、不添加转换语言或兼容适配。达到可用状态后停止供用户自行测试。
- 实现与开发检查完成，交付记录见 [T07 Plan](../plan/20260930-dom-data-extraction.md)。没有必须修复的遗留事项，不自动进入 T08。
- 用户反馈“All steps completed successfully”并明确要求完成本任务验证，进入 Verification；继续限定针对性回归和最小集成，完成后停在 T07。
- 本轮 95 项相关回归、5 个 Python 文件静态检查、离线正常与失败 CLI 场景通过，修复文本摘要丢失具体失败原因的问题。证据与范围见 [T07 Verification](../verification/20260930-dom-data-extraction.md)，不自动推进 T08。
