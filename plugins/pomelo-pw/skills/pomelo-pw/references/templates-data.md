# HTTP、DOM 与数据驱动模板

[Skill 入口](../SKILL.md) | [模板索引](../templates.md)

相对请求使用当前应用的 Cookie 会话。任务提交应放在 poll 前，只有应用能够保证幂等性时才重试写操作。

`<a id="browser-session-http-submission"></a>`

## 使用浏览器会话提交 HTTP 请求

```yaml
- type: request
  url: /api/tasks
  method: POST
  headers: {Authorization: "Bearer {{token}}"}
  json: {record_id: "{{record.id}}", metadata: null}
  expected_status: 201
  save_as: submitted
- type: request
  url: "/api/tasks/{{results.submitted.body.id}}"
  query: {details: true}
  save_as: task
```

使用相对 URL 和浏览器 Cookie 前，先导航或登录。响应内容位于 body，status 和 headers 单独保留。额外认证头必须显式提供。非 JSON 或空响应使用 response: text，提交操作放在 poll 外。重试需主动配置，可能重放写操作；读取重试可过滤 RequestNetworkError 和 RequestTimeoutError。

`<a id="dom-records-and-form-values"></a>`

## DOM 记录与表单值

```yaml
- type: wait
  condition: {page: {element_visible: 'table tbody tr'}}
  timeout: 5000
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
- type: foreach
  items: '{{results.records}}'
  as: record
  steps:
    - type: evaluate
      args: '{{record}}'
      script: 'record => record'
```

提取立即执行。根选择器使用 Playwright，字段使用相对于当前行的 CSS，不跨 frame 或 Shadow DOM 遍历。one 不接受多个根元素，all 允许为空。字段缺失时失败，除非设置 required: false，此时返回 null 或显式 JSON 默认值。字段匹配有歧义时始终失败。文本只去除首尾空白，表单值保持字符串。attribute 模式保留原始 href，url 模式以元素 baseURI 为基准解析，包括 HTML base。

## 数据驱动测试

`<a id="multi-user-test"></a>`

## 多用户测试

```yaml
name: multi-user-login
variables:
  base_url: "https://example.com"

data:
  - _label: "admin-user"
    username: "admin@example.com"
    password: "admin123"
    expected_page: "/admin"
  - _label: "regular-user"
    username: "user@example.com"
    password: "user123"
    expected_page: "/dashboard"

steps:
  - type: navigate
    url: "{{base_url}}/login"
  - type: fill
    selector: "#email"
    value: "{{username}}"
  - type: fill
    selector: "#password"
    value: "{{password}}"
  - type: click
    selector: "button[type='submit']"
  - type: wait
    url_contains: "{{expected_page}}"
  - type: screenshot
    file: "result.png"
```

`<a id="multi-environment-check"></a>`

## 多环境检查

```yaml
name: cross-env-check
data:
  - _label: "staging"
    base_url: "https://staging.example.com"
  - _label: "production"
    base_url: "https://example.com"

on_error: continue

steps:
  - type: navigate
    url: "{{base_url}}"
  - type: screenshot
    file: "homepage.png"
  - type: if
    condition:
      page: {element_exists: ".error-banner"}
    then:
      - type: screenshot
        file: "error-state.png"
```

---
