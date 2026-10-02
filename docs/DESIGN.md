# Pomelo PW - Flow-based UI Automation Tool
最后修改时间: 2026-10-02 11:16:05

## 项目概述

Pomelo PW 是一个基于 Playwright 的流程化 UI 自动化工具，从 typing-island/scripts 抽取核心能力成为独立工具。

**核心价值：**
- 声明式 YAML 定义 UI 自动化流程
- 类型安全的步骤规范与校验
- 可扩展的步骤处理器架构
- 灵活的变量替换系统
- 支持 Claude Code、Codex 与 Grok Build 原生插件集成

---

## 项目结构

```
pomelo-pw/
├── pyproject.toml           # uv 项目配置
├── Makefile                 # 构建命令
├── README.md
├── src/
│   └── pomelo_pw/
│       ├── __init__.py
│       ├── cli.py           # CLI 入口
│       ├── executor.py      # 流程执行器
│       ├── runtime.py       # 运行时输入和结果快照
│       ├── conditions.py    # 共享条件校验和求值
│       ├── polling.py       # 轮询预算、进度和失败诊断
│       ├── browser_functions.py # 浏览器函数及 JSON 传输
│       ├── substitution.py  # 变量替换
│       ├── config/          # 配置管理
│       │   ├── __init__.py
│       │   └── settings.py
│       └── steps/           # 步骤模块
│           ├── __init__.py
│           ├── base.py      # 步骤基类
│           ├── navigate.py
│           ├── screenshot.py
│           ├── click.py
│           ├── fill.py
│           ├── wait.py
│           └── ...
├── tests/                   # 单元测试
├── example/                 # 示例流程
└── docs/
    └── DESIGN.md
```

---

## 设计原则

### 配置分离

| 配置类型 | 位置 | 用途 |
|----------|------|------|
| **工具配置** | 内置默认值 | 浏览器行为、视口、超时等运行参数 |
| **流程配置** | `flow.yaml` | 变量定义、步骤序列、`output_dir`、`headless` |
| **运行时配置** | CLI 参数 | 变量覆盖、输出路径、浏览器模式 |

### 工作目录模型

```
用户工作目录/
├── example/            # 示例流程（可选）
│   └── my-flow.yaml
└── my-flow/            # 默认输出目录（按 flow 文件名）
    └── screenshots/
```

Flow 可以在顶层用 `output_dir` 覆盖默认输出目录；相对路径以用户工作目录解析，支持 `{{variable}}`。CLI `-o/--output` 的优先级高于 flow 配置。Flow 还可以用布尔型 `headless` 指定浏览器模式，未配置时默认显示浏览器；CLI `--headless` 的优先级更高。

---

## 核心组件

### 1. 步骤系统

每个步骤继承 `BaseStep`，定义 `StepSpec` 规范：

```python
@register_step
class NavigateStep(BaseStep):
    spec = StepSpec(
        name="navigate",
        description="Navigate to a URL",
        required_params=["url"],
        optional_params={"timeout": 30000},
    )
```

### 2. 类型化输入与结果

每次执行创建 `RuntimeContext`，分层持有输入及独立结果；data-driven 每行新建上下文。输入优先级：

```
CLI/API 覆盖 > 当前步骤变量 > 最近外层步骤变量 > data 行 > flow 变量
```

`{{name}}`、`{{item.path}}`、`{{inputs.filter}}`、`{{results.records[0].id}}` 的完整引用都保留 JSON 类型；文本拼接只接受标量。字段和非负下标组成路径，不支持表达式或通用 JSONPath。输入定义可以递归引用并检测循环；已返回的数据不再次解析。`inputs`/`results` 为保留的输入根名称。普通文本用 `\{{` 转义，`${...}` 不处理。

`StepContext` 共享 runtime，以 scopes 保存逐层局部变量；兄弟步骤不共享局部变量。`StepSpec.child_step_params` 标明需要延迟解析和递归校验的子步骤字段；`literal_params` 标明原文字段，如 evaluate.script。顶层及嵌套执行都走 `_execute_step()`。

`StepResult.output` 为唯一公开输出，`NO_OUTPUT` 表示没有输出，区别于 null；control 为分支和循环调度，diagnostics 为 console、截图对比、状态文件等信息。`StepSpec.produces_output` 声明能否使用 `save_as`。执行前捕获旧结果读取快照并清除待写绑定，成功重试结束后仅发布最终 JSON 快照；失败保持绑定缺失。

`evaluate` 只接受同步或 async 函数表达式，args 是单个结构化 JSON 载荷。统一的浏览器包装器读取 script、args 和 hasArgs，再按有无参数调用函数；不拼接业务数据到源码。返回前检查 JSON 数据，Python 再校验和复制；console 监听器在 finally 中移除。无参数与显式 null 不同，不注入模块脚本，不改写末尾 return。

