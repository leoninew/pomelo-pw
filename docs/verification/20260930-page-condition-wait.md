# T04 页面条件等待验证
最后修改时间: 2026-10-01 22:10:35

## Review status

Accepted

## Flow mode and stage

标准模式 / standard，Verification 已接受。针对性回归和离线最小集成已完成，用户要求分两批提交且不再测试；T04 已提交为 4d98eac，随后用户明确继续推进任务，视为接受本项验收并进入 T05。不新增测试证据。

## Intent alignment

依据 [T04 Intent](../intent/20260930-page-condition-wait.md)。wait.condition 使用统一条件与结构化参数，支持明确时限、原生页面等待、JS 谓词和组合探测；页面观察与 T05 的查询步骤轮询保持独立。

| 验收项 | 结果与证据 |
| --- | --- |
| 页面组合、JS 谓词、超时及运行时参数 | 通过；条件/引用/等待回归及 SPA 示例均通过 |
| 已满足立即完成、不满足有界检查 | 通过；短路不 sleep，实际异步永久未决谓词在 75ms 配置下约 78ms/94ms 返回超时 |
| 失败包含条件、位置并采集证据 | 通过；真实 foreach 内 wait 超时错误包含 2.index-0.1 (wait)、25ms 和条件，截图/HTML 已保存 |
| 等待模式互斥、无隐式优先级适配 | 通过；无模式、多模式、null/false、枚举、时间类型/范围及参数归属回归通过 |
| 单页导航及 SPA 数据就绪 | 通过；原生/组合 JS 跨完整导航通过；SPA 示例在 hash 更新后继续等行数据及 table.inert 状态 |
| 顶层、分支、循环行为一致 | 通过；示例包含顶层 page/JS、foreach 内组合及 if 内 JS；嵌套当前项引用与失败定位通过 |

## Spec alignment

不适用，按 standard 模式跳过独立 Spec，精确契约由 Plan 定义。

## Plan alignment

依据 [T04 Plan](../plan/20260930-page-condition-wait.md)。同一次等待固定输入/结果/绑定快照；原文脚本、args 缺省/null、strict boolean、节点短路与错误传播符合计划。单一 page 叶节点使用 Locator.wait_for/Page.wait_for_url，单一 JS 使用 Page.wait_for_function；组合观察使用共享 evaluator 和统一截止时间。

实测发现 asyncio.timeout 直接取消 Playwright 调用后，底层 Future 的迟到异常可能未被取回。验证中修正为原生叶节点使用 Playwright 自身时限，组合探测通过 shield 保留在途调用，并在外层超时/取消后消费迟到错误。新增回归确认 Future 未被直接取消且迟到异常不会进入事件循环错误日志；实测复跑未再出现 Future exception was never retrieved。

追加真实 CLI 检查发现原生 JS 包装返回 Promise，Playwright 的同步轮询将 Promise 当作真值，导致 false 被误报为成功。已改成同步返回布尔值的包装：同步结果直接检查，异步结果在单次等待的参数对象上保存 pending/ready/error，只在实际结果为 true 时完成，不并行发起未结束的探测。

修正后离线示例又暴露 Playwright Python 等待接口组装参数时递归删除字典中的 None，导致显式 args: null 变成 undefined。原生 JS 的 args 在传输边界统一使用 JSON 编码，每次调用解码，保留 null、嵌套数据和缺省参数区别；没有双契约或旧调用适配。

这些修正属于原等待布尔值、结构化参数、截止时间与生命周期契约，没有扩大等待模式。用户要求发现的问题当轮解决后，同时修正 run --json 失败退出 0 和 validate 校验失败退出 0：输出结果后统一退出 1，成功仍退出 0。

## Actual diff

| 计划范围 | 实际改动 |
| --- | --- |
| browser_functions/conditions | 同步返回严格布尔值、保存异步状态、JSON 编码传输 args、句柄释放、原生叶节点及组合等待、截止时间和取消处理 |
| WaitStep | condition/interval；互斥模式、类型/范围/参数归属校验；原生 URL/动画/route 实现调整 |
| 测试与离线示例 | test_wait、既有 wait 校验；page-condition-wait、SPA 示例；移除新示例多余导航 |
| 文档和模板 | 中英文 README、DESIGN、example 索引、仓库插件 skill/template、阶段与系列记录 |
| 用户追加的 CLI 缺陷修复 | run/validate 失败退出 1；保留 JSON、错误和证据字段，增加针对性回归 |

实际范围符合计划及用户追加的 CLI 缺陷修复要求。共享条件、执行器和绑定变化同时由 T03 回归覆盖。没有扩展 navigate 对 about:blank 的支持：新页面已经为空白页，示例与 collection-results 模板直接从 evaluate 开始。

## Test results

T03/T04 首轮共同执行的 8 个相关测试文件共 **370 passed**；首轮结果未充分验证原生 JS 的 false 行为，追加检查发现的问题均已修复：

