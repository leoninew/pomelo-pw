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

输入优先级为：CLI/API 显式覆盖 > 当前步骤变量 > 外层步骤变量 > data 行 > flow 变量。`--var key=value` 仍是文本输入。`inputs` 和 `results` 是保留名称，不能作为输入根变量。

### 运行时数据

完整引用保留 JSON 原生类型：`{{name}}`、`{{item.path}}`、`{{inputs.filter}}`、`{{results.records[0].id}}`。引用嵌入文本时只接受标量，布尔、数字和 null 使用 JSON 文本形式；对象和数组不能拼入文本。路径支持标识符字段和非负数组下标。用 `\{{` 表示字面量模板开头；`${name}` 保持原样。

```yaml
steps:
  - type: evaluate
    script: "() => [{id: 'a', enabled: false}]"
    save_as: records
  - type: evaluate
    args: "{{results.records[0]}}"
    script: "async (record) => ({id: record.id, enabled: record.enabled})"
    save_as: selected
```

`evaluate.script` 必须是同步或 async 函数表达式，源码保持原文。通过 `args` 传递单个 JSON 载荷；未提供 args 时不传参数，`args: null` 则传入一个 null 参数。函数必须明确返回 JSON 值，不需要数据时可 `return null`；不支持的类型、非有限数字和循环数据会报错。

只有产生公开输出的步骤支持 `save_as`，当前为 `evaluate`。成功后保存结果快照，再次成功写入会覆盖。替换时参数可以读取上一次值，但失败会使该绑定失效。嵌套步骤共享结果，data 行之间隔离。子步骤执行时才解析参数，子步骤局部变量不会泄漏给兄弟步骤。结果字符串始终作为数据，不重新解释为模板。`output_dir` 在运行前解析，只能读取输入。

这是不提供兼容适配的接口变更：裸模块代码改为函数，源码中的输入插值改为 `args`；完整引用不再强制转成字符串。Python 步骤实现改用 `StepContext.runtime`/`inputs` 和 `StepResult.output`、`control`、`diagnostics`，移除原 `variables` 和 `StepResult.data`。可直接运行[离线示例](example/public/runtime-results.yaml)。

### 结构化条件

`if.condition` 和 `loop.while` 使用同一条件对象，每个节点恰好包含一个操作符：

```yaml
- type: if
  condition:
    all:
      - exists: "{{results.record.enabled}}"
      - eq: ["{{results.record.enabled}}", false]
      - in: ["{{results.record.status}}", [ready, completed]]
      - page: {element_visible: "#submit"}
  then:
    - type: click
      selector: "#submit"
```

`eq`/`ne` 递归比较两个 JSON 值，不隐式转换：`1` 与 `1.0` 相等，`false` 与 `0` 不同。`in: [值, 数组]` 使用相同比较规则。`exists` 只接受一个完整引用，检查路径是否可读取；已定义的 null、false、零和空值都存在，其他判断中的缺失引用会失败。`all`/`any` 接收非空数组并按顺序短路，`not` 接收一个条件对象。可选字段先用 exists 保护，再比较其值。

`page` 支持 `element_exists`、`element_visible`、`element_hidden`、`url_contains`、`url_matches`（Python 正则 search）和 `text_contains`（Playwright DOM 文本匹配）。可见性以首个匹配元素为准，缺失元素视为隐藏。这些是即时探测，不自动等待或轮询。文本匹配遵循 Playwright 空白归一化规则，不再搜索 HTML 源码。

自定义谓词使用 `js: {script: "({flag}) => flag === false", args: {flag: "{{results.record.enabled}}"}}`。同步或 async 函数必须返回布尔值；源码保持原文，未提供 args 与 null 的区别和 evaluate 相同。每次探测获取最新输入及结果快照，while 在每轮循环体执行前重新判断。静态校验检查整棵条件树，运行时只解析实际访问的节点。旧冒号字符串和裸 JS 表达式直接拒绝，不提供兼容适配。可直接运行[离线条件示例](example/public/structured-conditions.yaml)。

### 集合遍历

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

`foreach` 按顺序遍历 JSON 数组快照，空数组不执行子步骤。`as` 默认为 `item`，`index_as` 默认为 `index`，索引从 0 开始；名称必须是不同的非保留 ASCII 标识符。迭代绑定优先于普通变量和 CLI 覆盖，数据不会再次解析成模板；内层循环退出后恢复外层绑定。回写源结果不会改变本次遍历范围。可直接运行[离线集合示例](example/public/collection-iteration.yaml)。

`loop` 必须且只能提供 `times`（非负整数）或 `while`；`max_iterations` 为正整数，仅允许与 while 使用。次数和上限支持完整类型化引用。原 foreach 次数/条件调用必须改用 loop。父 if/loop/foreach 的 retry 仅覆盖自身判断或准备，子步骤失败不会重放已经完成的控制体；需要重试的操作应在对应子步骤声明。嵌套错误包含步骤路径和集合索引。

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
| `foreach` | `items`、`steps`，可选 `as` / `index_as` | 遍历数组，提供局部元素和索引绑定 |
| `evaluate` | `script`，可选 `args` 和 `save_as` | 执行页面函数并传递 JSON 数据 |
| `scroll`、`set-viewport` | 各步骤参数 | 调整滚动位置或视口 |

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
