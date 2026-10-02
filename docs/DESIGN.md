# 架构设计

[返回首页](../README_CN.md) | [开发指南](DEVELOPMENT_CN.md) | [流程参考](FLOW_REFERENCE_CN.md)

本文面向实现和维护，说明模块职责、状态所有权与执行边界。命令和接入方式见[使用指南](USAGE_CN.md)，YAML 参数与对外数据契约见[流程参考](FLOW_REFERENCE_CN.md)。

## 模块职责

| 模块 | 职责 |
| --- | --- |
| [cli.py](../src/pomelo_pw/cli.py) | 命令参数、文本/JSON 输出和退出码 |
| [executor.py](../src/pomelo_pw/executor.py) | 加载、递归校验、参数解析、步骤调度与结果发布 |
| [browser.py](../src/pomelo_pw/browser.py) | 统一创建 Chromium 与 BrowserContext |
| [config/](../src/pomelo_pw/config/) | 工具默认配置与本机浏览器选择 |
| [steps/base.py](../src/pomelo_pw/steps/base.py) | StepSpec、StepContext、StepResult 与步骤注册 |
| [runtime.py](../src/pomelo_pw/runtime.py) | 分层输入、结果快照和 JSON 数据边界 |
| [substitution.py](../src/pomelo_pw/substitution.py) | 类型化引用、路径解析和输入循环引用检查 |
| [conditions.py](../src/pomelo_pw/conditions.py) | 共享条件校验、求值与页面条件等待 |
| [browser_functions.py](../src/pomelo_pw/browser_functions.py) | 页面函数调用与 JSON 参数传输 |
| [polling.py](../src/pomelo_pw/polling.py) | 截止时间、轮询进度和失败诊断 |
| [reporting.py](../src/pomelo_pw/reporting.py) | 统一执行报告、有界轨迹与错误集合 |
| [error_context.py](../src/pomelo_pw/error_context.py) | 失败截图、HTML、console 和网络证据 |

步骤模块实现单次操作或描述控制体，执行器负责调度。CLI 与 Python API 共用 `FlowExecutor.run_flow()`，各步骤不另建流程运行入口。

## 执行生命周期

1. 加载 YAML，递归校验顶层配置、步骤规范、输入与结果绑定声明。
2. 合并调用方覆盖值，解析输出目录与浏览器模式。
3. 启动浏览器；每次普通执行或 data 行创建独立 BrowserContext 和 RuntimeContext。
4. 调度步骤，在执行时解析参数、校验解析后的类型并执行单步重试。
5. 发布成功输出，再调度分支、集合或轮询控制体；记录逻辑步骤与失败证据。
6. 解析显式导出，形成报告并清理浏览器资源；启动和清理失败也返回统一报告。

工具配置、流程配置和调用方覆盖值分别由 config、YAML 与 CLI/API 持有。相对输出路径以执行器的 `work_dir` 为基准，具体优先级见[使用指南](USAGE_CN.md)。

## 步骤协议与校验

`StepSpec` 声明参数、别名、是否产生公开输出，以及哪些字段是子步骤或原文。静态校验可以检查未来结果引用的结构，但不提前要求结果存在；依赖执行数据的值在参数解析后再次校验。

`child_step_params` 使子步骤延迟解析并接受递归校验，避免在父步骤执行前解析尚未产生的数据。`literal_params` 保留函数源码、条件树和收集表达式，由相应模块在正确时机解析。

`StepResult` 的三类数据有独立用途：

- `output` 是可供后续流程读取的 JSON 数据；`NO_OUTPUT` 与 JSON null 有区别。
- `control` 描述分支或循环调度，交由执行器处理。
- `diagnostics` 保存运行诊断和取证信息，不作为隐式业务输出。

## 运行时状态与作用域

`RuntimeContext` 分开持有配置输入和结果。每个 data 行新建上下文，嵌套步骤共享当前行的结果；`StepContext.scopes` 保存普通局部变量，兄弟步骤不共享这些局部定义。

`StepContext.bindings` 保存集合元素与索引。它们独立于配置输入，并作为不透明数据传给引用解析器；嵌套遍历遮蔽同名绑定，退出时恢复外层绑定。进入遍历时复制数组，每轮复制元素，写回来源结果不会改变活动遍历。

结果发布由执行器统一负责。步骤执行前捕获旧结果供参数读取，并清除待写绑定；最终成功后仅发布 JSON 快照，失败时保持绑定缺失。返回字符串不再解释成模板，避免数据被意外执行或重新替换。

