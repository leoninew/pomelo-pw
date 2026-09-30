# Pomelo PW - Flow-based UI Automation Tool
最后修改时间: 2026-09-30 13:41:27

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

### 3. 流程执行

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
