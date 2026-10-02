# 浏览器流程模板

[Skill 入口](../SKILL.md) | [模板索引](../templates.md)

按实际应用调整 URL 和选择器。这些模板用于编写流程，不能直接用于验证 example.com。

## 基础模板

<a id="simple-navigation-and-screenshot"></a>

## 简单导航与截图

```yaml
name: quick-capture
variables:
  url: "https://example.com"

steps:
  - type: navigate
    url: "{{url}}"
  - type: screenshot
    file: "capture.png"
```

<a id="login-flow"></a>

## 登录流程

```yaml
name: login-test
variables:
  base_url: "https://example.com"
  username: "user@example.com"
  password: "password123"

steps:
  - type: navigate
    url: "{{base_url}}/login"
  - type: fill
    selector: "input[name='email']"
    value: "{{username}}"
  - type: fill
    selector: "input[name='password']"
    value: "{{password}}"
  - type: click
    selector: "button[type='submit']"
  - type: wait
    url_contains: "/dashboard"
  - type: screenshot
    file: "logged-in.png"
```

<a id="responsive-testing"></a>

## 响应式检查

```yaml
name: responsive-test
variables:
  url: "https://example.com"

steps:
  - type: navigate
    url: "{{url}}"
  - type: set-viewport
    width: 1920
    height: 1080
  - type: screenshot
    file: "desktop.png"
  - type: set-viewport
    width: 375
    height: 667
  - type: screenshot
    file: "mobile.png"
```

<a id="form-submission"></a>

## 表单提交

```yaml
name: form-submit
variables:
  form_url: "https://example.com/contact"

steps:
  - type: navigate
    url: "{{form_url}}"
  - type: fill
    selector: "#name"
    value: "John Doe"
  - type: fill
    selector: "#email"
    value: "john@example.com"
  - type: check
    selector: "#agree-terms"
  - type: click
    selector: "button[type='submit']"
  - type: wait
    selector: ".success-message"
  - type: screenshot
    file: "submitted.png"
```

---

<a id="auth-state-reuse"></a>

## 认证状态复用

保存和复用流程应从同一工作目录执行，并使用下面统一的 output_dir。不同的默认输出目录不会共享 auth.json。先运行保存流程；状态加载不会检查是否过期。见[登录状态约定](browser-and-http.md#login-state-reuse)。

<a id="save-login-state"></a>

## 保存登录状态

```yaml
name: save-auth
output_dir: output/auth
variables:
  base_url: "https://example.com"
  username: "admin@example.com"
  password: "secret"

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
    url_contains: "/dashboard"
  - type: save-state
    file: "auth.json"
  - type: screenshot
    file: "logged-in.png"
```

<a id="reuse-login-state"></a>

## 复用登录状态

```yaml
name: test-with-auth
output_dir: output/auth
variables:
  base_url: "https://example.com"

steps:
  - type: load-state
    file: "auth.json"
  - type: navigate
    url: "{{base_url}}/dashboard"
  - type: screenshot
    file: "dashboard.png"
```

---

## 视觉回归

<a id="baseline-comparison"></a>

## 基线采集与比较

先通过 `--var baseline_mode=capture` 采集一次基线，后续运行省略该覆盖参数即可比较。采集模式写入基线，比较模式保留原基线。

```yaml
name: visual-regression
output_dir: output/visual-regression
variables:
  url: "https://example.com"
  baseline_mode: compare
steps:
  - type: navigate
    url: "{{url}}"
  - type: wait
    condition: {page: {element_visible: "body"}}
  - type: if
    condition: {eq: ["{{baseline_mode}}", capture]}
    then:
      - type: screenshot
        file: homepage-baseline.png
    else:
      - type: screenshot
        file: homepage-current.png
        baseline: homepage-baseline.png
        threshold: 0.02
        diff_output: homepage-diff.png
        fail_on_diff: true
```

当前实现中，缺少基线只会产生警告，不会失败或自动生成基线。比较前必须显式创建基线，并在 CLI 的执行环境中安装 visual 扩展依赖。

---

## SPA 与动态内容

<a id="spa-navigation-wait"></a>

## SPA 导航等待

```yaml
name: spa-test
variables:
  base_url: "https://app.example.com"

steps:
  - type: navigate
    url: "{{base_url}}"

  - type: click
    selector: "nav a[href='/dashboard']"

  - type: wait
    url_contains: "/dashboard"

  - type: wait
    network_idle: true

  - type: wait
    animation_stable: true

  - type: screenshot
    file: "dashboard.png"
```

<a id="flaky-element-with-retry"></a>

## 元素操作重试

```yaml
name: retry-example
variables:
  url: "https://example.com"

steps:
  - type: navigate
    url: "{{url}}"

  - type: click
    selector: ".async-button"
    retry: 3
    retry_delay: 1000

  - type: wait
    selector: ".result"
    timeout: 10000
    retry: 2

  - type: screenshot
    file: "result.png"
```

---

<a id="common-selector-patterns"></a>

## 常用选择器写法

```yaml
# 按 ID 定位
selector: "#submit-button"

# 按角色定位，优先用于交互元素
selector: "role=button[name='Submit']"
selector: "role=textbox[name='Email']"
selector: "role=link[name='Sign in']"

# 按文本定位
selector: "text=Accept all cookies"

# 按 data-test 属性定位，适合自动化测试
selector: "[data-testid='submit-btn']"
selector: "[data-test='login-form']"

# 按 CSS 定位
selector: "button[type='submit']"
selector: "input[name='email']"
selector: ".modal .close-button"
```