```powershell
uv run --locked --no-sync pytest tests/test_foreach.py tests/test_loop.py tests/test_wait.py tests/test_steps.py tests/test_conditions.py tests/test_substitution.py tests/test_executor_control_flow.py tests/test_executor.py -q
```

追加 CLI 与受影响 wait 的针对性回归，最终 **66 passed**：

```powershell
uv run --locked --no-sync pytest tests/test_cli.py::TestRunCommand tests/test_cli.py::TestValidateCommand tests/test_wait.py -q
```

新增 7 个 CLI 用例覆盖 JSON 成功/流程失败/数据驱动失败/异常及有效、无效配置校验；另有 2 个用例使用 Playwright 自带 Node 实际运行 JS 包装，确认同步/异步 false 到 true 的轮询只返回布尔值、保留嵌套 null。

首轮 13 个变更 Python 文件通过 Ruff format --check、Ruff check 和 mypy；追加修复涉及的 browser_functions.py、cli.py、test_wait.py、test_cli.py 四个文件通过相同检查。四个相关 YAML 与 collection-results 模板静态校验通过，工作树与暂存区 diff 空白检查通过。

### Offline examples

- page-condition-wait 在本机 Chrome headless 完整执行 8 个顶层步骤。hash 立即变化后，组合条件继续等延迟数据更新，依序处理 a、b；嵌套 async JS、无参数和显式 null 均通过，最后确认 ready=2/last.id=b。
- collection-iteration 同时复跑通过，确认等待代码修正未破坏共享的条件/局部绑定行为。
- 首轮示例使用 FlowExecutor API 断言 success=true、全部步骤执行和截图存在；追加检查同时核对实际 CLI 子进程的退出码与 JSON 结果。
- 两个示例初次失败源于显式 navigate about:blank，已在原示例/模板移除；错误产物保留，成功产物写入 collection-pass/wait-pass 子目录。

### Real browser boundaries

- 非布尔返回和业务抛错立即成为条件错误；未转成 false 等到超时。
- 原生 JS 与组合 JS 的永不完成 async 谓词在 75ms 配置下分别约 78ms/94ms 返回失败，包含配置时限。
- 拦截 http://wait-fixture.test/start -> /complete，初始页面在 75ms 后整页跳转，谓词跨 150ms async 探测；原生与组合等待均成功观察最终 ready 节点。
- 声明 10s transition 但未运行的按钮不会阻塞 animation_stable。
- 实际嵌套 wait 的 25ms 耗尽输出条件、位置及截图/HTML；受控 foreach 写入失败额外确认父重试不重放，见 T03 记录。
- 第一次边界检查暴露底层 Future 日志问题；修正后的边界复跑日志干净，只有预期的受控业务失败输出。
- 原生等待包装修正后，真实浏览器针对性复跑：同步非布尔及异步抛错失败；async false、永不结束的 Promise 均在 75ms 配置下超时；async false 到 true 恰好执行 3 次串行探测；异步谓词跨完整导航通过。最终 page-condition-wait 离线示例的 8 个顶层步骤全部执行，缺省/null 参数均通过。
- 真实 CLI 的离线成功、嵌套等待失败、执行前校验异常、validate 无效配置与 v2 有效配置共五个场景通过，实际退出码分别为 0/1/1/1/0；失败保留 JSON 错误路径、时限、截图和 HTML。

产物根：output/verification-t03-t04/20260930191257。成功截图为 wait-pass/ready.png，整页导航截图为 edges/native-navigation.png、edges/composite-navigation.png，等待耗尽证据为 edges/wait-failure/error-step-2.png/.html。成功示例截图已查看，页面显示 Ready row b 和 a b，内容正常。

追加修复后的产物位于 cli-exit-codes：wait-success/ready.png、success/collection.png 及 failure/error-step-2.png/.html；夹具为 failure.yaml、invalid.yaml。

## Missed or expanded scope

用户明确要求解决验收发现的问题，授权追加 CLI 退出码修复，没有推迟到 T08；原生 JS、参数传递、取消处理与示例修正直接来自本轮失败证据。不运行全量测试、公共网站矩阵或真实业务页面，不修改相邻仓库、不启动服务器、不执行 Git 写操作。插件模板仅做本地静态核对，未同步用户级安装。

## Risks and incomplete items

- 没有必须修复的 T04 遗留项；用户要求提交并继续任务，Verification 已接受。
- 多节点探测不是页面状态的原子快照，条件满足后页面仍可能改变。interval 控制组合和 JS，page 叶节点遵循 Playwright 内置节奏。
- 毫秒截止时间不是硬实时保证，浏览器响应/事件循环调度存在少量开销；本轮记录了真实耗时。
- 等待超时不会强制终止页面用户函数；在途探测最终结束或页面关闭时消费结果。JS 谓词应只观察页面，不承担写操作。
- 真正登录、生产 SPA 与教材解析未执行。HTTP、步骤轮询和完整业务验收继续由后续任务承担。

## Conclusion

限定范围内技术验证通过，用户已接受并要求继续任务。验收发现的问题已修正并针对性回归；T04 已提交，本轮没有追加测试。