Python 调用迁移到 `StepContext.runtime`/`inputs` 及 `StepResult.output`/`control`/`diagnostics`；旧 data 和变量快照接口不保留适配。YAML 源码插值改为 args，裸脚本改为函数；CLI 覆盖现在统一高于行和局部输入。

### 3. 结构化条件

`conditions.py` 提供 `validate_condition()` 与 `evaluate_condition()`。if.condition 和 loop.while 使用恰好包含一个操作符的对象，不识别旧冒号字符串或裸 JS 表达式。数据操作符为 eq/ne/in/exists，组合为 all/any/not，页面检查位于 page，自定义函数谓词位于 js。

JSON 相等递归区分布尔和数字，数字 1 与 1.0 相等；in 仅接受数组。exists 仅将路径缺失转成 false，已定义的 null/false/0/空值为 true。非法路径、循环引用和其他判断中的缺失引用均失败。all/any 非空并按顺序短路；validate 检查整棵树的结构，实际求值只解析访问到的操作数，业务数据对象不解释为条件。

通过现有 `literal_params` 保留原始 condition/while，直到求值时才解析。每次求值获取一份有效输入和结果快照，同一组合复用此快照；while 每轮执行循环体前重新获取，读取上一轮已发布的结果。执行器调用公共入口，不再依赖 ConditionalStep 的私有方法。

页面条件用 Playwright locator 作即时探测，可见性以首个匹配元素为准，缺失视为隐藏；text_contains 使用 DOM 文本匹配及其空白归一化规则，不再查询 HTML 源码。条件入口不定义等待或轮询时序。

`browser_functions.py` 共享函数调用包装器，evaluate 与 js 谓词均通过独立 args 传递数据，保持无参数与显式 null 的区别；js 必须返回布尔值。错误保留条件节点路径。循环耗尽和统一报告不由条件模块接管。

### 4. 集合与重试边界

`foreach` 独立于 loop，使用 items/steps 和静态 as/index_as 标识符。进入时复制数组快照，按顺序串行执行，空数组执行零次；索引从 0 开始。loop 必须指定 times 或 while 之一，次数为非负整数，while 上限为正整数，max_iterations 不与 times 混用。foreach 不再注册为 loop 别名。

`StepContext.bindings` 持有当前嵌套集合的运行时绑定，独立于 scopes 配置定义。绑定优先于普通变量与 CLI，内层同名绑定遮蔽外层，退出恢复；普通变量仍遵循既有优先级。引用解析器将绑定作为不透明数据，完整引用、字段和下标不重新解释字符串，条件使用同样的绑定快照。每轮复制元素，回写结果不改变活动集合。

`_execute_with_retry()` 只执行单一步骤自身，`_execute_step()` 在重试完成后调度控制体；子步骤有各自重试边界。父控制步骤不会因子步骤失败重放已经完成的分支/迭代/写操作。集合通过 index-N 和子步骤路径定位错误，沿既有顶层失败证据路径传播，不新增报告契约或自动聚合结果。

### 5. 页面条件等待

`wait.condition` 直接消费共享条件树，literal_params 保留条件与 JS 原文。`wait_for_condition()` 在开始时复制运行时输入、结果及迭代绑定，实时观察页面；单一 page 条件使用 Locator.wait_for / Page.wait_for_url，URL 只等待 commit，单一 JS 条件使用共享严格布尔包装和 Page.wait_for_function，并释放句柄。

Playwright 原生轮询同步判断谓词返回值，包装器必须返回实际布尔值，不能直接返回 Promise。同步结果直接校验；异步结果保存在单次等待的参数对象上，pending 时返回 false，完成后仅 true 结束等待，false 继续，错误在下一次探测传播；不会并行发起未结束的调用。原生等待的 args 在传输边界统一使用 JSON 编码，每次调用解码，避免等待接口组装参数时递归删除 None，保留缺省/null 及嵌套 JSON 数据。

组合条件使用现有 evaluator，按 interval 重查，asyncio.timeout 将探测和等待限制在一个截止时间内；只有 false 才继续，错误立即传播。原生叶节点使用 Playwright 自身时限；组合探测通过 shield 保留在途 Playwright 调用，在外层超时/取消后消费迟到异常，避免取消协议 Future 后出现未取回异常。等待退出不强制终止页面用户函数，谓词应只观察页面。组合探测仅对明确的导航销毁执行上下文错误重试，关闭页面或业务 JS 错误不会转成未就绪。超时包括条件与时限，错误仍走顶层既有截图/页面/console/network 证据收集。