JSON 值在输入、浏览器传输和输出发布边界校验并复制。参数通过结构化载荷传入页面函数，不拼接到源码；浏览器和 Python 两端都检查返回值。引用规则见[流程参考](FLOW_REFERENCE_CN.md#运行时数据)。

## 条件、等待与轮询

| 执行形式 | 观察对象 | 快照时机与调度职责 |
| --- | --- | --- |
| if / while / assert | 输入、结果与页面 | 单次求值使用一份数据快照；while 每轮重新取快照 |
| wait.condition | 实时页面 | 输入、结果与迭代绑定固定；只观察，不执行查询步骤 |
| poll | 查询步骤产生的新结果 | 执行完整控制体后重新取快照，再判断是否继续 |

`conditions.py` 统一校验和求值。组合条件顺序短路，运行时只解析访问到的节点，静态校验仍检查整棵树。断言观察值在同一次求值中记录，不重新读取节点或访问短路分支。

单个页面或 JS 等待使用 Playwright 原生等待；组合条件使用共享 evaluator 与统一截止时间。Playwright 原生轮询需要同步布尔结果，因此异步 JS 包装器保存 pending 状态，等待函数完成后再检查，不并行启动未完成的探测。

浏览器参数在需要时编码为 JSON 后解码，避免 Playwright 的参数过滤省略嵌套 null。函数调用保留无参数与显式 null 的区别。具体时序与错误语义见[流程参考](FLOW_REFERENCE_CN.md#页面条件等待)。

## 重试与副作用边界

`_execute_with_retry()` 只执行步骤自身。`_execute_step()` 在单步重试完成后调度控制体，因此子步骤失败不会让父控制步骤重放已完成的分支、迭代或写操作。子步骤有独立重试策略。

`foreach.collect` 在每项完整成功后的作用域中读取一次并复制结果。集合数量和 JSON 字节预算逐项检查，超限不发布部分集合，也不重放已完成的操作。

轮询首次立即查询，每轮串行完成后才考虑下一轮。`StepContext.polls` 传递各层进度，执行器按最早截止时间收紧原生 timeout，并覆盖控制体、条件、重试间隔和轮询间隔。轮询步骤自身不承担重试，查询步骤可以显式重试。

在途协议调用通过 shield 保留，完成回调消费迟到异常；结果发布与后续调度留在调用端。超时后不开始新操作或发布迟到结果，但已经发出的浏览器操作可能完成。执行器不撤销副作用，也不推断写操作是否幂等。

轮询诊断保留每层最近成功结果，独立于 runtime 的失败重绑定清理。失败沿嵌套路径携带预算、阶段和最近结果；`on_error: continue` 只影响后续调度，不把最终失败改成成功。

## 页面与请求适配

`request` 使用当前 BrowserContext 的 APIRequestContext，复用 Cookie 及响应 Cookie 更新。URL 由标准解析器处理，不通过页面 fetch；响应读完后释放 APIResponse，不销毁共享请求客户端。总预算覆盖请求与读取，并服从外层轮询预算。

`extract` 使用一次同步 `evaluate_all` 回调取得根集合并映射字段，字段之间没有 await。根 selector 使用 Playwright，行内字段使用浏览器相对 CSS；配置通过结构化参数传入，原生错误带行和字段位置传播。

两者都复用结果发布、重试、轮询预算和取证机制。认证头、页面就绪以及业务类型转换由流程显式表达；用户可见边界见[请求](FLOW_REFERENCE_CN.md#浏览器会话-http-请求)与[提取](FLOW_REFERENCE_CN.md#dom-数据提取)参考。

## 报告与失败取证

`ExecutionReport` 由 `StepContext.report` 共享。步骤开始时预留轨迹条目以保持嵌套顺序，结束时记录最终逻辑状态与单调时钟耗时；重试中间态不另写轨迹。控制步骤耗时包含子步骤执行。

嵌套错误沿因果链保留最深步骤位置与轮询诊断。顶层失败触发截图和 HTML 取证；取证失败追加证据，不覆盖原始原因。data 行独立报告，顶层合并时保留行定位并继续约束轨迹和错误数量。

流程结束时固定 inputs/results 快照，逐字段解析显式 `outputs`。导出失败追加报告错误，其他字段仍尝试导出；业务分类与执行状态没有隐式关联。显式导出不自动公开所有输入或运行时数据。

轨迹、错误与可选步骤输出有独立数量或字节预算，省略详情不改变状态；业务集合超限和显式导出错误则按执行失败处理。对外字段、默认值与退出码统一在[报告参考](FLOW_REFERENCE_CN.md#断言与执行报告)维护。

## 扩展约定

新增步骤继承 `BaseStep`，声明 `StepSpec`，用 `register_step` 注册，并在 `steps/__init__.py` 导入模块。步骤通过 `StepContext` 使用现有页面、运行时、输出目录和轮询预算，不另建不受调度器管理的浏览器或运行时。

有公开输出的步骤声明 `produces_output` 并返回 `StepResult.output`；控制步骤通过 `control` 描述子步骤。新增引用、条件、重试或报告规则应进入共享模块，保持顶层和嵌套执行一致。

用户用法与参数更新进入使用指南或流程参考，运行前置条件进入示例说明，模块职责和机制变化才更新本文。旧接口不提供兼容适配；历史需求、方案和验证证据保存在各自过程目录。
