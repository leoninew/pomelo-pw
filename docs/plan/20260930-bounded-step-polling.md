# T05 有界步骤轮询实施计划
最后修改时间: 2026-10-02 09:56:33

## Review status

Accepted

## Flow mode and stage

标准模式 / standard，Intent/Plan 已接受，Implementation 已交付，当前验证阶段 / Verification。用户查看交付后要求开始验证，针对性回归、离线最小集成及静态检查已通过，Verification 为 Draft 待用户审阅；不自动推进 T06。

## Intent basis

依据 [T05 Intent](../intent/20260930-bounded-step-polling.md)，复用 T01 的结果绑定与 T02 的条件树。T03/T04 已分别提交，本次限于 T05。

## Proposed contracts

```yaml
- type: poll
  until: {in: ["{{results.task.status}}", [ready, failed]]}
  timeout: 30000
  interval: 1000
  max_attempts: 20
  save_as: polling
  steps:
    - type: evaluate
      args: {id: "{{results.submitted.id}}"}
      script: "async ({id}) => { const r = await fetch('/tasks/' + id); if (!r.ok) throw new Error('HTTP ' + r.status); return await r.json(); }"
      save_as: task
      retry: 2
      retry_delay: 250
```

- 新增独立 `poll`，必需 `until` 和非空 `steps`；until 使用共享条件树并保留原文，子步骤执行时解析参数。
- 首轮立即执行完整轮询体，成功后判断 until；false 时从本轮完成起等待 interval，再开始下一轮，不并发查询、不在首次查询前判断旧结果。
- timeout 默认 30000ms、interval 默认 1000ms，必须为正且有限的数字；可选 max_attempts 为正整数。支持完整类型化引用，拒绝 bool、字符串数字及显式 null。
- 整个轮询使用单调时钟截止时间，涵盖轮询体、条件、子步骤重试及 retry_delay、interval。内层预算不能延长外层预算；耗尽后不启动新操作、不保存迟到结果。
- 在途单步骤及条件探测通过 shield 保留 Playwright 调用，消费迟到异常；返回结果的发布与控制体调度在截止时间检查之后。已有原生 timeout 参数按剩余预算收紧。浏览器已发出的操作或 JS 不能保证被终止，轮询退出也不撤回已经发生的副作用。
- 条件 true 正常结束，包括业务失败终态；业务成功由后续分支决定。条件错误和子步骤失败立即结束，读取异常只按对应子步骤显式 retry 处理。poll 本身拒绝 retry/retry_delay/retry_on，避免整体重放。
- 超时和轮次耗尽均明确失败。输出/诊断包含 attempts、elapsed_ms 和轮询体最近成功发布的 results；失败另含 until、timeout、max_attempts、阶段与具体步骤路径。成功 poll 可 save_as；失败不发布成功输出。嵌套错误保留各层轮询诊断，CLI 沿现有失败路径输出并退出 1。
- 现有 while 在上限后再次判断：false 正常完成，仍为 true 则失败；不新增兼容开关。固定 times 行为不变。
- 实现检查发现 on_error=continue 会掩盖步骤失败，因此修正最终汇总：继续执行后续步骤，但整体 success=false，保留最后失败步骤与诊断，CLI 沿既有契约退出 1。

## Implementation steps

1. 新增 poll 步骤声明、静态/运行时校验及注册。
2. 增加轻量轮询进度与失败诊断类型；StepContext 传递嵌套预算和进度。
3. 执行器调度 poll，约束步骤/重试/探测和结果发布，保留嵌套路径与 CLI 诊断；调整 while 耗尽语义。
4. 增加针对性测试代码和离线示例，同步中英文 README、DESIGN 及仓库插件说明/模板。
5. 仅检查变更文件的格式、lint、类型和 diff；不运行 pytest 或浏览器示例。

## Files to change

- src/pomelo_pw/polling.py、steps/poll.py、steps/base.py、steps/__init__.py、executor.py。
- tests/test_poll.py、tests/test_executor_control_flow.py。
- example/public/bounded-step-polling.yaml、example/README.md。
- README.md、README_CN.md、docs/DESIGN.md、plugins/pomelo-pw/skills/pomelo-pw/{SKILL.md,templates.md}。
- T05 Intent/Plan、系列入口；T03/T04 Verification 只更新用户接受记录。
- 用户追加前置脚本迁移：创建 K12 的 .pomelo-pw/material-parse-all-v4.yaml，原文件保留；交付前发现该新文件已移至本项目 dist/material-parse-all-v4.yaml，按现有位置保留。仅改写脚本，不改动相邻服务代码或运行真实业务。

## Verification plan

当前用户已授权 Agent 运行针对性回归与最小离线集成：立即首查/多步骤新结果、业务失败终态、超时/次数耗尽、末轮恰好满足、子查询重试预算、迟到结果不发布、条件错误、嵌套轮询预算与路径、foreach 绑定、while 新耗尽语义及参数/递归校验。核对 CLI 失败退出码和轮询诊断；发现的问题当轮解决并复查。不进行全量测试，不追求极致覆盖率，不运行真实材料业务。