WaitStep 按字段存在性校验恰好一种原生模式，拒绝多模式、null 开关、非法枚举、字符串数字和无效范围；state、interval、route_stable_duration 限定对应模式。不做优先级适配或旧条件转换。animation_stable 使用 document.getAnimations() 观察运行中或 pending 的动画。页面等待不执行查询步骤、不更新结果，数据刷新轮询属于 T05。

### 6. 有界步骤轮询

`poll` 的 until 为原文共享条件树，steps 是非空延迟解析控制体；首次立即查询，每轮完整执行后获取新快照判断终止条件。interval 从未满足的一轮完成时起计算，不并发启动新查询。timeout 使用单调时钟，max_attempts 为可选附加上限；最后一轮条件满足仍成功。

`StepContext.polls` 传递各层 PollProgress。执行器在步骤、重试和探测前后检查最早截止时间；asyncio.timeout_at 覆盖控制体、条件、retry_delay 和 interval，原生 timeout 按剩余预算收紧。控制体仍在父步骤重试边界之外，poll 拒绝父 retry，只允许子查询显式重试。foreach 和分支保留作用域、绑定及预算。

在途单步骤和条件探测通过 shield 保留协议调用并消费迟到异常，结果发布和控制体调度留在调用端；超时后不开始新操作或发布迟到结果。页面 JS 和已经发出的浏览器操作可能继续完成，不提供副作用撤销或幂等性推断。

每次轮询体成功发布 save_as 时，为活动的各层轮询保存独立最近结果；失败重绑定仍按 T01 清除 runtime 绑定，但诊断保留之前成功的值。成功 poll 输出 attempts/elapsed_ms/results，可再次 save_as。PollError 沿嵌套路径保留各层诊断，顶层 failed_step.diagnostics.polls 包含条件、预算、阶段、路径和最近结果。on_error=continue 只影响是否继续调度，任何步骤失败后最终 success 仍为 false。

while 在 max_iterations 后再检查一次条件，false 正常完成、true 明确耗尽失败。固定 times 不变；不保留旧耗尽成功语义的适配。业务失败终态可以正常结束 poll，由后续分支或断言确定业务结果。

### 7. 浏览器会话 HTTP 请求

`request` 通过当前 `page.context.request.fetch` 复用 Cookie 及响应 Set-Cookie 更新，不创建独立客户端、不读取 localStorage token。使用标准 urljoin/urlsplit 解析相对地址，基准为当前 HTTP(S) page.url，与页面 base 标签无关；绝对 HTTP(S) 地址不要求页面已导航。请求不经过页面 fetch、CORS、page.route 或 Service Worker，重定向和查询参数处理使用 Playwright 契约。

字段在步骤执行时按现有 resolver 解析；query/headers 接受对象完整引用，子字段保留类型，运行前再次校验。query 的布尔值通过标准 JSON 序列化为小写 true/false，其他标量交给 Playwright 编码。json 使用标准序列化明确发送 null 与嵌套 JSON；GET/HEAD 禁止请求体，不增加 data/form/multipart 别名。缺省 GET/30000ms/json/2xx，expected_status 可声明整数或非空列表，先检查状态再读取响应。输出仅包含 url/status/headers/body，JSON 与 text 保持同一个结构，不自动解析降级。

asyncio.timeout_at 覆盖请求和响应读取，Playwright fetch 使用有限的原生 timeout；执行器现有逻辑按 poll 剩余预算收紧并阻止迟到结果发布。在途任务通过 shield 保留协议调用，强引用集合持有到完成，回调消费迟到异常；截止时间后不再解析迟到响应。APIResponse 在 finally 中释放，不销毁共享 APIRequestContext。错误分类为 RequestNetworkError/RequestTimeoutError/RequestStatusError/RequestResponseError，沿现有嵌套步骤定位和 CLI 失败出口传播；请求消息不主动输出头或 body。显式 retry 复用现有单步骤语义，默认没有请求重试；幂等性由调用方决定。

### 8. DOM 数据提取

`extract` 以 `page.locator(selector).evaluate_all` 取得根集合，在单个同步回调内检查匹配数并映射所有字段，没有跨字段 await。根 selector 使用 Playwright，行内字段使用浏览器原生 querySelectorAll 的相对 CSS（可用 :scope），不跨 iframe/Shadow DOM。字段配置作为结构化参数传入，不拼接数据到源码；无自动等待、DOM 写操作、转换语言或兼容分支。

