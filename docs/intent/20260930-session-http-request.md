# T06 浏览器会话 HTTP 请求
最后修改时间: 2026-09-30 12:50:26

## Review status

Draft

## Task metadata

- 流程：标准模式 / standard，意图阶段 / Intent。
- 优先级：P1；依赖：[T01](20260930-runtime-result-context.md)；工作量：1-2 人日。
- 系列入口：[P0/P1 流程能力任务系列](20260930-p0-p1-flow-capabilities.md)。

## Background

现有业务脚本反复使用 fetch、HTTP 状态检查及 response.json()。这些是通用请求操作，但每段脚本都要自行处理 URL、会话、响应和错误。

## Goals

- 增加可声明的 HTTP 请求能力，复用当前浏览器会话的 Cookie。
- 支持必要的 method、URL、查询参数、请求头、JSON 请求体、超时及响应校验。
- 将响应状态、必要元数据和结构化内容作为步骤输出，供条件、轮询和断言消费。

## Non-goals

- 不新增认证服务集成，不自动推断或读取 localStorage token。
- 不提供文件上传下载、流式响应、GraphQL 专用语法或独立 HTTP SDK。
- 不把 HTTP 写操作默认纳入自动重试。

## User scenarios

- 通过 UI 完成登录后，查询记录最新状态或任务详情，并将 JSON 响应保存为结果。
- 调用方显式提供所需请求头或 JSON 参数，后续步骤引用返回的 ID。

## Acceptance

- 请求复用浏览器 Cookie；请求头和 JSON 参数可引用结构化运行时数据。
- 相对 URL 的解析基准明确，完整 URL 继续可用；不通过拼接 JS 源码执行请求。
- 输出包含可引用的状态码及 JSON 或文本内容，JSON 解析错误和不符合期望的状态码明确失败。
- 支持有限请求超时，查询重试与 T05 总预算的组合行为可验证。
- 网络失败、HTTP 状态不符和响应解析失败能够区分并定位到步骤。
- 默认不自动重试写请求，显式配置的重试语义在文档中说明。
- validate 能校验请求参数的类型与互斥关系，新增请求不承担旧 fetch 脚本的自动转换或适配。

## Open questions

暂无必须由用户决定的未决事项。默认响应模式、期望状态码配置及相对 URL 基准在 Plan 中明确；页面 fetch 的 CORS 行为与 Playwright 请求行为的差异需要说明。

## Decisions

- 使用 Playwright 当前 BrowserContext 的请求能力，复用现有依赖和浏览器生命周期。
- 会话复用仅承诺 Cookie 范围，额外认证头由调用方显式提供。
- 使用唯一的请求与输出契约，不提供旧脚本或旧结果格式的兼容层。

## Risks

Playwright 请求并非页面 fetch 的所有语义完全等价。URL、缓存、Cookie 更新和状态校验必须明确，不能把请求成功与业务操作成功混为一谈。

## User review notes

依据用户对 P0/P1 的任务拆分要求创建，等待意图审阅。
