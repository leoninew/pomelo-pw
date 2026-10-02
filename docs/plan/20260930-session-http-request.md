# T06 浏览器会话 HTTP 请求实施计划
最后修改时间: 2026-10-02 10:26:51

## Review status

Accepted

## Flow mode and stage

标准模式 / standard，Intent/Plan 已接受，Implementation 已交付。用户要求按顺序继续任务，沿用“没有未决事项就开始实现”的授权；本项已达到可用状态，当前停止供用户自行测试，不自动进入正式 Verification 或 T07。

## Intent basis

依据 [T06 Intent](../intent/20260930-session-http-request.md)，复用 T01 结果/引用与现有步骤重试，接受 T05 验收后接入统一轮询预算。T05 已由用户提交为 cc6cc24。

## Proposed contracts

```yaml
- type: request
  url: /api/tasks
  method: POST
  headers: {Authorization: "Bearer {{token}}"}
  json: {record_id: "{{record.id}}"}
  expected_status: 201
  save_as: submitted
- type: poll
  until: {in: ["{{results.task.body.status}}", [ready, failed]]}
  timeout: 30000
  interval: 1000
  steps:
    - type: request
      url: "/api/tasks/{{results.submitted.body.id}}"
      save_as: task
      retry: 2
      retry_delay: 250
      retry_on: [RequestNetworkError, RequestTimeoutError]
```

- request 必需非空 url；method 默认 GET，只接受 GET/HEAD/POST/PUT/PATCH/DELETE/OPTIONS。完整 HTTP(S) URL 可直接使用，相对 URL 通过标准 URL 解析以当前 page.url 为基准，忽略 HTML base 标签；相对地址要求当前页面为 HTTP(S)，about:blank 上可使用绝对地址。
- 使用 page.context.request.fetch，共享当前 BrowserContext Cookie 及响应 Set-Cookie 更新；不新建请求会话、不读取 localStorage token。不经过页面 fetch、CORS、页面路由拦截或 Service Worker；遵循 Playwright 请求的重定向行为，状态校验针对最终响应，输出最终 URL。
- query 为非空字符串键、字符串/有限数字/布尔值的对象；布尔值在 HTTP 查询中编码为小写 true/false，避免 Playwright Python 的 True/False。headers 为非空字符串键、字符串值的对象。参数支持嵌套引用和对象完整引用，解析结果按实际类型再次校验。重名 URL 查询参数遵循 Playwright params 语义。
- json 接受任意 JSON 值，显式 null 发送 JSON null，未声明则没有请求体；GET/HEAD 禁止声明 json。通过标准 JSON 序列化保留 null/布尔值并拒绝非有限数字；缺省 Content-Type 为 application/json，显式请求头可覆盖。没有 data/form/multipart 别名或旧 fetch 适配。
- response 默认 json，也可 text；不自动按 Content-Type 猜测或降级。JSON 空响应（包括 204/HEAD）及非法 JSON 失败，需要空/文本响应时显式选择 text。输出唯一为 {url, status, headers, body}，body 保持原始 JSON 类型或文本。
- expected_status 缺省接受 200-299，可声明单个 100-599 整数或非空整数列表；先检查状态再解析响应。HTTP 层成功不等于业务成功，业务状态由条件/分支消费 body。
- timeout 默认 30000ms，必须为正且有限的数字，覆盖请求及响应读取；纳入 T05 最早截止时间，继承剩余预算收紧及迟到结果不发布。请求在途任务使用 shield 保留协议调用，完成后释放响应并消费异常；截止时间后不继续解析迟到响应。释放每个 APIResponse 的缓存，不销毁共享 APIRequestContext。
- 网络失败、请求超时、HTTP 状态不符和响应解析失败分别使用 RequestNetworkError/RequestTimeoutError/RequestStatusError/RequestResponseError，沿现有步骤路径及 CLI 失败出口传播；不默认输出请求头、请求体或响应体。
- 不配置隐式请求重试。只有显式 retry 才会按现有单步骤策略重试，默认涉及所有执行错误，可用 retry_on 按错误类名筛选；写请求重试的幂等性由调用方负责，不自动重放提交。

## Implementation steps

1. 实现并注册 RequestStep，静态和解析后分别校验，接入结果绑定、重试和 poll 预算。
2. 增加请求/响应契约及嵌套控制、错误分类、重试与预算的针对性测试。
3. 提供无需外部服务的本地 HTTP fixture 与 session-http-request.yaml，演示 UI Cookie 登录、JSON 提交、相对查询轮询和文本响应。
4. 同步中英文 README、DESIGN、示例索引和本地插件说明/模板；不刷新用户级插件。
5. 运行变更文件格式/lint/类型检查和必要的针对性开发测试，不运行全量、覆盖率或真实材料业务；记录实现交付后停止。

## Files to change

