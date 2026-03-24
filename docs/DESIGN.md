# Pomelo PW - Flow-based UI Automation Tool

## 项目概述

Pomelo PW 是一个基于 Playwright 的流程化 UI 自动化工具，从 typing-island/scripts 抽取核心能力成为独立工具。

**核心价值：**
- 声明式 YAML 定义 UI 自动化流程
- 类型安全的步骤规范与校验
- 可扩展的步骤处理器架构
- 灵活的变量替换系统
- 支持 Claude Code Skill 集成

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
├── flows/                   # 示例流程
└── docs/
    └── DESIGN.md
```

---

## 设计原则

### 配置分离

| 配置类型 | 位置 | 用途 |
|----------|------|------|
| **工具配置** | 内置默认值 | 浏览器行为、视口、超时等运行参数 |
| **流程配置** | `flow.yaml` | 变量定义、步骤序列 |
| **运行时配置** | CLI 参数 | 变量覆盖、输出路径 |

### 工作目录模型

```
用户工作目录/
├── flows/              # 流程定义（可选）
│   └── my-flow.yaml
└── output/             # 默认输出目录
    └── screenshots/
```

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

### 2. 变量替换

支持 `${var}` 语法，三级优先级：

```
CLI 参数 > 步骤级变量 > 流程级变量
```

### 3. 流程执行

`FlowExecutor` 负责加载、校验、执行流程：

- 加载 YAML 流程文件
- 校验步骤参数
- 变量替换
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
| `select` | `selector`, `value` | 选择下拉选项 |
| `check` | `selector` | 勾选复选框 |
| `uncheck` | `selector` | 取消勾选 |
| `evaluate` | `script` | 执行 JavaScript |
| `set-viewport` | - | 设置视口 |

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
    url: "${base_url}/login"

  - type: screenshot
    file: "01-login.png"

  - type: fill
    selector: "input[name='username']"
    value: "${username}"

  - type: fill
    selector: "input[name='password']"
    value: "${password}"

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