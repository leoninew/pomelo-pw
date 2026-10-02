# 浏览器与 HTTP 步骤

[Skill 入口](../SKILL.md) | [模板索引](../templates.md)

- [步骤概览](#step-overview)
- [输出路径](#output-directory)
- [下拉选项](#select---dropdown-options)
- [登录状态复用](#login-state-reuse)
- [HTTP 请求](#request---browser-session-http)
- [DOM 提取](#extract---dom-data-snapshot)
- [截图](#screenshot---baseline-comparison)

<a id="step-overview"></a>

## 步骤概览

| 步骤 | 主要参数 | 说明 |
|------|-----------|-------------|
| `navigate` | `url` | 导航到 URL |
| `screenshot` | `file` | 截图 |
| `click` | `selector` | 点击元素 |
| `fill` | `selector`, `value` | 填写表单字段，先清空原值 |
| `type` | `selector`, `value` | 逐字符输入 |
| `press` | `key` | 按下键盘按键 |
| `wait` | - | 等待条件满足 |
| `scroll` | `direction`, `distance` | 滚动页面 |
| `hover` | `selector` | 鼠标悬停在元素上 |
| `select` | `selector`，以及 `value` / `label` / `index` 中的一项 | 选择下拉选项 |
| `check` / `uncheck` | `selector` | 勾选或取消勾选复选框 |
| `evaluate` | `script`，可选 `args`、`save_as` | 执行使用 JSON 输入和输出的浏览器函数 |
| `request` | `url`，可选 method/query/headers/json/response | 共享浏览器 Cookie，返回 HTTP 响应数据 |
| `extract` | `selector`，可选 mode/read/fields | 读取 DOM 值或映射后的集合快照 |
| `set-viewport` | `width`, `height` | 设置视口尺寸 |
| `save-state` | `file` | 保存 Cookie 和 localStorage |
| `load-state` | `file` | 恢复已保存的认证状态 |
| `if` | `condition`, `then` | 条件执行 |
| `loop` | `steps`, `times`/`while` | 循环执行 |
| `poll` | `until`, `steps` | 在限制范围内反复查询，每轮读取新结果 |
| `assert` | `condition`，可选 `message` | 检查预期条件并记录观测值 |
| `foreach` | `items`, `steps`，可选 `as`、`index_as` | 串行遍历数组并绑定局部变量 |

<a id="output-directory"></a>

## 输出目录

截图默认保存到 `./<flow-name>/`，目录名由流程文件名派生。

- `example/my-test.yaml` -> `./my-test/`
- 在流程顶层设置 `output_dir`，支持 `{{variable}}` 替换。
- `output_dir` 在执行前解析，不能引用执行结果。
- 相对 `output_dir` 以命令工作目录为基准解析。
- 使用 `-o /custom/path` 覆盖流程中的目录值。
- 顶层布尔值 `headless` 控制是否以无界面模式运行，默认为 `false`。
- 使用 `--headless` 覆盖浏览器模式。

<a id="select---dropdown-options"></a>

## select - 下拉选项

提供 `selector`，并且只选择一种选项定位方式：

- `value`：选项的 HTML `value` 属性。
- `label`：选项的完整可见文本。
- `index`：选项从零开始的位置。

```yaml
# 有稳定的选项值时优先使用 value
- type: select
  selector: "#country"
  value: "cn"

# 没有稳定选项值时使用可见文本
- type: select
  selector: "#country"
  label: "China"

# 选项值由先前界面操作动态生成时，使用从零开始的位置
- type: select
  selector: "#course-adoption"
  index: 1
```

<a id="login-state-reuse"></a>

## 登录状态复用

登录成功后保存 Cookie（包括 HttpOnly）和 localStorage，不包含 sessionStorage 和 IndexedDB。每次执行都会创建新的 BrowserContext，不会自动加载上次会话。

```yaml
# 两个流程都使用 output_dir: output/auth
# 登录后保存状态
- type: save-state
  file: session.json
```

```yaml
# 在另一个流程中，先加载状态，再导航到应用
- type: load-state
  file: session.json
- type: navigate
  url: "{{base_url}}/dashboard"
```

`file` 相对于解析后的输出目录。不同 YAML 文件名对应不同的默认输出目录；两个流程应设置相同的 output_dir，或使用同一状态文件的绝对路径。`-o` 覆盖也会改变相对状态文件的解析位置。

状态文件缺失时 `load-state` 会失败；它不会检查服务端会话是否仍有效。应先执行登录和保存流程。恢复 localStorage 后，导航或刷新应用，使其读取恢复的值。如果会话过期导致应用跳转到登录页，使用条件登录分支并保存更新后的状态。

HTTP request 步骤共享恢复后的 Cookie。存放在其他位置的 Authorization 或 CSRF 值必须显式提供；localStorage 中的 token 不会自动转成请求头。见配套的[认证模板](templates-browser.md#auth-state-reuse)。

<a id="request---browser-session-http"></a>

## request - 使用浏览器会话的 HTTP 请求

```yaml
- type: request
  url: /api/tasks
  method: POST
  headers: {Authorization: "Bearer {{token}}"}
  json: {id: "{{record.id}}", enabled: false, metadata: null}
  expected_status: 201
  save_as: submitted
```

HTTP 查询优先使用 request。它共享当前 BrowserContext 的 Cookie 存储，包括响应带来的 Cookie 更新。相对 URL 以当前 HTTP(S) 页面 URL 为基准，不使用 HTML base；绝对 HTTP(S) URL 在 about:blank 页面也可使用。请求不经过页面 fetch、CORS、路由处理器和 Service Worker。额外的认证头必须显式提供，localStorage token 不会自动复制。重定向遵循 Playwright 行为，响应检查作用于最终响应。

默认方法为 GET，超时为 30000ms，响应模式为 response: json，接受任意 2xx 状态。方法必须大写，可用 GET/HEAD/POST/PUT/PATCH/DELETE/OPTIONS。query 的值为字符串、有限数值或布尔值，布尔值编码为小写 true/false；headers 的值必须为字符串。两者都使用非空字符串键，对象和嵌套字段支持保留类型的引用。json 可以是任意 JSON 值，包括 null，但不能与 GET/HEAD 一起使用；省略 json 时不发送请求体。未显式提供时，JSON Content-Type 默认为 application/json。expected_status 接受一个整数或非空整数列表，范围为 100-599。

输出为 `{url, status, headers, body}`，可通过 `{{results.task.body.status}}` 读取业务状态。response: text 用于文本或空响应；JSON 解析错误不会回退为文本。HTTP 成功不代表业务成功。请求超时也覆盖响应读取，并受 poll 剩余时间限制。已经发起的调用可能在超时后完成；迟到的响应会被释放，错误会被接收处理，输出会被丢弃。不进行隐式重试；显式 retry 可能重复写入，调用方需保证幂等性。retry_on 可过滤 RequestNetworkError/RequestTimeoutError/RequestStatusError/RequestResponseError。释放 API 响应不会关闭共享客户端。操作片段见随包提供的 [HTTP 模板](templates-data.md#browser-session-http-submission)。

<a id="extract---dom-data-snapshot"></a>

## extract - DOM 数据快照

```yaml
- type: extract
  selector: table tbody tr
  mode: all
  fields:
    id: {read: attribute, attribute: data-id}
    name: {selector: .name}
    url: {selector: a, read: url, attribute: href}
    status: {selector: .status, required: false, default: unknown}
  save_as: records
```

常见 DOM 读取使用 extract。它同步采集一次快照，不等待也不修改页面；应先通过 wait 明确就绪条件。根选择器使用 Playwright；字段选择器使用相对于当前行的 CSS，支持 :scope，不跨 frame 或 Shadow DOM 遍历。省略字段选择器时读取当前行。字段名必须是 ASCII 标识符。fields 和配置值支持保留类型的引用，并在执行时检查。

mode 默认为 one，严格要求单个根元素；all 按 DOM 顺序返回值或映射对象，无根元素时返回 []。未配置 fields 时直接读取根元素。read 默认读取 textContent 文本，trim 默认为 true，只去除首尾空白；false 保留原文本。attribute 读取原始字符串；url 必须指定 attribute，并以 element.baseURI 为基准解析，包括 HTML base。value 读取 input/textarea/select 的当前字符串值，不转换为数值或复选框状态，其他元素会失败。fields 不能与根级 read/attribute/trim 混用；trim 只适用于文本。

默认情况下，根元素、字段或属性缺失会失败。required: false 返回 null 或显式的 JSON default；配置 default 必须同时设置 required: false。空字符串是有效值，false/0/null 默认值会保留。根级配置不会覆盖字段配置。字段匹配到多个元素时始终失败，并给出行和字段位置；空的 all 仍返回 []。输出可直接用于 foreach、条件和 poll。重试需显式配置，poll 会丢弃迟到的快照，ExtractError 保留浏览器读取错误。见随包提供的 [DOM 模板](templates-data.md#dom-records-and-form-values)。不提供旧脚本的兼容适配。

<a id="screenshot---baseline-comparison"></a>

## screenshot - 基线比较

```yaml
# 截图
- type: screenshot
  file: "page.png"
  full_page: true

# 与基线比较
- type: screenshot
  file: "page-current.png"
  baseline: "page.png"
  threshold: 0.05        # 允许 5% 的差异
  diff_output: "diff.png"
  fail_on_diff: true
```

在 CLI 的执行环境中安装 Pillow：工具安装使用 `uv tool install "pomelo-pw[visual]" --force`，项目依赖使用 `uv add "pomelo-pw[visual]"`。

当前实现遇到基线缺失时会警告，但截图步骤仍成功，即使开启 fail_on_diff 也不会自动创建基线。应先显式采集基线，再比较。[基线模板](templates-browser.md#baseline-comparison)提供独立的采集模式，常规比较不会替换基线。

界面交互见[浏览器模板](templates-browser.md)，HTTP 和 DOM 流程见[数据模板](templates-data.md)。