one 默认严格单元素，all 按 DOM 顺序返回数组（可空）；无 fields 时返回读取值，有 fields 时返回 ASCII 字段名映射的对象。text 为 textContent，trim 仅去首尾；attribute 为原始属性，url 按 baseURI 解析，value 为 input/textarea/select 当前字符串。读取格式、属性、字段配置和 required/default 经静态及运行时校验；缺失默认失败，optional 返回明确 default 或 null，空串仍是值，多匹配始终失败。根的缺失配置不覆盖字段配置。

参数对象在传输边界编码为 JSON 字符串，浏览器回调内解码，避免 Playwright 的参数过滤递归省略 None 键，保留显式 null 默认值。原生读取错误转为 ExtractError，保留行与字段位置，沿既有嵌套路径和失败证据传播。结果使用 T01 JSON 快照与 save_as 契约，默认没有重试；poll 复用执行器既有总预算和迟到结果丢弃逻辑。快照只覆盖当前提取，不保证后续步骤仍观察到同一页面，页面就绪和类型转换由调用方表达。

### 9. 流程执行

`FlowExecutor` 负责加载、校验、执行流程：

- 加载 YAML 流程文件
- 递归校验步骤结构、局部输入及结果绑定声明
- 执行时解析参数；子流程及函数源码保持原文
- 逐步执行并收集结果

---

## CLI 命令

| 命令 | 功能 |
|------|------|
| `run` | 执行流程文件 |
| `validate` | 验证流程文件 |
| `install` | 安装 Playwright 浏览器 |
| `steps` | 列出可用步骤 |
| `spec <step>` | 查看步骤规范 |

---

## 步骤清单

| 步骤 | 必需参数 | 描述 |
|------|----------|------|
| `navigate` | `url` | 导航到 URL |
| `screenshot` | `file` | 截图 |
| `click` | `selector` | 点击元素 |
| `fill` | `selector`, `value` | 填充表单 |
| `type` | `selector`, `value` | 逐字输入 |
| `press` | `key` | 按键 |
| `wait` | - | 等待条件 |
| `scroll` | - | 滚动页面 |
| `hover` | `selector` | 悬停 |
| `select` | `selector`，`value`、`label` 或 `index` 三选一 | 按 HTML value、可见文本或从零开始的选项序号选择下拉选项 |
| `check` | `selector` | 勾选复选框 |
| `uncheck` | `selector` | 取消勾选 |
| `evaluate` | `script` | 执行函数表达式，可用 args 传参、save_as 绑定 JSON 输出 |
| `request` | `url` | 复用浏览器 Cookie，请求 JSON/文本并绑定 url/status/headers/body |
| `extract` | `selector` | 同步读取文本、属性、URL、表单值或映射对象数组 |
| `poll` | `until`, `steps` | 有界查询轮询，可用 save_as 绑定轮次、耗时和最近结果 |
| `set-viewport` | - | 设置视口 |

`select` 的 `value` 对应 option 的 HTML `value` 属性；`label` 对应用户可见的精确选项文本；`index` 对应从零开始的选项序号。三者必须且只能提供一个。

---

## 流程文件示例

```yaml
name: login-test
description: Login verification flow

variables:
  base_url: "http://localhost:3000"
  username: "admin"
  password: "admin123"

steps:
  - type: navigate
    url: "{{base_url}}/login"

  - type: screenshot
    file: "01-login.png"

  - type: fill
    selector: "input[name='username']"
    value: "{{username}}"

  - type: fill
    selector: "input[name='password']"
    value: "{{password}}"

  - type: click
    selector: "button[type='submit']"

  - type: wait
    url: "/dashboard"

  - type: screenshot
    file: "02-dashboard.png"
```

---

## 错误处理

- **默认中断**: 步骤失败立即终止流程
- **变量未声明**: 抛出 `UndefinedVariableError`
- **循环引用**: 抛出 `CircularReferenceError`
- **URL 校验**: 必须为绝对路径

---

## 使用方式

```bash
# 安装并运行
uvx pomelo-pw install
uvx pomelo-pw run flow.yaml

# 验证流程
uvx pomelo-pw validate flow.yaml

# 覆盖变量
uvx pomelo-pw run flow.yaml --var base_url=https://prod.example.com

# JSON 输出
uvx pomelo-pw run flow.yaml --json
```

---

## 开发命令

```bash
make install     # 安装依赖和浏览器
make test        # 运行测试
make lint        # 代码检查 (ruff + mypy)
make check       # 全部检查 (lint + test)
```

---

## 已确认决策

| 决策项 | 选择 |
|--------|------|
| 浏览器 | 仅 Chromium |
| 截图命名 | 用户指定 |
| 错误处理 | 默认中断 |
| 变量声明 | 必须显式声明 |
| 运行方式 | uvx |
