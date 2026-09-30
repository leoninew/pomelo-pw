# T04 页面条件等待实施计划
最后修改时间: 2026-09-30 20:08:02

## Review status

Accepted

## Flow mode and stage

标准模式 / standard，Intent/Plan 已接受，Implementation 已交付，当前为验证阶段 / Verification。用户已查看实现交付后明确要求“进行验证”，授权本轮针对性回归和离线最小集成；不自动推进 T05。

## Proposed contracts

```yaml
- type: wait
  condition:
    all:
      - page: {url_contains: "/items?page=2"}
      - page: {element_visible: "table tbody tr:first-child"}
      - js:
          script: "({expected}) => !document.querySelector('table').inert && document.querySelector('tbody tr').dataset.id === expected"
          args: {expected: "{{record.id}}"}
  timeout: 5000
  interval: 100
```

- wait 新增 `condition`，直接使用 T02 的完整条件树、原文 JS 函数和 args 规则；静态检查全树，运行时短路，不提供旧字符串适配。
- `condition`、`delay`、`selector`、`url`、`url_contains`、`url_pattern`、`for`、`network_idle`、`animation_stable`、`route_stable` 是原生且互斥的等待模式，按字段出现计数，必须恰好提供一种。保留已有单一模式的直接实现，不存在参数优先级或自动转换。
- `state` 仅用于 selector；`route_stable_duration` 仅用于 route_stable；`interval` 仅用于 condition。模式字符串必须非空；state 和 for 使用已知枚举，开关模式仅接受 true；null/false 不能表示未选择。
- timeout、interval、route_stable_duration 为正且有限的毫秒数，delay 为非负且有限毫秒数，不接受 bool 或字符串数字；完整引用的类型在运行时检查。timeout 默认 30000，interval 默认 100。
- 单一 page 条件优先使用 Locator.wait_for / Page.wait_for_url；单一 js 谓词使用 Page.wait_for_function，包装器同步返回布尔值，异步调用未完成时保持 false 并避免并发探测，错误立即传播。原生等待的 args 在传输边界统一 JSON 编码后解码，保持 strict boolean 与 args 缺省/null 的区别，释放返回句柄。interval 控制组合和 JS 检查间隔，单一 page 使用 Playwright 内置探测节奏。
- 组合条件复用 T02 evaluator，按 interval 检查，整个等待受统一截止时间约束，包括单次页面/async JS 探测。已经满足时立即完成；条件 false 才继续，错误立即传播，超时为明确步骤失败。
- 同一次等待在进入时固定 inputs/results/bindings 快照，页面状态实时检查；不执行查询步骤或更新结果，更新数据后判断由 T05 定义。
- 原生等待支持页面导航；组合探测仅对 Playwright 明确的执行上下文被导航销毁错误重新检查，不吞掉业务谓词错误、页面关闭或其他浏览器错误。
- 超时文本包含等待模式/条件及毫秒上限；嵌套位置使用现有执行路径，顶层仍走现有失败证据收集。条件中只看 URL 的调用方仍只等待 URL，完整 SPA 就绪必须显式组合表格/数据条件。
- 原生 animation_stable 改用 document.getAnimations() 观察 pending/running 动画，避免有 transition 声明但并未运动时一直等待；route_stable 的 sleep 限制在剩余时限内。

## Implementation steps

1. browser_functions 提供共享严格布尔谓词等待包装，复用函数调用与 JSON args 契约。
2. conditions 提供公共 wait_for_condition，原生叶节点等待与组合有界探测使用相同条件校验及解析。
3. WaitStep 增加 literal condition、互斥模式和静态/运行时类型校验，移除优先级选择行为。
4. 增加离线 page-condition-wait 示例和针对性测试代码，迁移受影响的示例及用户/插件说明。
5. 仅运行变更文件的格式、lint、类型和 YAML 静态检查；回归与浏览器测试由用户执行。

## Files to change

- `src/pomelo_pw/browser_functions.py`、`conditions.py`、`steps/wait.py`。
- `tests/test_wait.py`、现有 wait 校验测试。
- `example/public/page-condition-wait.yaml`、`spa-readiness.yaml`、example README、中英文 README、DESIGN、插件 skill/template。
- T04 Intent/Plan 及系列入口。
- 用户追加的验收缺陷修复：`src/pomelo_pw/cli.py`、`tests/test_cli.py`；run/validate 失败退出 1，成功退出 0，保留结果与诊断。

## Verification plan

当前用户已明确要求验证，Agent 运行针对性回归及离线最小集成：覆盖即刻满足、false 后成功、总超时和慢 async 谓词、严格布尔、缺省/null args、引用及迭代绑定、组合短路、输入固定、导航销毁重试、错误立即失败、互斥/范围/类型校验、嵌套等待一致性。不运行全量测试、公共网站矩阵或真实业务 flow。

