# T09 P0/P1 串联示例与能力验收实施计划
最后修改时间: 2026-10-02 13:49:45

## Review status

Accepted

## Flow mode and stage

标准模式 / standard，Intent/Plan 已接受，Implementation 已交付。用户查看交付后要求推进完成，正式 Verification 的技术检查已完成且结论通过，验证文档 Draft 表示用户审阅状态；没有执行 Git 写操作。

## Intent basis

依据 [T09 Intent](../intent/20260930-flow-capability-example.md)，用当前 T01-T08 的公开契约串联分页、页面等待、DOM 数据、Cookie 会话、串行提交、终态轮询和结构化结果。T08 已提交为 83e06a0；T02/T06/T08 尚无独立正式 Verification，本项不代替它们的验收。

## Design decisions

- 新增独立回环 HTTP fixture，沿用既有 example/support 的标准库 HTTP 服务方式，不依赖外部系统或新增包。每次页面登录创建独立模拟会话，重复运行不需要重启服务。
- 页面提供两页材料表格与异步翻页，先变更路由和 loading 标记，再完成数据刷新。flow 同时等待正确页码与 ready 标记，再执行 extract，避免抓取上一页残留行；空列表也有 ready 标记。
- 模拟数据包含已完成、无文件、不支持格式、已有任务、新任务成功、新任务失败和历史失败。只需短 evaluate 做扁平化、业务结果投影和计数，不在 JS 中遍历提交或轮询，不用 sessionStorage。
- 登录后 save-state 保存 Cookie，再调用模拟 logout 清除客户端 Cookie；确认接口返回 401 后 load-state 恢复，并重新读取 manifest。logout 仅移除本 fixture 的客户端 Cookie，保留服务会话，以验证浏览器状态复用；不模拟真实服务的会话吊销。
- 流程使用 manifest 中的页码数组 foreach 采集各页，collect 保存快照，再按稳定顺序 foreach 处理材料。提交 POST 位于 poll 外且不重试；已有任务只恢复查询。服务记录事件并拒绝在前一个任务结束前提交新任务，为顺序和无重放提供独立证据。
- 读取步骤仅对网络/超时显式重试。poll 同时接受 ready/failed 终态；业务失败默认导出为 failed 分类，failure_policy=fail 时在完整汇总之后断言失败。
- 场景通过 scenario 输入选择 mixed、empty、read-error、timeout；严格模式复用 mixed。读取失败为确定的 HTTP 503；超时场景维持 pending，不把限次耗尽替代超时。
- 顶层 outputs 导出 inventory/outcomes/summary/audit，report 开启有界轨迹但关闭操作输出。中途失败时完整集合和汇总可能不存在，沿用 T08 缺失导出错误语义，不发布部分集合；已经采集的 inventory 仍可导出。
- 页面和 flow 只采用当前公开接口，不新增分页专属步骤、业务引擎或旧格式适配。文档明确 UI/Cookie、业务政策、失败取证与退出码边界。

## Implementation steps

1. 实现隔离会话的模拟页面、分页接口、任务接口与审计事实。
2. 编写一个使用当前契约的串联 YAML，包含受控正常、跳过、业务失败、读取失败和超时场景。
3. 增加针对本示例的静态回归和可显式启用的真实 CLI 集成检查，验证分页唯一性、顺序、不重复提交、嵌套失败定位、完整导出、JSON stdout 和退出码。
4. 更新中英文 README、example 说明及仓库内 Agent skill，说明场景与最小运行方式。
5. 仅运行新测试文件、两个新增 Python 文件静态检查和本机最小集成，记录实际结果并停止供用户自行测试。

## Files to change

- example/support/flow_capability_server.py。
- example/public/flow-capability-example.yaml。
- tests/test_flow_capability_example.py。
- example/README.md、README.md、README_CN.md。
- plugins/pomelo-pw/skills/pomelo-pw/SKILL.md。
- 本项 Intent/Plan 和系列入口；不改产品执行器，不改 dist 材料脚本或用户级插件。

## Verification plan

开发阶段只检查新示例：validate、新测试文件、Ruff format/lint 和 mypy。真实 CLI 最小集成包含 mixed/report、mixed/fail、empty、read-error、timeout 五种必要组合，使用临时端口及独立输出目录；测试完成后关闭服务。检查 stdout 可直接解析为唯一 JSON，stderr 保留日志，成功/失败退出 0/1；服务审计与 flow 输出交叉核对，读取失败和超时不能重放 POST。正式 Verification 等用户查看交付后再进入。

## Blockers and assumptions

暂无需要用户确认的未决事项。示例要求本机可用 Chrome/Chromium，测试使用项目既有浏览器选择逻辑；无法启动浏览器时必须明确未完成集成，不能用 mock 结果代替。开发检查通过不表示系列整体验收或 T02/T06/T08 正式验收已完成。

## Risks

- fixture 按读取次数推进任务，适合确定性检查，不模拟真实服务的全部时序和认证。
- 模拟超时不会撤销已经提交的任务；超时后的服务任务仍可能是 pending，测试必须检查没有继续提交下一项。
- 基本集成不能证明外部页面选择器、认证或并发更新行为；不执行真实教材解析。

## Rollback

移除本项 fixture、flow、测试及对应文档说明，保留 T01-T08 的公开能力，不增加兼容分支。

## Implementation handoff

