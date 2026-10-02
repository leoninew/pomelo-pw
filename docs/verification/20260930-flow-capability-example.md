# T09 P0/P1 串联示例与能力验收验证
最后修改时间: 2026-10-02 13:49:45

## Review status

Draft

## Flow mode and stage

标准模式 / standard，Verification 技术检查已完成，结论通过。用户已查看 Implementation 交付及模拟场景限制，并要求“那推进完成吧”，据此进入正式验证。本项实现及限定范围技术验收已完成；Draft 表示本文件的用户审阅状态，不表示测试尚未执行。

## Intent alignment

按 [T09 Intent](../intent/20260930-flow-capability-example.md) 核对：使用 T01-T08 公开契约完成多页 DOM 采集、会话恢复、顺序处理、已有任务恢复、终态轮询、业务分类及报告输出。mixed/report、mixed/fail、empty、read-error、timeout 均得到预期结果；不依赖外部业务、不新增生产步骤或旧格式适配。

## Spec alignment

不适用，标准模式没有独立 Spec，组合方式与场景在 Plan 中定义。

## Plan alignment

按 [T09 Plan](../plan/20260930-flow-capability-example.md) 核对，实现与预期一致：标准库回环服务、每次登录独立会话、异步分页 ready 标记、快照采集、串行 POST/poll、审计事实、明确业务失败政策和有界报告。本轮没有发现需要修改执行器或步骤实现的缺口。

save-state 保存 Cookie，模拟 logout 清除客户端 Cookie，接口实际返回 401；load-state 后再次读取 manifest 成功。任务只在第二次查询达到终态，timeout 场景保持 pending；顺序审计独立于 flow 汇总，避免仅通过汇总数量推断无重放。

## Actual diff summary

- 新增回环 fixture、串联 flow 和聚焦测试；同步中英文 README、example 说明及仓库内 Agent skill。
- 更新 T09 Intent/Plan 与系列进度；本轮新增本 Verification，记录实际验收和限制。
- 本轮没有产品、fixture 或测试代码修复；只纠正验证命令的产物父目录准备，并更新过程文档。

## Expected vs actual changed files

| 范围 | Plan 预期 | 实际 |
| --- | --- | --- |
| 模拟页面/接口 | example/support/flow_capability_server.py | 一致 |
| 串联流程 | example/public/flow-capability-example.yaml | 一致 |
| 针对性检查 | tests/test_flow_capability_example.py | 一致 |
| 用户/Agent 说明 | README.md、README_CN.md、example/README.md、仓库内 SKILL.md | 一致 |
| 过程记录 | T09 Intent/Plan、系列入口 | 一致 |
| 正式验收 | 标准模式的本项 Verification | 新增本文件 |

相对于上一提交共 11 个文件属于本项交付；本轮只新增 Verification 并更新三个已有过程文档。没有改动 src、依赖/锁文件、dist 材料脚本、相邻项目或用户级插件。用户在本轮开始前已经暂存实现；本轮没有改动暂存区或创建提交。

## Acceptance criteria checklist

- [x] T01-T08 公开契约协同使用；正常、跳过、业务失败、读取失败和超时均可由受控场景复现。
- [x] 每页先确认路由、页码和 ready 标记再 extract；服务实际访问页码为 [1,2]，七条材料顺序与 fixture 一致，没有漏项或重复。
- [x] 顺序处理与无重放：已有任务仅恢复查询；fresh-ok 终态之后才提交 fresh-fail；读取失败/超时只提交 fresh-ok 一次，后续材料未提交，审计 violations 为空。
- [x] flow 没有 sessionStorage 状态机、手写 fetch/延时/轮询控制器；evaluate 仅做快照扁平化、结果投影、原因分类、计数和摘要渲染。模拟应用自己的 fetch 和异步刷新属于被测页面行为。
- [x] mixed 汇总为 total=7、ready=3、skipped=3、failed=1、submitted=2、resumed=1，逐条分类和原因一致；严格政策由 assert 使执行失败，并保留完整导出。
- [x] 局部绑定恢复、0/false/null JSON 和字面模板字符串均正确；失败包含集合索引/嵌套操作路径、轮询诊断和截图/HTML。
- [x] 五个 CLI 场景 stdout 都能直接解析为唯一 schema_version=1 JSON，日志在 stderr；预期成功退出 0，预期失败退出 1。空列表导出空数组和零汇总；未完成集合不发布部分结果。
- [x] 所有常规验证采用临时端口、本机 Chrome 和模拟接口；README、example 说明及 Agent skill 与实际参数/输出一致，没有新增适配分支。
- [x] 现行报告字段核对通过：旧名称只出现在“字段已移除”的说明、测试中的缺失断言和内部局部变量，不构成旧报告消费者或兼容契约。

