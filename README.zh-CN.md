# Pomelo PW

中文 | [English](README.md)

基于 Playwright 的流程化 UI 自动化工具。你可以用声明式 YAML 文件定义浏览器自动化流程，并获得类型安全的步骤校验和灵活的变量替换能力。

## 功能特性

- **声明式 YAML 流程**：用简单、可读的 YAML 定义 UI 自动化流程
- **类型安全步骤**：内置步骤参数校验
- **变量替换**：支持 `{{ var }}` 和 `${ var }` 语法，并提供多级优先级
- **丰富错误上下文**：失败时自动收集截图、HTML 快照、控制台错误和网络错误
- **增强 SPA 支持**：支持 URL 模式匹配、网络空闲、动画稳定、路由稳定等等待策略
- **步骤级重试**：支持按次数、延迟和错误类型自动重试
- **视觉回归测试**：支持截图基线对比和差异高亮
- **可扩展架构**：便于添加自定义步骤
- **开发模式**：源码运行时自动使用系统 Chrome，避免缓慢下载
- **丰富步骤库**：支持导航、点击、填写、输入、截图、滚动等常用操作

## 安装

```bash
# 安装 Playwright 浏览器（一次性设置）
uvx pomelo-pw install

# 开发模式
uv sync
uv run pomelo-pw install

# 可选：安装视觉回归测试支持
pip install pomelo-pw[visual]
# 或使用 uv
uv pip install pillow
```

## 快速开始

### 交互式工具

```bash
# 交互式探索页面，发现可用选择器
pomelo-pw explore https://example.com

# 录制用户操作并生成流程文件
pomelo-pw record https://example.com output.yaml
```

### 创建并运行流程

创建流程文件 `my-flow.yaml`：

```yaml
name: example-flow
description: Navigate and capture screenshots

variables:
  base_url: "https://example.com"

steps:
  - type: navigate
    url: "${base_url}"

  - type: screenshot
    file: "homepage.png"

  - type: scroll
    direction: down
    distance: 500

  - type: screenshot
    file: "scrolled.png"
```

运行流程：

```bash
uvx pomelo-pw run my-flow.yaml
```

## 使用方法

### 交互式工具

#### 页面探索器

交互式发现页面元素选择器：

```bash
# 启动探索器
pomelo-pw explore https://example.com

# 无头模式运行
pomelo-pw explore https://example.com --headless
```

**功能**：

- 鼠标悬停元素即可查看可用选择器
- 点击元素会在终端显示所有选择器选项
- 选择器优先级：data-test > id > role > text > class > css > xpath
- 页面实时显示选择器覆盖层

**适用场景**：

- 为元素寻找最佳选择器
- 理解页面结构
- 调试选择器问题
- 学习 Playwright 选择器语法

#### 流程录制器

录制用户操作并生成 YAML 流程：

```bash
# 录制流程
pomelo-pw record https://example.com output.yaml

# 无头模式运行
pomelo-pw record https://example.com output.yaml --headless
```

**可录制操作**：

- Click：自动记录点击事件
- Fill：记录表单输入
- Press：记录 Enter 按键

**功能**：

- 实时步骤计数
- 自动生成选择器，并选择最佳候选
- 生成干净的 YAML 流程文件
- 按 Ctrl+C 停止并保存

**输出示例**：

```yaml
name: output
description: Recorded flow from https://example.com
steps:
  - type: navigate
    url: https://example.com
  - type: click
    selector: role=button[name="Get started"]
  - type: fill
    selector: "#email"
    value: user@example.com
  - type: press
    selector: "#email"
    key: Enter
```

### 基础命令

```bash
# 运行流程（截图保存到以流程文件命名的 ./flow/ 目录）
pomelo-pw run flow.yaml

# 输出详细日志
pomelo-pw run flow.yaml -v

# 指定自定义输出目录
pomelo-pw run flow.yaml -o /custom/path

# 注意：输出目录名来自流程文件名，与路径无关
# 示例：flows/my-test.yaml → ./my-test/

# 覆盖变量
pomelo-pw run flow.yaml --var base_url=https://prod.example.com

# 输出 JSON
pomelo-pw run flow.yaml --json

# 只校验流程，不执行
pomelo-pw validate flow.yaml

# 列出所有可用步骤
pomelo-pw steps

# 查看步骤规格
pomelo-pw spec navigate
```