- 新增 example/support/flow_capability_server.py，提供异步分页 DOM、独立 Cookie 会话、任务终态与审计接口。既有任务先恢复查询，新任务完成或失败后才能提交下一项；重复或重叠提交会被拒绝并记录。fixture 的 logout 只清除客户端 Cookie。
- 新增 example/public/flow-capability-example.yaml，直接串联 T01-T08：save/load 浏览器状态、页面就绪、extract、foreach/collect、类型化条件、request、poll、assert、outputs/report。JS 仅承担快照扁平化、投影、原因分类、计数和摘要渲染；没有 sessionStorage、手写 fetch/延时/轮询控制器或旧格式适配。
- 新增 tests/test_flow_capability_example.py，默认两项快速回归，POMELO_PW_INTEGRATION=1 显式开启五个真实浏览器 CLI 场景。测试独立核对 fixture 审计与 flow 输出，并检查 Cookie 恢复、输入 JSON 的 0/false/null、字面模板数据、作用域恢复、嵌套失败定位、截图/HTML、stdout JSON 与 0/1 退出码。
- pytest 首次收集发现 example 不是可导入安装包；改为仓库 test_version_calc.py 已采用的 importlib 脚本加载方式。未调整全局 pytest 配置、包结构、依赖或生产代码。
- 实际文件范围与计划一致：4 个新增文件（fixture/YAML/测试/Plan）及 6 个修改文件（两个 README、example 说明、仓库内 Agent skill、Intent 与系列入口）。没有修改产品执行器、dist 材料 flow、相邻项目或用户级插件。
- YAML validate --json 通过。两个新增 Python 文件 Ruff lint、format --check 及 mypy --explicit-package-bases 通过；显式 package bases 仅用于本次跨 example/tests 文件的命令，不修改全局配置。
- 仅运行本项新测试文件，7 passed in 10.73s：两项快速检查加五个本机 Chrome 真实 CLI 场景。未运行全量或覆盖率，未追加既有单步骤测试。
- mixed/report：status=passed，退出 0，19/19 顶层步骤、65 条轨迹；7 条材料按 DOM 顺序完整采集，ready=3/skipped=3/failed=1/submitted=2/resumed=1。服务审计顺序为 existing 终态、fresh-ok 提交/终态、fresh-fail 提交/终态，各任务查询两次，没有重复或重叠提交。
- mixed/fail：status=failed，退出 1，AssertionFailed 定位 18.1，完整 inventory/outcomes/summary/audit 保留，并生成截图/HTML；后续业务成功不能覆盖明确失败。
- empty：status=passed，退出 0，19/19 顶层步骤、22 条轨迹，inventory/outcomes 为空、汇总全零，没有提交任务。
- read-error：退出 1，首个错误为 RequestStatusError，定位 14.index-4.1.1.3.attempt-1.1；fresh-ok 只提交一次、读取一次，fresh-fail 未提交，inventory 保留，未完成集合和后续导出明确缺失。
- timeout：退出 1，首个错误为 PollTimeoutError，保留最近 pending 结果和轮询预算；fresh-ok 只提交一次，fresh-fail 未提交，inventory 保留，不发布部分集合。实际超时发生在第 24 次条件探测；尝试次数仅记录观察事实，不作为固定验收值。
- 五种场景的 stdout 均可直接 JSON 解析、日志在 stderr；失败证据文件实际存在。产物位于 output/development-t09；已查看 mixed 的 results.png，分页表格与汇总显示正常。
- 另在本机启动自测 fixture：URL http://127.0.0.1:8767/，PID 29944，HTTP 200；启动日志在 output/flow-capability-preview。可执行下方命令自行测试，结束后用 Stop-Process -Id 29944 停止该模拟服务。
- 当前没有必须修复的遗留事项。检查只证明受控页面和模拟接口的公开契约；未运行真实材料业务，没有完成正式 Verification、系列整体验收或 Git 暂存/提交。T02/T06/T08 的独立正式验收缺口仍保留。

```powershell
uv run --locked --no-sync pomelo-pw run example/public/flow-capability-example.yaml --headless --json -v
```

严格业务失败可追加 --var failure_policy=fail；空列表、读取失败、超时可分别追加 --var scenario=empty/read-error/timeout，具体命令及预期见 example/README.md。

## Verification handoff

- 用户要求“那推进完成吧”，接受实现交付及已说明的模拟场景限制，进入正式 Verification。
- 两项快速回归与五个真实 CLI 场景均通过；两个 Python 文件 Ruff lint/format/mypy、新 YAML 校验、旧报告消费者静态核对及产物检查通过。验证命令首次漏建自定义 basetemp 的父目录，补建后仅重跑五个尚未启动的集成场景，5 passed、2 deselected。
- mixed/report、mixed/fail、empty、read-error、timeout 与预期一致；服务审计确认分页不漏不重、先终态再提交下一项，读取失败或超时不能重放提交。完整结果及截图/HTML 证据见 [T09 Verification](../verification/20260930-flow-capability-example.md)。
- 本轮只新增 Verification 并更新 Intent/Plan/系列记录，没有修改产品、fixture、测试代码或暂存区。限定范围内无必须修复的遗留事项，本项技术工作完成；用户审阅状态和 T02/T06/T08 的独立正式验收不自动标记 Accepted。

## User review notes

- 用户要求“推进下一个”，沿用按顺序实现、只做针对性回归与最小集成、达到可用状态后自行测试的约束。
- 用户随后要求推进完成，已按原定范围完成正式 Verification 的技术检查；未扩大为全量测试或真实业务验证。
