# 流程参考

[返回首页](../README_CN.md) | [使用指南](USAGE_CN.md) | [English](FLOW_REFERENCE.md)

本文定义 YAML 的数据与执行契约。运行命令、登录状态复用和 Python API 见[使用指南](USAGE_CN.md)；内部实现见[架构设计](DESIGN.md)。

- [步骤概览](#步骤概览)
- [运行时数据](#运行时数据)
- [结构化条件](#结构化条件)
- [页面条件等待](#页面条件等待)
- [有界步骤轮询](#有界步骤轮询)
- [浏览器会话 HTTP 请求](#浏览器会话-http-请求)
- [DOM 数据提取](#dom-数据提取)
- [集合遍历](#集合遍历)
- [断言与执行报告](#断言与执行报告)

## 步骤概览

| 步骤 | 主要参数 | 用途 |
| --- | --- | --- |
| `navigate` | `url` | 打开页面 |
| `click`、`hover`、`press` | `selector` 或 `key` | 与元素或键盘交互 |
| `fill`、`type` | `selector`、`value` | 输入文本 |
| `select` | `selector`，`value`、`label` 或 `index` 三选一 | 按 HTML value、可见文本或从零开始的选项序号选择选项 |
| `wait` | 选择器、URL、网络或时间条件 | 与动态 UI 同步 |
| `screenshot` | `file` | 截取页面或元素，可选基线对比 |
| `check`、`uncheck` | `selector` | 控制复选框 |
| `save-state`、`load-state` | `file` | 复用已认证的浏览器状态 |
| `if`、`loop` | 条件或迭代配置 | 表达分支和重复操作 |
| `poll` | `until`、`steps` | 在统一时限内刷新数据并检查终态 |
| `assert` | `condition`，可选 `message` | 检查明确的预期并报告观察值 |
| `foreach` | `items`、`steps`，可选 `as` / `index_as` | 遍历数组，提供局部元素和索引绑定 |
| `evaluate` | `script`，可选 `args` 和 `save_as` | 执行页面函数并传递 JSON 数据 |
| `request` | `url`，可选 method/query/headers/json/response | 共享浏览器 Cookie 并绑定 HTTP 响应 |
| `extract` | `selector`，可选 mode/read/fields | 读取 DOM 值或映射记录数组 |
| `scroll`、`set-viewport` | 各步骤参数 | 调整滚动位置或视口 |

```bash
pomelo-pw steps
pomelo-pw spec wait
pomelo-pw spec select
```

## 运行时数据

完整引用保留 JSON 原生类型：`{{name}}`、`{{item.path}}`、`{{inputs.filter}}`、`{{results.records[0].id}}`。引用嵌入文本时只接受标量，布尔、数字和 null 使用 JSON 文本形式；对象和数组不能拼入文本。路径支持标识符字段和非负数组下标。用 `\{{` 表示字面量模板开头；`${name}` 保持原样。

```yaml
steps:
  - type: evaluate
    script: "() => [{id: 'a', enabled: false}]"
    save_as: records
  - type: evaluate
    args: "{{results.records[0]}}"
    script: "async (record) => ({id: record.id, enabled: record.enabled})"
    save_as: selected
```

`evaluate.script` 必须是同步或 async 函数表达式，源码保持原文。通过 `args` 传递单个 JSON 载荷；未提供 args 时不传参数，`args: null` 则传入一个 null 参数。函数必须明确返回 JSON 值，不需要数据时可 `return null`；不支持的类型、非有限数字和循环数据会报错。

只有产生公开输出的步骤支持 `save_as`，当前为 `evaluate`、`extract`、`request`、`poll` 和 `foreach`。成功后保存结果快照，再次成功写入会覆盖。替换时参数可以读取上一次值，但失败会使该绑定失效。嵌套步骤共享结果，data 行之间隔离。子步骤执行时才解析参数，子步骤局部变量不会泄漏给兄弟步骤。结果字符串始终作为数据，不重新解释为模板。`output_dir` 在运行前解析，只能读取输入。

流程必须遵循当前契约，不提供旧语法兼容适配。可运行[离线数据示例](../example/public/runtime-results.yaml)。

## 结构化条件

`if.condition` 和 `loop.while` 使用同一条件对象，每个节点恰好包含一个操作符：

```yaml
- type: if
  condition:
    all:
      - exists: "{{results.record.enabled}}"
      - eq: ["{{results.record.enabled}}", false]
      - in: ["{{results.record.status}}", [ready, completed]]
      - page: {element_visible: "#submit"}
  then:
    - type: click
      selector: "#submit"
```

`eq`/`ne` 递归比较两个 JSON 值，不隐式转换：`1` 与 `1.0` 相等，`false` 与 `0` 不同。`in: [值, 数组]` 使用相同比较规则。`exists` 只接受一个完整引用，检查路径是否可读取；已定义的 null、false、零和空值都存在，其他判断中的缺失引用会失败。`all`/`any` 接收非空数组并按顺序短路，`not` 接收一个条件对象。可选字段先用 exists 保护，再比较其值。

`page` 支持 `element_exists`、`element_visible`、`element_hidden`、`url_contains`、`url_matches`（Python 正则 search）和 `text_contains`（Playwright DOM 文本匹配）。可见性以首个匹配元素为准，缺失元素视为隐藏。这些是即时探测，不自动等待或轮询。文本匹配遵循 Playwright 空白归一化规则，不再搜索 HTML 源码。

自定义谓词使用 `js: {script: "({flag}) => flag === false", args: {flag: "{{results.record.enabled}}"}}`。同步或 async 函数必须返回布尔值；源码保持原文，未提供 args 与 null 的区别和 evaluate 相同。每次探测获取最新输入及结果快照，while 在每轮循环体执行前重新判断。静态校验检查整棵条件树，运行时只解析实际访问的节点。旧冒号字符串和裸 JS 表达式直接拒绝，不提供兼容适配。可直接运行[离线条件示例](../example/public/structured-conditions.yaml)。

## 页面条件等待

```yaml
- type: wait
  condition:
    all:
      - page: {url_contains: "/items?page=2"}
      - page: {element_visible: "table tbody tr"}
      - js:
          script: "({id}) => !document.querySelector('table').inert && document.querySelector('tr').dataset.id === id"
          args: {id: "{{record.id}}"}
  timeout: 5000
  interval: 100
```

`wait.condition` 使用与 if/while 相同的条件树及严格布尔 JS 契约。已经满足时立即完成，未满足时在统一截止时间内重复检查，单次 async 探测也受超时约束；谓词错误立即失败。单个 page/JS 条件使用 Playwright 原生等待，组合条件使用固定输入/结果/迭代绑定快照观察实时页面。interval 控制组合条件和 JS 谓词的检查间隔，单个 page 条件使用 Playwright 内置探测节奏。仅等待 URL 不能保证列表已刷新。可直接运行[离线等待示例](../example/public/page-condition-wait.yaml)。

每个 wait 必须且只能选择 condition、delay、selector、url、url_contains、url_pattern、for、network_idle、animation_stable 或 route_stable 之一。interval 仅用于 condition（默认 100ms），state 仅用于 selector，route_stable_duration 仅用于 route_stable。timeout 默认 30000ms；时间参数为正且有限的数字，delay 可以为 0。支持完整类型化引用，拒绝字符串数字和布尔值；开关模式必须为 true。混合模式直接校验失败，没有适配。动画稳定改为观察正在运行的 Web Animations，不根据 CSS 声明时长判断。

## 有界步骤轮询

```yaml
- type: poll
  until: {in: ["{{results.task.body.status}}", [ready, failed]]}
  timeout: 30000
  interval: 1000
  max_attempts: 20
  save_as: polling
  steps:
    - type: request
      url: "/api/tasks/{{results.submitted.body.id}}"
      save_as: task
      retry: 2
      retry_delay: 250
```

`poll` 立即执行非空轮询体，再使用本轮新结果判断 until；false 时从本轮完成起等待 interval，然后再查询。timeout 默认 30000ms，interval 默认 1000ms，均为正且有限的数字；可选 max_attempts 为正整数，均支持完整类型化引用。总时限覆盖步骤、条件、子步骤重试和等待，嵌套轮询不能延长外层预算。耗尽明确失败，最后一轮恰好满足时正常成功。

读取重试在对应子步骤声明，poll 拒绝自身 retry 参数。业务失败终态可以满足 until，之后通过分支判断业务结果。可选 save_as 保存 `{attempts, elapsed_ms, results}`，results 为轮询体最近成功发布的绑定。失败时将最近结果、条件、时限、阶段及嵌套路径保留在 `errors[].diagnostics.polls`。`on_error: continue` 继续后续步骤，但最终仍报告流程失败。

提交操作放在轮询之前。超时后不启动新步骤或重试，不发布迟到结果；已经发出的浏览器操作可能继续完成，迟到异常会被消费，轮询不撤回副作用。可自行运行[离线轮询示例](../example/public/bounded-step-polling.yaml)。

## 浏览器会话 HTTP 请求

```yaml
- type: request
  url: /api/tasks
  method: POST
  headers: {Authorization: "Bearer {{token}}"}
  json: {record_id: "{{record.id}}", enabled: false, metadata: null}
  expected_status: 201
  save_as: submitted
- type: request
  url: "/api/tasks/{{results.submitted.body.id}}"
  query: {details: true}
  save_as: task
```

`request` 使用当前 BrowserContext 的请求客户端，共享浏览器 Cookie 及响应 Cookie 更新。相对 URL 以当前 HTTP(S) 页面 URL 为基准，不读取 HTML base 标签；绝对 HTTP(S) 地址也可在 about:blank 上使用。请求不经过页面 fetch、CORS、页面 route 拦截或 Service Worker。重定向遵循 Playwright 行为，状态检查和输出针对最终响应。额外认证/CSRF 请求头由调用方显式传入，不自动复制 localStorage token。

默认 method 为 GET、timeout 为 30000ms、response 为 json，接受全部 2xx 状态。method 只接受大写 GET/HEAD/POST/PUT/PATCH/DELETE/OPTIONS。query 为非空字符串键与字符串/有限数字/布尔值的对象，布尔值编码为小写 true/false；headers 为非空字符串键与字符串值的对象。对象和字段都支持类型化引用，解析后再次校验。json 接受任意 JSON 值，显式 null 发送 JSON null，省略则不发送请求体；GET/HEAD 禁止 json。JSON 请求的缺省 Content-Type 为 application/json，可显式覆盖。

输出唯一为 `{url, status, headers, body}`，通过 `{{results.task.body.status}}` 读取 JSON 字段。文本或空响应（包括 HEAD/204）选择 `response: text`；空/非法 JSON 明确失败，不自动降级。expected_status 可指定单个 HTTP 状态整数或非空整数列表（100-599），先检查状态再解析。HTTP 成功不等于业务成功。

请求超时覆盖网络及响应读取，并按 poll 剩余预算收紧。在途协议调用可能在超时后完成；迟到响应被释放、异常被消费、输出被丢弃。读取后释放响应缓存，不销毁共享客户端。失败分别为 RequestNetworkError、RequestTimeoutError、RequestStatusError 和 RequestResponseError。不默认重试；显式 retry 使用现有单步骤策略，可用 retry_on 按错误类名筛选。写请求的幂等性由调用方负责。可运行[本地会话请求示例](../example/public/session-http-request.yaml)，服务启动方式见[示例说明](../example/README.md#browser-session-http-requests)。

## DOM 数据提取

```yaml
- type: extract
  selector: table tbody tr
  mode: all
  fields:
    id: {read: attribute, attribute: data-id}
    name: {selector: .name}
    raw_href: {selector: a, read: attribute, attribute: href}
    url: {selector: a, read: url, attribute: href}
    status: {selector: .status, required: false, default: unknown}
  save_as: records
- type: extract
  selector: '#page-size'
  read: value
  save_as: page_size
```

`extract` 在单次同步 DOM 快照中读取，不等待或修改页面；先用 wait 声明就绪条件。根 selector 使用 Playwright，字段 selector 为相对于该行的 CSS，支持 `:scope`，不跨 iframe 或穿透 Shadow DOM。省略字段 selector 则读取该行自身。字段名为 ASCII 标识符；fields 对象与配置值支持类型化引用，执行时再次校验。

默认 `mode: one` 返回单值或字段对象，多个根匹配失败；`mode: all` 按 DOM 顺序返回数组，无匹配返回 `[]`。未配置 fields 时直接读取根元素。默认 `read: text` 使用 textContent，包含隐藏文本；默认 `trim: true` 只去掉首尾空白，内部空白保留，false 保留原文。`read: attribute` 必须配置 attribute，返回原始属性；`read: url` 也必须配置 attribute，按元素 baseURI（包含 HTML base）解析绝对 URL。`read: value` 返回 input/textarea/select 当前字符串值，不转数字或复选框布尔状态；其他元素失败。fields 不与同层 read/attribute/trim 混用，trim 只用于 text。

单根、字段元素或属性缺失默认失败；显式 `required: false` 返回 null，也可配置任意 JSON default（只允许与 required: false 同用）。空串是有效值，false/0/null 默认值保持原类型。字段多匹配始终失败，错误包含行序号和字段位置；根 required/default 不覆盖字段自己的设置，空 all 集合仍为 []。结果可直接供 foreach、条件和 poll 使用；仅显式重试，poll 超时丢弃迟到快照。可运行[离线提取示例](../example/public/dom-data-extraction.yaml)。

## 集合遍历

```yaml
- type: foreach
  items: "{{results.records}}"
  as: record
  index_as: position
  steps:
    - type: evaluate
      args: {record: "{{record}}", index: "{{position}}"}
      script: "payload => payload"
```

`foreach` 按顺序遍历 JSON 数组快照，空数组不执行子步骤。`as` 默认为 `item`，`index_as` 默认为 `index`，索引从 0 开始；名称必须是不同的非保留 ASCII 标识符。迭代绑定优先于普通变量和 CLI 覆盖，数据不会再次解析成模板；内层循环退出后恢复外层绑定。回写源结果不会改变本次遍历范围。可直接运行[离线集合示例](../example/public/collection-iteration.yaml)。

`loop` 必须且只能提供 `times`（非负整数）或 `while`；`max_iterations` 为正整数，仅允许与 while 使用。次数和上限支持完整类型化引用。最后一轮结束后重新判断 while：false 正常完成，仍为 true 则耗尽失败，不适配原成功退出语义。原 foreach 次数/条件调用必须改用 loop。父 if/loop/foreach 的 retry 仅覆盖自身判断或准备，子步骤失败不会重放已经完成的控制体；需要重试的操作应在对应子步骤声明。嵌套错误包含步骤路径和集合索引。

## 断言与执行报告

```yaml
outputs:
  outcomes: '{{results.collected.items}}'
report:
  steps: true
steps:
  - type: foreach
    items: '{{records}}'
    as: record
    collect: '{{results.outcome}}'
    save_as: collected
    steps:
      - type: evaluate
        args: '{{record}}'
        script: 'record => ({id: record.id, category: "processed"})'
        save_as: outcome
  - type: assert
    condition: {eq: ['{{results.collected.items[0].category}}', processed]}
    message: Unexpected processing result
```

`assert` 复用统一条件树与短路语义。false 抛出 AssertionFailed，保留条件、访问过的操作数和探测结果；求值错误仍是执行错误。没有隐式等待或重试。message 为非空字符串，默认为 Assertion failed。

`foreach.collect` 在每项完整成功后解析一次，读取该项绑定和当前结果，输出 `{iterations, items}`；没有 collect 时 items 为空。默认 max_collect_items=1000、max_collect_bytes=1048576（JSON UTF-8 字节，含数组括号和分隔符），均支持正整数完整引用且仅与 collect 同用。超限明确失败，不重放控制体，不发布部分集合。

顶层 `outputs` 从结束时的固定运行时快照显式导出命名 JSON 值，键为 ASCII 标识符。缺失或非法引用追加 output 错误，其他字段继续导出。输出中的 failed 等业务分类不影响执行状态，应通过 assert 声明失败政策。

`run --json` 的 stdout 只有一个 JSON 文档，执行日志写入 stderr；成功退出 0，失败退出 1。API/CLI 统一结构为 schema_version=1、status=passed/failed、flow、duration_ms、outputs、steps={total,executed,completed}、trace={enabled,entries,dropped}、errors、errors_dropped、artifacts={screenshots}、rows、row_summary。steps 统计顶层调度次数与成功完成数；错误包含 path/type/kind/error_type/message/diagnostics/evidence，continue 保留多次失败。嵌套路径沿用 index-N/iter-N/attempt-N。旧 success/failed_step 等字段移除，不提供适配。`validate --json` 保留独立 valid/errors 契约。

详细轨迹默认关闭：report 缺省 steps=false、max_steps=1000、include_outputs=false、max_value_bytes=16384、max_errors=100。include_outputs 需要开启 steps。重试只记录逻辑步骤最终状态，控制步骤耗时覆盖子步骤执行。超出轨迹或错误数量统计 dropped；大值标记 `{omitted: true, bytes: ...}`，消息截断有明确标记，显式业务导出不静默截断。每个 data 行带独立报告及 label/index，各自导出 outputs，不自动公开行输入；顶层 row_summary 汇总 total/executed/passed/failed，合并后的错误和轨迹也有上限，并包含行定位。

可运行[离线断言与报告示例](../example/public/flow-assertions-results.yaml)。

完整组合可运行[本机能力串联示例](../example/README.md#integrated-flow-capabilities)：采集分页 DOM 数据、恢复浏览器 Cookie 状态、串行处理任务并导出可与服务审计核对的结果。mixed、empty、read-error、timeout 为确定性场景，业务失败是否使流程失败由显式断言政策决定。