### 可用步骤

| 步骤 | 必填参数 | 说明 |
|------|----------|------|
| `navigate` | `url` | 跳转到 URL |
| `screenshot` | `file` | 截图 |
| `click` | `selector` | 点击元素 |
| `fill` | `selector`, `value` | 填写表单字段 |
| `type` | `selector`, `value` | 逐字符输入文本 |
| `press` | `key` | 按下键盘按键 |
| `wait` | - | 等待条件（选择器、URL、网络空闲、动画等） |
| `scroll` | - | 滚动页面 |
| `hover` | `selector` | 悬停元素 |
| `select` | `selector`, `value` | 选择下拉选项 |
| `check` | `selector` | 勾选复选框 |
| `uncheck` | `selector` | 取消勾选复选框 |
| `evaluate` | `script` | 执行 JavaScript |
| `set-viewport` | - | 设置视口尺寸 |
| `save-state` | `file` | 保存浏览器状态（cookies、localStorage） |
| `load-state` | `file` | 从文件加载浏览器状态 |

运行 `pomelo-pw spec <step>` 可查看详细参数信息。

### 增强等待步骤

`wait` 步骤支持多种 SPA 应用等待条件：

```yaml
# 等待选择器状态
- type: wait
  selector: ".content"
  state: "visible"  # visible, attached, detached, hidden

# 等待 URL 包含文本
- type: wait
  url_contains: "/dashboard"

# 等待 URL 匹配正则
- type: wait
  url_pattern: "^/user/\\d+$"

# 等待网络空闲
- type: wait
  network_idle: true

# 等待动画稳定
- type: wait
  animation_stable: true

# 等待路由稳定（URL 不再变化）
- type: wait
  route_stable: true
  route_stable_duration: 500  # ms

# 固定延迟
- type: wait
  delay: 2000  # ms
```

### 步骤级重试

任意步骤都可以在失败时自动重试：

```yaml
# 重试 3 次，每次间隔 1 秒
- type: click
  selector: ".flaky-button"
  retry: 3
  retry_delay: 1000

# 只针对特定错误类型重试
- type: fill
  selector: "input"
  value: "test"
  retry: 2
  retry_on:
    - "timeout"
    - "element_not_found"
```

### 登录状态复用

保存并复用浏览器状态（cookies、localStorage），避免重复登录：

```yaml
# 流程 1：登录并保存状态
name: login-flow
steps:
  - type: navigate
    url: "https://example.com/login"

  - type: fill
    selector: "input[name='username']"
    value: "{{username}}"

  - type: fill
    selector: "input[name='password']"
    value: "{{password}}"

  - type: click
    selector: "button[type='submit']"

  - type: wait
    url_contains: "/dashboard"

  # 保存认证状态
  - type: save-state
    file: "auth-state.json"

# 流程 2：复用状态（无需登录）
name: use-saved-auth
steps:
  - type: navigate
    url: "https://example.com"

  # 加载认证状态
  - type: load-state
    file: "auth-state.json"

  # 此时已处于登录状态
  - type: navigate
    url: "https://example.com/dashboard"
```

**收益**：

- 后续流程跳过登录
- 提升测试执行速度
- 降低认证服务器压力
- 在多个流程间共享登录状态

### 视觉回归测试

将截图与基线图对比，检测视觉变化：

```yaml
# 首次运行：创建基线
- type: screenshot
  file: "homepage.png"

# 后续运行：与基线对比
- type: screenshot
  file: "homepage-current.png"
  baseline: "homepage.png"
  threshold: 0.05  # 允许 5% 差异
  diff_output: "homepage-diff.png"
  fail_on_diff: false  # 不失败，只报告

# 严格对比（出现差异则失败）
- type: screenshot
  file: "critical-page.png"
  baseline: "critical-baseline.png"
  threshold: 0.01  # 只允许 1% 差异
  diff_output: "critical-diff.png"
  fail_on_diff: true
```