## Blockers and assumptions

暂无需要用户确认的未决事项。默认轮询面向只读查询；框架不推断用户脚本的幂等性。最近结果只包含轮询体成功发布的绑定，不自动收集没有 save_as 的返回值。

## Risks

- while 上限后条件仍为 true 的旧流程将失败，需要调用方选择合理上限；不兼容旧成功退出语义。
- 在途页面操作可能继续执行；不会启动下一查询或发布迟到结果，但不能保证浏览器侧任务被撤销。
- 本轮运行检查限于静态检查，回归和浏览器示例留给用户，不能声称运行验收通过。

## Rollback

按本项 diff 回退新增 poll 与预算调度、while 耗尽语义及相关示例说明；不增加新旧适配，不执行 Git 暂存或提交。

## Implementation handoff

- 新增 poll 及完整声明/运行时校验，立即首查、多步骤新结果判断、统一截止时间、可选轮次上限、子查询显式重试和嵌套预算已实现。
- 超时后停止调度和结果发布，在途操作迟到结果/异常被消费；最近成功结果独立保留，失败重绑定不误用旧 runtime 值。成功输出可 save_as，顶层失败诊断与嵌套路径保持完整。
- while 末轮后重新判断，仍 true 时失败；on_error=continue 继续调度但最终报告失败。没有兼容适配、业务状态专用步骤或 T06 HTTP 能力。
- 新增 tests/test_poll.py，覆盖首查、新结果、末轮满足、失败终态、耗尽、子查询重试、整体预算、迟到结果、条件错误、嵌套预算/路径、绑定及继续执行的失败汇总；更新已有 while 耗尽测试。
- 新增离线 example/public/bounded-step-polling.yaml，串联 foreach、多步骤 poll、成功/失败终态及结果核对。README、DESIGN 和本地插件说明/模板同步，未同步用户级插件安装。
- 7 个变更 Python 文件通过 Ruff 格式/lint 和 mypy，离线 polling 示例通过 CLI 静态校验；工作区及暂存区 diff 检查通过。按用户指令未运行 pytest、浏览器或真实登录/材料解析，没有创建本项 Verification。
- 先按用户要求完成 v4 脚本迁移，使用当时已提交的 T01-T04 能力：结果绑定、分页/记录 foreach、wait.condition、结构化 while 及显式耗尽检查。移除 sessionStorage 和 JS 等待循环，读取 fetch 使用原生超时；仍保留业务规则和 DOM 提取 JS。脚本在创建位置静态校验通过，随后被移至 dist/material-parse-all-v4.yaml；没有覆盖原始脚本，也没有重新搬回。
- 当前停止在 Implementation，供用户自行测试；不自动推进 T06，不执行 Git 暂存或提交。

用户可运行的最小离线示例：

```powershell
uv run --locked --no-sync pomelo-pw run example/public/bounded-step-polling.yaml --headless -v
```

针对性回归入口，尚未由 Agent 执行：

```powershell
uv run --locked --no-sync pytest tests/test_poll.py tests/test_executor_control_flow.py tests/test_loop.py tests/test_foreach.py -q
```

## Verification handoff

- 4 个相关测试文件共 120 项通过；7 个变更 Python 文件的格式/lint/类型检查通过。
- 离线 polling 示例通过，两个任务均在第 3 轮结束并汇总为 ready=1/failed=1；真实 CLI 轮次耗尽与总超时退出 1，continue 模式保留失败及证据。
- 真实浏览器慢查询/慢条件在 75ms 配置下各约 94ms 返回超时，迟到结果不发布、迟到异常被消费；浏览器关闭后无未结束操作或事件循环错误。
- v4 仅静态校验通过，未执行真实材料业务；未跑全量测试、覆盖率或开发服务器。
- 没有产品代码缺陷或修复，只修正辅助验收脚本的证据字段名。完整证据与限制见 [T05 Verification](../verification/20260930-bounded-step-polling.md)。当前等待用户审阅，不自动进入 T06 或执行 Git 写操作。

## User review notes

- 沿用用户“没有未决事项就开始实现”“达到可用状态后停止，用户自行测试”的指令。
- 用户此前要求不再测试；本轮不运行测试，仅必要静态开发检查。
- 用户追加要求在 T05 之前改写指定 K12 材料脚本为 v4；先完成该前置产物并静态校验，再继续本项实现。收尾时尊重文件已被移至 dist 的现状。
- 用户随后要求开始验证，进入 Verification；此前本轮不测试的限制据此解除，仍限定针对性回归和离线最小集成。
- 用户再次明确“进行基本的测试就行”；已有针对性回归与最小集成完成，不追加测试或扩大验收范围。