## Test results

全部命令在 D:/SourceCodes/mywork/pomelo-pw 执行，沿用 Makefile 的 uv run --locked --no-sync 入口并收窄到本项文件。没有执行全量测试或覆盖率。

| 检查 | 本轮结果 |
| --- | --- |
| pytest tests/test_flow_capability_example.py -q，启用 POMELO_PW_INTEGRATION=1 | 两项快速检查通过；五个集成场景在 tmp_path 准备阶段报错，原因是自定义 basetemp 的父目录尚未创建 |
| 补建 output/verification-t09 后，pytest tests/test_flow_capability_example.py -q -k real_cli_scenarios --basetemp output/verification-t09/20261002-134345 | 5 passed、2 deselected，10.02s；仅重跑先前未启动的五个场景 |
| Ruff check：fixture 和新测试文件 | 通过，两个文件 |
| Ruff format --check：fixture 和新测试文件 | 通过，两个文件 |
| mypy --explicit-package-bases：fixture 和新测试文件 | 通过，两个文件，没有修改全局配置 |
| validate example/public/flow-capability-example.yaml --json | 退出 0，valid=true |
| 当前示例、测试、产品报告消费者及说明的旧字段静态核对 | 没有发现旧报告访问或兼容分支 |

两项快速检查与补跑的五项集成检查合计七项通过。首次错误来自本轮命令的目录准备，已实际修正并重跑，不能将首次执行记为七项通过。

| CLI 场景 | 退出码 / 状态 | 核验结果 |
| --- | --- | --- |
| mixed/report | 0 / passed | 顶层 19/19 完成，65 条轨迹；七条 inventory/outcomes、正确汇总和独立 audit 完整导出 |
| mixed/fail | 1 / failed | AssertionFailed，路径 18.1；完整 inventory/outcomes/summary/audit 保留，截图/HTML 存在 |
| empty/report | 0 / passed | 顶层 19/19 完成，22 条轨迹；空集合、零汇总、无任务提交 |
| read-error/report | 1 / failed | RequestStatusError，路径 14.index-4.1.1.3.attempt-1.1；首个新任务只提交一次、读取一次，inventory 保留 |
| timeout/report | 1 / failed | PollTimeoutError，路径 14.index-4.1.1.3.attempt-25.1；保留最近 pending 结果、时限及失败证据，下一项未提交 |

timeout 的实际尝试次数/阶段随耗时变化，检查只断言时限失败、最近结果与无重放；不把本次第 25 次请求视为固定契约。所有场景 trace.dropped=0，失败截图及 HTML 文件实际存在。已查看 mixed 的 results.png，表格、页码与汇总正常。

本轮证据位于 output/verification-t09/20261002-134345/，每个场景保留 report.json、execution.log 和相关截图/HTML；测试子进程及其临时服务均正常退出。此前供用户自行测试的预览服务 http://127.0.0.1:8767/（PID 29944）独立保留，本轮没有复用它作为测试服务。

## Missed or expanded scope

本轮没有增加功能范围或新测试矩阵。仅纠正验证产物目录的准备问题，不将其当作产品缺陷，也没有省略失败记录。没有运行真实材料解析、外部站点或用户级插件同步，没有执行 Git 写操作。

## Risks and incomplete items

- T09 限定范围内没有必须修复的遗留项或未完成技术检查。
- fixture 按查询次数推进任务，logout 只清除客户端 Cookie，不能替代外部认证过期、并发更新和真实异步服务时序的验证。
- 读取失败/超时后保留已完成的 inventory；未完成集合及后续汇总没有发布，缺失声明导出追加明确 output 错误。已经提交的任务不会被撤销。
- 外部调用方仍需迁移新契约并验证页面选择器、认证来源和业务政策；Cookie 共享不自动补齐 localStorage token 请求头。
- 本文件的审阅状态为 Draft；T02/T06/T08 的独立正式 Verification 尚未补齐，本项组合验证不代替它们的逐项验收。

## Conclusion

T09 实现与限定范围技术验收完成，结论通过：两项针对性回归、五个真实 CLI 最小集成、两个 Python 文件静态检查、YAML 校验与产物核对均通过。本轮没有发现产品缺陷；验证命令的目录准备问题已修正并实际补跑。

本系列八项通用能力和一项串联示例均已交付，组合验证已完成。T02/T06/T08 的独立验收以及本验证文档的用户审阅状态保持明确，不据此宣称全部阶段已 Accepted。没有创建提交。