**参数**：

- `baseline`：基线图片路径（相对于输出目录）
- `threshold`：允许差异比例（0.05 = 5%）
- `diff_output`：差异图输出路径（红色高亮差异）
- `fail_on_diff`：差异超过阈值时是否让步骤失败

**依赖**：安装 Pillow 用于图片对比。

```bash
pip install pomelo-pw[visual]
# 或
uv pip install pillow
```

**适用场景**：

- 检测非预期 UI 变化
- 跨环境视觉一致性检查
- 样式回归测试
- 组件视觉测试

### 条件执行

根据条件执行步骤：

```yaml
# 检查元素是否存在
- type: if
  condition: "element_exists: .login-button"
  then:
    - type: click
      selector: ".login-button"
  else:
    - type: screenshot
      file: "already-logged-in.png"

# 检查元素是否可见
- type: if
  condition: "element_visible: .error-message"
  then:
    - type: screenshot
      file: "error-state.png"

# 检查 URL
- type: if
  condition: "url_contains: /dashboard"
  then:
    - type: screenshot
      file: "dashboard.png"

# JavaScript 表达式
- type: if
  condition: "document.querySelectorAll('.item').length > 5"
  then:
    - type: screenshot
      file: "many-items.png"
```

**条件类型**：

- `element_exists: selector`：元素存在于 DOM 中
- `element_visible: selector`：元素可见
- `element_hidden: selector`：元素隐藏或不存在
- `url_contains: text`：URL 包含指定文本
- `url_matches: pattern`：URL 匹配正则表达式
- `text_contains: text`：页面内容包含指定文本
- JavaScript 表达式：任意返回布尔值的有效 JS

**适用场景**：

- 处理不同页面状态
- 根据条件跳过步骤
- 实现分支逻辑
- 适配动态内容

### 循环执行

重复执行步骤：

```yaml
# 固定次数循环
- type: loop
  times: 5
  steps:
    - type: scroll
      direction: down
      distance: 500
    - type: wait
      duration: 300

# 条件循环（while）
- type: loop
  while: "element_visible: .load-more-button"
  max_iterations: 10
  steps:
    - type: click
      selector: ".load-more-button"
    - type: wait
      network_idle: true

# 嵌套循环
- type: loop
  times: 3
  steps:
    - type: loop
      times: 2
      steps:
        - type: screenshot
          file: "nested-{{outer}}-{{inner}}.png"
```

**参数**：

- `times`：循环次数（固定次数）
- `while`：每次循环前检查的条件
- `max_iterations`：while 循环安全上限（默认 100）
- `steps`：每轮循环执行的步骤

**适用场景**：

- 滚动分页内容
- 重复点击 “Load More” 按钮
- 测试重复交互
- 生成多张截图

### 组合模式

组合条件和循环，实现更复杂的流程：

```yaml
# 循环中嵌套条件
- type: loop
  times: 5
  steps:
    - type: if
      condition: "element_exists: .next-page"
      then:
        - type: click
          selector: ".next-page"
        - type: wait
          duration: 1000
      else:
        - type: screenshot
          file: "last-page.png"

# 条件中嵌套循环
- type: if
  condition: "element_visible: .gallery"
  then:
    - type: loop
      times: 10
      steps:
        - type: scroll
          direction: down
          distance: 300
```

### 数据驱动测试

用多组数据运行同一流程：

```yaml
name: login-test
variables:
  base_url: "https://example.com"

data:
  - _label: "user-alice"
    username: "alice@example.com"
    password: "pass1"
  - _label: "user-bob"
    username: "bob@example.com"
    password: "pass2"

steps:
  - type: navigate
    url: "{{base_url}}/login"
  - type: fill
    selector: "#email"
    value: "{{username}}"
  - type: fill
    selector: "#password"
    value: "{{password}}"
  - type: screenshot
    file: "login-{{username}}.png"
```

