# 运行时与控制流程

[Skill 入口](../SKILL.md) | [模板索引](../templates.md)

根据任务需要阅读相关章节，用于步骤间数据传递、选择页面等待或查询轮询，以及组合分支和结果收集。

- [运行时数据](#runtime-data)
- [结构化条件](#structured-conditions)
- [页面就绪](#page-readiness)
- [循环与数组遍历](#loop---repeat-steps)
- [有界查询](#poll---bounded-queries)
- [重试](#step-level-retry)

<a id="runtime-data"></a>

## 运行时数据

完整引用保留 JSON 类型，例如 `{{name}}`、`{{item.path}}`、`{{inputs.filter}}` 和 `{{results.records[0].id}}`。路径支持标识符字段和非负数组索引。嵌入文本的引用只接受标量。需要按字面量写出模板起始符时使用 `\{{`。`inputs` 和 `results` 是保留的输入名称。

输入优先级：CLI/API 覆盖值 > 当前步骤变量 > 外层变量 > 数据行 > 流程变量。CLI `--var` 的值始终是字符串。

通过 `args` 将数据传入浏览器函数；脚本源码按字面量处理：
```yaml
- type: evaluate
  args:
    token: "{{api_token}}"
  script: "async ({token}) => { const response = await fetch(`/api?token=${encodeURIComponent(token)}`); return await response.json(); }"
  save_as: response
```

`${ }` 保留给 JavaScript 等宿主语言，不作为流程变量语法处理。

`save_as` 将成功步骤的公开 JSON 输出绑定为结果，目前 evaluate、extract、request、poll 和 foreach 支持此功能；通过 `{{results.response}}` 读取。嵌套步骤共享结果，不同数据行之间隔离。子步骤参数在执行时解析，局部变量不会泄漏到同级步骤。输入定义可以引用其他输入，循环引用会失败。结果不进行二次解析，即使字符串包含模板语法也保持原样。重新绑定会替换原结果；写入失败会清除旧绑定，但该步骤的参数仍可读取写入前的快照。

`evaluate.script` 必须是同步或异步函数表达式，并显式返回 JSON 数据；不返回数据时使用 `return null`。省略 args 表示不传参数，显式 null 表示传入一个 null 参数。不支持的值、非有限数值和循环数据会失败。旧的模块体脚本应改为函数，源码插值应改为 args；不提供兼容适配。

<a id="structured-conditions"></a>

## 结构化条件

```yaml
- type: if
  condition:
    page: {element_exists: ".cookie-banner"}
  then:
    - type: click
      selector: ".accept-cookies"
  else:
    - type: screenshot
      file: "no-banner.png"
```

每个条件都是仅包含一个操作符的对象：

- `eq: [left, right]` / `ne: [left, right]`：递归比较 JSON 值，不做类型转换；数值视为同一类型，但 `false` 与 `0` 不同。
- `in: [value, array]`：按相同的相等规则判断数组成员。
- `exists: "{{results.record.field}}"`：使用完整引用；已定义的 null、false、零和空值都视为存在。其他操作符遇到缺失引用会失败。
- `all: [condition, ...]` / `any: [condition, ...]`：非空列表，按顺序求值并短路；`not: condition` 对一个条件对象取反。
- `page: {element_exists: selector}`：还支持 `element_visible`、`element_hidden`、`url_contains`、`url_matches`（Python 正则搜索）和 `text_contains`（Playwright DOM 文本匹配）。
- `js: {script: "({record}) => record.enabled === false", args: {record: "{{results.record}}"}}`：返回布尔值的同步或异步函数；源码按字面量处理。

访问可选数据的字段前，先用 exists 判断是否存在。静态校验检查整棵条件树，运行时只解析实际访问的节点。页面探测立即执行；可见性判断使用第一个匹配项，不存在的元素视为隐藏。文本探测使用 Playwright 的空白归一化规则，不匹配 HTML 源码。JS 使用结构化 args，区分省略 args 与传入 null。旧的冒号字符串条件和裸 JS 表达式会被拒绝，不提供兼容适配。

<a id="page-readiness"></a>

## 页面就绪

只能选择一种 wait 模式。等待 SPA 就绪时，可在 condition 中组合多个状态判断：

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

条件树使用固定的运行时数据快照和实时页面状态。单个 page/JS 条件使用 Playwright 原生等待，组合条件在同一截止时间内检查。JS 必须返回布尔值，源码保持字面量，通过结构化 args 传参。false 表示继续等待，错误会立即使步骤失败。interval 只适用于 condition，state 只适用于 selector，route_stable_duration 只适用于 route_stable。时间值必须是有限正数，delay 可以为零；标志模式必须设置为 true。混用模式和字符串数值会被拒绝，不做适配。

```yaml
# 等待元素
- type: wait
  selector: ".dashboard"
  timeout: 5000

# 等待 URL
- type: wait
  url_contains: "/dashboard"

- type: wait
  url_pattern: "^/user/\\d+$"

# 等待网络或动画稳定
- type: wait
  network_idle: true

- type: wait
  animation_stable: true

- type: wait
  route_stable: true
  route_stable_duration: 500

# 固定延时
- type: wait
  delay: 1000
```

<a id="loop---repeat-steps"></a>

## loop - 重复执行步骤

```yaml
# 固定次数
- type: loop
  times: 5
  steps:
    - type: scroll
      direction: down
      distance: 300

# 按条件循环
- type: loop
  while:
    page: {element_visible: ".load-more"}
  max_iterations: 20
  steps:
    - type: click
      selector: ".load-more"
    - type: wait
      network_idle: true
```

## foreach - 数组遍历

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

进入 foreach 时对数组建立快照并串行遍历；空数组不执行子步骤。默认名称为 `item`/`index`，索引从零开始。别名必须是不同的、非保留的 ASCII 标识符。循环绑定优先于普通变量和 CLI 覆盖值，不进行二次解析，嵌套循环结束后恢复外层绑定。旧的 foreach times/while 用法必须改为 loop；loop 只能选择一种模式，次数必须为整数，max_iterations 只能与 while 一起使用。

可选的 collect 在每次成功迭代后，在该项作用域内解析一次。输出为 `{iterations, items}`；未配置 collect 时 items 为 []。使用 save_as 绑定输出。max_collect_items 默认为 1000，max_collect_bytes 默认为 1048576 个 JSON UTF-8 字节，包含数组结构开销；两者接受正整数引用，且必须同时配置 collect。超过限制会失败，不重放步骤，也不发布部分结果。collect 和子步骤源码在进入各自执行作用域前保持原样。

while 在最后一次允许的迭代结束后会再次检查条件：false 表示完成，true 表示次数耗尽并失败。不兼容旧的耗尽后仍成功行为。

<a id="poll---bounded-queries"></a>

## poll - 有界查询

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

非空的轮询体立即执行，随后 until 读取本轮的新结果。条件为 false 时，在本轮结束后等待 interval。timeout 默认为 30000ms，包含轮询体、条件求值、重试和延时；interval 默认为 1000ms。两者必须是有限正数，可选的 max_attempts 必须是正整数。所有限制参数支持保留类型的完整引用。嵌套 poll 不能延长父级截止时间。限制耗尽会失败，但最后一轮条件为 true 时仍成功。写操作应放在 poll 前，读取重试配置在子步骤上；poll 不接受父级重试参数。

成功输出为 `{attempts, elapsed_ms, results}`，包含轮询体最近成功绑定的结果。业务失败终态也可能满足 until，应在后续分支处理结果。失败详情位于 errors[].diagnostics.polls，包含嵌套路径和此前成功值，即使后续重新绑定失败也会保留。超时后不再启动新操作，迟到的结果会被丢弃；已经发起的浏览器操作可能继续完成，迟到的错误会被接收处理。即使设置 on_error=continue，只要有步骤失败，最终流程状态仍为失败。

<a id="step-level-retry"></a>

## 步骤级重试

操作步骤以及 if/loop/foreach 支持重试参数；poll 的重试必须配置在子步骤上。

if/loop/foreach 的重试只覆盖父步骤自身的探测或准备过程。子步骤失败不会重放已完成的分支或迭代；应在具体操作上配置重试。嵌套错误包含步骤路径和数组索引。

```yaml
- type: click
  selector: ".flaky-button"
  retry: 3
  retry_delay: 1000
  retry_on:
    - "TimeoutError"
```

`retry_on` 按异常类名进行不区分大小写的子串匹配。步骤返回失败的 StepResult 时，按重试次数执行，不应用异常过滤。上述示例针对 Playwright TimeoutError；request 失败使用 [HTTP 参考文档](browser-and-http.md#request---browser-session-http)中的 Request* 错误类。

完整的运行时和收集示例见[控制流程模板](templates-control.md)。
