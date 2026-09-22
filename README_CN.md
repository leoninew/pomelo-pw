# Pomelo PW

[![CI](https://github.com/leoninew/pomelo-pw/actions/workflows/ci.yml/badge.svg)](https://github.com/leoninew/pomelo-pw/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/pomelo-pw)](https://pypi.org/project/pomelo-pw/)
[![GitHub Release](https://img.shields.io/github/v/release/leoninew/pomelo-pw)](https://github.com/leoninew/pomelo-pw/releases)

[English](README.md) | [简体中文](README_CN.md)

Pomelo PW 是一个基于 Playwright 的浏览器自动化 CLI。它通过声明式 YAML flow 执行浏览器操作，让 UI 检查可以与应用代码一起维护，而不需要定制测试框架。

它适用于可重复的 UI 检查、脚本化工作流、视觉对比和由 Agent 协助的浏览器任务。Flow 会在执行前校验参数；步骤失败时，自动收集截图、页面快照、控制台错误和网络失败信息。

## 能力概览

- 支持 `{{variable}}` 变量替换和 CLI 覆盖的 YAML flow
- 覆盖导航、表单、等待、截图、状态复用、条件和循环的浏览器步骤
- 用于发现选择器和生成初始 flow 的交互式 explorer 与 recorder
- 步骤级重试、数据驱动执行和截图基线对比
- 面向 Claude Code、Codex 和 Grok Build 的原生插件打包

## 安装

Pomelo PW 需要 Python 3.12+ 和 [uv](https://docs.astral.sh/uv/)。

Python 软件包已发布到 [PyPI](https://pypi.org/project/pomelo-pw/)，Windows、macOS 和 Linux 独立可执行文件可从 [GitHub Releases](https://github.com/leoninew/pomelo-pw/releases) 下载。

```bash
# 安装已发布的 CLI，再安装浏览器
uv tool install pomelo-pw
pomelo-pw install

# 或仅运行一次已发布的软件包，不安装 CLI
uvx pomelo-pw install

# 从源码检出目录运行
uv sync --all-groups --locked
uv run pomelo-pw install
```

对于软件包安装，`install` 命令会下载 Playwright Chromium。在源码检出目录或独立二进制中运行时，Pomelo PW 会在可用时使用本机已安装的 Chrome 或 Chromium。

仅当 flow 使用截图基线时，才需要安装视觉对比支持：

```bash
uv pip install pillow
```

## 快速开始

创建 `smoke.yaml`：

```yaml
name: example-smoke
output_dir: "output"
headless: false
variables:
  base_url: "https://the-internet.herokuapp.com"
  run_id: "local"

steps:
  - type: navigate
    url: "{{base_url}}"
  - type: screenshot
    file: "homepage.png"
  - type: scroll
    direction: down
    distance: 500
  - type: screenshot
    file: "scrolled.png"
```

校验并运行：

```bash
uvx pomelo-pw validate smoke.yaml
uvx pomelo-pw run smoke.yaml --headless
```

默认会将截图和失败产物写入 `./smoke/`。Flow 可以用顶层 `output_dir` 指定目录，且支持 `{{variable}}`；相对路径以执行命令时的工作目录解析。Flow 也可用布尔型顶层字段 `headless` 指定无头模式，默认值为 `false`。使用 `-o <目录>` 或 `--headless` 可在单次运行中分别覆盖这两项设置。

## 使用 Pomelo PW

### 发现选择器并创建 Flow

```bash
# 在交互式覆盖层中检查页面并复制选择器
pomelo-pw explore https://the-internet.herokuapp.com

# 将点击、填充和 Enter 按键记录为 YAML flow
pomelo-pw record https://the-internet.herokuapp.com recorded-flow.yaml
```

优先使用稳定的语义化选择器，例如 `role=button[name="Continue"]`，而不是依赖样式表现的 CSS class。

### 运行 Flow

```bash
# 显示浏览器并输出步骤进度
pomelo-pw run flow.yaml -v

# 无头执行并输出 JSON 结果
pomelo-pw run flow.yaml --headless --json

# 覆盖本次运行的 flow 变量
pomelo-pw run flow.yaml --var base_url=https://staging.example.com

# 覆盖本次运行的 flow output_dir
pomelo-pw run flow.yaml -o .pomelo-pw/artifacts/manual-run

# 不启动浏览器，只校验 YAML 和步骤参数
pomelo-pw validate flow.yaml
```

变量使用 `{{name}}`；CLI 参数优先于步骤级变量，步骤级变量优先于 flow 级变量。`${name}` 会被保留给 JavaScript 和 shell 模板字符串。

### 编写 Flow

下例展示了常见模式：导航、交互、等待有意义的结果，然后保存证据。

```yaml
name: login-smoke
variables:
  base_url: "https://app.example.com"
  username: "user@example.com"
  password: "secret"

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
    file: "dashboard.png"
```

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
| `evaluate`、`scroll`、`set-viewport` | 各步骤参数 | 执行页面脚本或调整视口 |

在编写 flow 前，先列出可用步骤或查看某一步骤的精确参数：

```bash
pomelo-pw steps
pomelo-pw spec wait
pomelo-pw spec select
```

[example/](example/) 目录将可运行 flow 划分为公共检查、浏览器交互和浏览器状态复用；其 [README](example/README.md) 说明各场景、前置条件和变量覆盖方式。内置的 [Agent skill](plugins/pomelo-pw/skills/pomelo-pw/SKILL.md) 提供了面向 Agent 的说明和可复用 flow 模板。

## 开发

安装锁定的开发环境：

```bash
uv sync --all-groups --locked
```

直接使用 `uv` 运行常规质量检查：

```bash
uv run --locked --no-sync ruff format --check src tests scripts
uv run --locked --no-sync ruff check src tests scripts
uv run --locked --no-sync mypy src tests scripts
uv run --locked --no-sync pytest
```

在安装 GNU Make 和 Bash 的系统上，`make check` 与 `make test` 封装了这些命令。`make test cov=1` 还会生成 HTML 覆盖率报告。

### 刷新原生插件

仓库将 `pomelo-pw` skill 打包为原生插件。先校验软件包，再为可用的 Agent 客户端刷新可编辑 CLI 和已安装插件：

```bash
uv run --locked python scripts/install.py plugin check
uv tool install --editable . --force
uv run --locked python scripts/install.py plugin apply
```

应用插件更新后，重启 Agent 客户端以加载新 skill。

### 构建与发布

```bash
# 查看由 Git 历史推导出的发布版本
uv run --locked --no-sync python scripts/version_calc.py

# 将计算出的版本写入 pyproject.toml 和 uv.lock
uv run --locked --no-sync python scripts/version_calc.py --no-dry-run

# 构建源码和 wheel 分发包
uv build

# 将已有分发包上传到 PyPI
make pypi

# 在可用 GNU Make 和 Bash 时构建独立可执行文件
make binary
```

`make pypi` 会在 `./.env` 存在时加载它；否则 Twine 使用当前环境、`.pypirc` 或 keyring。使用 PyPI API token 时，在已被忽略的 `.env` 文件或 shell 环境中设置 `TWINE_USERNAME=__token__`，并将 `TWINE_PASSWORD` 设置为该 token。该目标为非交互式，缺少可用凭据时会失败。

发布版本由 Git 历史推导。检查版本文件的变更后，将其提交并创建对应的 `vX.Y.Z` tag；GitHub Actions 会从该 tag 构建 wheel 和各平台二进制文件。

## 仓库布局

```text
src/pomelo_pw/       CLI、执行器、配置和步骤实现
tests/               单元测试和集成风格测试
example/             可运行的 YAML 示例和使用说明
plugins/pomelo-pw/   原生插件和 Agent skill
docs/                架构和过程文档
scripts/             插件同步和发布辅助脚本
```

## 许可证

MIT