**工作方式**：

- `data` 中每一行都会独立运行全部步骤
- 行变量会覆盖同名的全局 `variables`
- 每行输出到独立子目录：使用 `_label` 值或 `row-N`
- `on_error: continue` 可在失败后继续运行剩余数据行（默认：`stop`）

**结果结构**：

```json
{
  "success": true,
  "data_driven": true,
  "rows_total": 2,
  "rows_passed": 2,
  "rows_failed": 0,
  "row_results": [
    {"row": "user-alice", "success": true, "...": "..."},
    {"row": "user-bob", "success": true, "...": "..."}
  ]
}
```

**适用场景**：

- 测试多个用户账号
- 验证不同语言或环境下的行为
- 对多个页面运行相同视觉检查
- 参数化回归测试

## 流程文件格式

```yaml
name: flow-name
description: Flow description

variables:
  var1: "value1"
  var2: "value2"

steps:
  - type: step-type
    param1: "${var1}"
    param2: "literal value"
```

### 变量替换

变量支持两种语法：

**推荐：`{{ }}` 语法**（不会与 JS/Shell 冲突）

```yaml
variables:
  api_token: "abc123"

steps:
  - type: evaluate
    script: "const token = '{{api_token}}'; fetch(`/api?token=${token}`)"
    # {{api_token}} 会被替换，${token} 会保留为 JS 模板字符串
```

**旧语法：`${ }`**（向后兼容，但应避免在脚本中使用）

```yaml
variables:
  base_url: "https://example.com"

steps:
  - type: navigate
    url: "${base_url}/login"
```

**注意**：如果字符串包含 `{{ }}`，则只处理 `{{ }}`。这可以避免与 JavaScript 模板字符串、Shell 变量等冲突。

变量优先级（三层）：

1. CLI 参数（`--var`）
2. 步骤级变量
3. 流程级变量

## 错误处理

步骤失败时，Pomelo PW 会自动收集丰富的错误上下文：

- **错误截图**：`./flow/error-step-N.png`
- **HTML 快照**：`./flow/error-step-N.html`
- **控制台错误**：浏览器 console 中的错误和警告
- **网络错误**：失败的 HTTP 请求（4xx、5xx）
- **当前 URL**：失败时页面 URL
- **可见文本**：页面文本前 500 个字符

**错误输出示例**：

```text
[3/5] click FAILED: Element not found: .submit-btn
  Screenshot saved: ./my-flow/error-step-3.png
  HTML snapshot saved: ./my-flow/error-step-3.html
  Console errors: 2
  Network errors: 1
  Current URL: https://example.com/login
```

**JSON 输出**包含完整错误上下文：

```json
{
  "success": false,
  "failed_step": {
    "index": 2,
    "type": "click",
    "error": "Element not found: .submit-btn",
    "context": {
      "url": "https://example.com/login",
      "screenshot": "./my-flow/error-step-3.png",
      "html_snapshot": "./my-flow/error-step-3.html",
      "console_errors": ["[ERROR] Failed to load resource"],
      "network_errors": [{"url": "/api/user", "status": 500}],
      "visible_text": "Login failed. Please try again.",
      "step_index": 2,
      "step_type": "click"
    }
  }
}
```

## 开发

```bash
# 安装依赖
make install

# 运行测试
make test

# 运行代码质量检查（格式化、lint、类型检查）
make check

# 运行示例流程
make example
```

### 开发模式

从源码运行时，Pomelo PW 会自动检测开发模式，并使用系统 Chrome，而不是下载 Playwright 的 Chromium。这可以显著加快环境设置速度。

## 项目结构

```text
pomelo-pw/
├── src/pomelo_pw/
│   ├── cli.py              # CLI 入口
│   ├── executor.py         # 流程执行引擎
│   ├── substitution.py     # 变量替换
│   ├── config/             # 配置管理
│   └── steps/              # 步骤实现
├── tests/                  # 单元测试
├── flows/                  # 示例流程
└── docs/                   # 文档
```

## 许可证

MIT
