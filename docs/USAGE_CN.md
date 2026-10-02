# 使用指南

[返回首页](../README_CN.md) | [流程参考](FLOW_REFERENCE_CN.md) | [English](USAGE.md)

本文介绍运行流程和接入其他项目的方式。步骤参数与数据契约见[流程参考](FLOW_REFERENCE_CN.md)，开发和发布见[开发指南](DEVELOPMENT_CN.md)。

## 浏览器与临时运行

安装方法见[首页](../README_CN.md#安装)。`pomelo-pw install` 为软件包安装下载 Playwright Chromium；源码检出和独立二进制在找到本机 Chrome/Chromium 时会使用它。也可用 `uvx pomelo-pw` 临时运行已发布软件包，无需预先安装 CLI。

```bash
uvx pomelo-pw install
uvx pomelo-pw run flow.yaml --headless
```

## 发现选择器并创建 Flow

```bash
# 在交互式覆盖层中检查页面并复制选择器
pomelo-pw explore https://the-internet.herokuapp.com

# 将点击、填充和 Enter 按键记录为 YAML flow
pomelo-pw record https://the-internet.herokuapp.com recorded-flow.yaml
```

优先使用稳定的语义化选择器，例如 `role=button[name="Continue"]`，而不是依赖样式表现的 CSS class。

## 运行 Flow

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

## 输出目录与浏览器模式

默认输出目录按流程文件名确定，例如 `smoke.yaml` 的截图和失败产物写入 `./smoke/`。Flow 可以用顶层 `output_dir` 指定目录，且支持 `{{variable}}`；相对路径以执行命令时的工作目录解析。Flow 也可用布尔型顶层字段 `headless` 指定无头模式，默认值为 `false`。使用 `-o <目录>` 或 `--headless` 可在单次运行中分别覆盖这两项设置。

## 编写流程

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

## 保存与复用登录状态

登录成功后保存状态；另一流程显式加载同一个文件，再导航到业务页面。两个流程可以设置相同的 `output_dir: output/auth`：

```yaml
# Login flow: run after a successful login.
- type: save-state
  file: session.json
```

```yaml
# New flow: restore state before opening the application.
- type: load-state
  file: session.json
- type: navigate
  url: "{{base_url}}/"
```

相对 `file` 路径以流程输出目录解析，绝对路径可跨不同输出目录共享。当前保存和恢复 Cookie（包括 HttpOnly）与 localStorage，不包含 sessionStorage 或 IndexedDB。每次运行创建新的浏览器上下文，不会自动加载上次状态。

`load-state` 在文件不存在时失败，也不校验服务端会话是否仍有效。首次先登录保存；会话过期或撤销时，用流程分支重新登录。`request` 共享恢复后的 Cookie，localStorage token 不会自动转为请求头。

运行示例见[浏览器状态](../example/README.md#browser-state)。示例保存的是匿名公共页面状态，实际登录步骤需要按应用配置。

## 作为 Python 包使用

在调用方项目中安装依赖，再安装浏览器。使用发布包；本地共同开发时，可改用可编辑源码依赖：

```bash
uv add pomelo-pw
uv run pomelo-pw install

# Alternative for local development:
uv add --editable ../pomelo-pw
```

CLI 和 Python API 使用同一个 `FlowExecutor` 执行已有 YAML。下面代码以调用方项目的当前目录为工作目录：

```python
import asyncio
from pathlib import Path

from pomelo_pw.executor import FlowExecutor


async def main():
    root = Path.cwd()
    executor = FlowExecutor(work_dir=root)
    result = await executor.run_flow(
        root / "flow.yaml",
        variables={"base_url": "http://localhost:3000"},
        output_dir=root / "output",
        headless=True,
    )
    if result["status"] == "failed":
        raise RuntimeError(result["errors"])
    return result


result = asyncio.run(main())
```

在已有异步入口中直接 `await executor.run_flow(...)`。可用 `executor.validate_flow_file(path)` 只校验 YAML，返回错误列表。执行失败通过报告的 `status` 与 `errors` 表达，调用方需要检查。报告字段见[流程参考](FLOW_REFERENCE_CN.md#断言与执行报告)。

正式依赖应固定版本，YAML 需要符合该版本的语法。`work_dir` 用于解析相对输出目录；传入绝对 `flow_path`，可以明确指定 YAML 的位置。

## 重试与数据驱动执行

普通步骤可设置 `retry`、`retry_delay`（毫秒）和 `retry_on`（错误类名列表）。重试只重复当前步骤；控制体中的子步骤不会使已完成的分支或迭代整体重放。`poll` 的重试应声明在子查询上，提交操作放在轮询前；写操作重试需要调用方保证幂等性。

顶层 `data` 数组让同一个流程按行独立执行；行字段覆盖流程变量，可用 `_label` 命名输出子目录。`on_error: stop` 为默认值，`continue` 可继续后续顶层步骤或数据行，但任何执行错误仍使最终报告失败。完整示例见 [Agent skill](../plugins/pomelo-pw/skills/pomelo-pw/SKILL.md#data-driven-testing)。

## 截图基线对比

使用基线对比时，在运行 CLI 的同一环境中安装可选依赖：

```bash
# Tool installation:
uv tool install "pomelo-pw[visual]" --force

# Project dependency:
uv add "pomelo-pw[visual]"
```

可运行[视觉对比示例](../example/README.md#visual-comparison)。

## 示例与参数参考

[示例目录](../example/README.md) 包含各流程的前置条件、运行命令和变量覆盖方式；[组合示例](../example/README.md#integrated-flow-capabilities) 串联分页、登录状态恢复、串行任务处理与报告导出。步骤参数和数据语义见[流程参考](FLOW_REFERENCE_CN.md)，Agent 模板见 [skill](../plugins/pomelo-pw/skills/pomelo-pw/SKILL.md)。