## Blockers and assumptions

暂无需要用户决定的未决事项。保持现有原生单模式能力，拒绝含多模式的旧组合；不新增新旧转换。参数计时使用事件循环的单调时钟；页面导航由 Playwright 原生等待处理，组合条件只针对确定的生命周期错误继续探测。

## Risks

- 混合等待模式、不合法枚举和类型会在执行前失败；调用方必须显式拆步或使用 condition 组合。
- JS 谓词必须只观察页面；框架不会检测用户函数中的业务副作用。
- 多节点页面探测是顺序检查，不提供页面状态的原子快照；结果满足后页面仍可能变化。
- 用户自行测试，本轮不声称回归、最小集成或真实导航已通过。

## Rollback

按本任务 diff 回退公共等待、wait 声明/校验及示例说明，不增加兼容开关，不操作 Git 暂存或提交。

## Implementation handoff

- wait.condition、原生 page/JS 等待、统一组合截止时间、固定运行时快照、严格布尔与 args 缺省/null、导航销毁识别及错误定位已实现。
- 原生模式互斥与参数类型/范围校验已生效；没有旧条件转换或参数优先级适配。动画等待及 URL/route 等待的实现随相关契约调整。
- 新增 tests/test_wait.py，覆盖声明、运行时类型、原生等待委托、短路、超时/慢探测、谓词错误、上下文销毁、固定结果及嵌套 foreach/if；更新既有无模式 wait 测试。
- 新增离线 example/public/page-condition-wait.yaml，保留 T03 collection-iteration 示例；SPA 示例和中英文说明、插件模板、DESIGN 已更新。
- 本轮实际变更的 13 个 Python 文件通过 Ruff format/lint 和 mypy。collection-iteration、page-condition-wait、spa-readiness 及 dist/material-parse-all-v2.yaml 通过 CLI 静态校验。git diff --check 的两个 CRLF 文件问题已通过限定文件格式化修正。
- 按用户自行测试的指令，T04 未运行 pytest 或浏览器；新增两个离线 example 未试跑。先前 T03 的 280 项通过及 v2 fixture 证据不代表最终 T04 版本已经完成运行验证。
- 当前停在可供用户试跑的 Implementation，不创建正式 Verification，不进入 T05。Git 暂存和提交由用户操作；dist 被忽略，v2 需要用户留意其提交范围。

用户最小试跑入口：

```powershell
uv run --locked --no-sync pomelo-pw run example/public/collection-iteration.yaml --headless -v
uv run --locked --no-sync pomelo-pw run example/public/page-condition-wait.yaml --headless -v
```

针对性回归入口：

```powershell
uv run --locked --no-sync pytest tests/test_foreach.py tests/test_loop.py tests/test_wait.py tests/test_steps.py tests/test_conditions.py tests/test_substitution.py tests/test_executor_control_flow.py tests/test_executor.py -q
```

## Verification handoff

- 用户明确要求验证；T03/T04 首轮 8 个相关测试文件共 370 项通过，13 个变更 Python 文件及相关 YAML/模板静态检查通过。
- 两个离线示例、v2 受控场景、原生/组合整页导航与 async 超时、非布尔/抛错及实际等待失败证据检查通过。
- 验证中移除两份示例及模板的多余 about:blank 导航；原生等待使用 Playwright 自身时限，组合探测屏蔽直接取消并消费迟到错误，解决未取回 Future 异常。
- 追加检查修正原生 JS 返回 Promise 被当作真值及等待接口递归删除 null 参数的问题；同时按用户要求修正 CLI 失败退出码。最终相关回归 66 项、四个修复文件静态检查、真实 CLI 五个场景通过；原生 false/async/错误/导航及离线等待示例针对性复跑通过。
- 完整结论、证据、实际耗时和限制见 [T04 Verification](../verification/20260930-page-condition-wait.md)。当前等待用户审阅，不自动推进 T05；修正与验收文档未自动暂存，Git 操作留给用户。

## User review notes

- 用户明确“推进下一步工作，我自行测试”，并随后要求继续；达到可用状态后交付。
- 用户随后明确“进行验证”，授权 Agent 运行相关回归、离线最小集成和必要静态检查；保留不自动推进下一任务和不操作 Git 暂存/提交的约束。
- 用户明确要求验收发现的问题必须分析并解决，不能只记录或留待后续任务；追加修复与针对性验证已完成。按“不追求极致的覆盖率”收敛检查，不扩大测试矩阵。