- src/pomelo_pw/steps/request.py、steps/__init__.py。
- tests/test_request.py。
- example/public/session-http-request.yaml、example/support/session_http_server.py、example/README.md。
- README.md、README_CN.md、docs/DESIGN.md、plugins/pomelo-pw/skills/pomelo-pw/{SKILL.md,templates.md}。
- T06 Intent/Plan、系列入口和 T05 Intent/Plan/Verification 接受记录，仅同步上一任务阶段状态。

## Verification plan

正式验证由用户查看本次交付后决定。仅执行针对性回归和本地最小集成：会话 Cookie 复用与更新、相对/绝对 URL、类型化 query/header/json、JSON null、JSON/文本输出、状态/解析/网络/超时失败、显式读取重试与 poll 总预算、分支/foreach 延迟绑定。检查失败退出码与响应释放，不运行全量测试或外部站点。

## Blockers and assumptions

暂无需要用户确认的未决事项。按 Playwright 现有 API 实现，不引入 HTTP 依赖；query 不支持数组/对象/null，响应模式和状态列表为显式契约。示例服务只绑定本机回环地址，端口可配置，不接触相邻项目。

## Risks

- Cookie 共享不自动同步 localStorage token、CSRF token 或业务请求头；调用方需显式提供。
- Playwright API 请求不具有页面 fetch 的全部语义，特别是 CORS、页面拦截及重定向。使用相对 URL 前需有明确 HTTP(S) 页面。
- 超时不能撤销已发出的写操作；写请求显式重试可能重复提交，流程应将提交与查询轮询分开。
- 本地 fixture 只能验证声明式请求能力，不能代表真实业务认证或解析成功。

## Rollback

按本项 diff 移除 request 注册、实现、测试及示例/说明，不添加兼容适配，不执行 Git 写操作。

## Implementation handoff

- 已注册 request，支持绝对/相对 URL、method、类型化 query/headers/json、有限超时、显式状态检查和 JSON/文本响应；成功输出统一为 url/status/headers/body。
- 浏览器 Cookie 双向共享、不读取 localStorage token；query 布尔值明确编码为小写 true/false，JSON 的 null/false/0 和显式 Content-Type 均保留。GET/HEAD 禁止 json，没有旧 fetch 或旧结果适配。
- 网络/超时/状态/解析错误分别传播；复用子步骤显式 retry 与 poll 剩余预算，迟到响应不发布，在途协议任务消费迟到异常并释放响应。没有改动执行器、条件或浏览器生命周期。
- 新增 tests/test_request.py 与本地示例/回环 fixture；同步 README、DESIGN、本地插件说明和常用轮询模板。其他文件改动限于阶段状态及任务记录，没有功能范围偏差。
- 开发检查：4 个 Python 文件 Ruff 格式/lint/mypy 通过；uv run --locked --no-sync pytest tests/test_request.py tests/test_poll.py -q 最终 58 passed（0.59s）；新 YAML 静态校验通过。
- 本地 Chrome 最小试跑完成 9 个顶层步骤：UI 登录 Cookie 被 request 复用，响应 request_seen Cookie 回写浏览器，任务第二次查询 ready，文本输出 ready。截图 output/development-t06/20261002/session.png 已查看；临时服务使用系统分配的回环端口，试跑结束后关闭。
- 真实 HTTP 慢请求配置 50ms，实测约 62ms 返回 RequestTimeoutError；确认无迟到结果、残留请求任务或未处理事件循环异常。时限包含平台调度开销，不是硬实时保证。
- 首轮修正示例 fixture 的 lint/类型和测试时钟精度断言；真实试跑发现 Playwright 原生 query 布尔编码为 True/False，已明确并实现小写编码；请求自身时限使用 shield，避免取消在途协议 Future。修改后相关检查通过，没有遗留必须修复事项。
- 未运行全量测试、覆盖率、真实材料业务或外部站点，没有安装/同步用户级插件。尚未执行正式 Verification 的 CLI 失败验收；当前停在 Implementation，供用户自行测试，不创建本项 Verification，不执行 Git 暂存/提交，不自动推进 T07。

用户自行试跑：先在一个终端启动本地 fixture，再在另一终端运行 flow；端口被占用时改 --port，并给 flow 提供对应 --base-url。

```powershell
uv run --locked --no-sync python example/support/session_http_server.py --port 8766
```

```powershell
uv run --locked --no-sync pomelo-pw run example/public/session-http-request.yaml --headless -v
```

测试结束后 Ctrl+C 停止 fixture；以上只是可用性开发检查记录，不代替用户正式验收。

## User review notes

- 用户要求继续下一任务，沿用无未决事项时开始实现的授权；本项没有必须由用户决定的未决事项。
- 保留“达到可用状态后停止，用户自行测试”和“仅基本、针对性测试”的限制，不自动推进 T07。
