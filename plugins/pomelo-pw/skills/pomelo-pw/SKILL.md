---
name: pomelo-pw
description: 通过 Pomelo PW CLI 或 Python 包编写、校验和运行 YAML 浏览器流程，支持登录状态复用与结构化执行报告。
---

# Pomelo PW

使用 Pomelo PW 在用户项目中编写和运行 YAML 流程。随包提供的参考文档和模板描述当前接口约定；只读取本次任务需要的内容。

## 按需阅读

| 任务 | 参考文档 |
| --- | --- |
| 变量、evaluate、条件、等待、循环、foreach 或轮询 | [运行时与控制流程](references/runtime-and-control.md) |
| 浏览器操作、登录状态、HTTP 请求、DOM 提取或截图 | [浏览器与 HTTP 步骤](references/browser-and-http.md) |
| 断言、收集与导出、JSON 报告或数据驱动执行 | [报告与数据驱动执行](references/reporting.md) |
| 在其他 Python 项目中执行已有 YAML | [Python 包集成](references/python-api.md) |
| 基于完整流程或操作片段开始编写 | [模板索引](templates.md) |

这些文件包含在插件包内。仓库中的示例服务是可选的源码资源，使用已安装的 skill 不需要这些服务。

## 执行已有流程

从用户指定的工作目录执行：相对输出目录以该工作目录为基准解析，而不是以 YAML 或插件所在目录为基准。

已安装 CLI 时使用 `pomelo-pw`；调用方项目管理该依赖时使用 `uv run pomelo-pw`。流程使用较新能力时，先确认安装版本：

```bash
pomelo-pw --version
pomelo-pw validate path/to/flow.yaml
pomelo-pw run path/to/flow.yaml --headless --json
```

如果 PATH 中其他 Python 环境的命令遮蔽了 uv 管理的工具，使用 `uv tool run pomelo-pw` 明确选择该工具，并在运行流程前确认其版本。刷新插件不会升级其他 Python 环境。

遵循用户指定的浏览器模式和变量值。需要可见浏览器时省略 `--headless`。通过 `--var key=value`、`--base-url` 或 `-o <directory>` 显式覆盖配置；`--var` 的值始终是字符串。

通过 CLI 查询准确参数：

```bash
pomelo-pw steps
pomelo-pw spec wait
pomelo-pw spec request
```

通过 Python 包执行需要 Python 3.12+ 和可用的 Chromium 浏览器。`pomelo-pw install` 安装 Playwright Chromium；源码环境和独立二进制可以使用检测到的系统 Chrome。安装应在实际执行流程的环境中进行。

## 编写流程

浏览器操作、查询、提取、分支、遍历和轮询优先使用原生步骤。对于原生步骤无法表达的数据转换或应用特有状态判断，使用 evaluate 函数。

```yaml
name: smoke
variables:
  base_url: "https://example.com"
steps:
  - type: navigate
    url: "{{base_url}}"
  - type: wait
    condition: {page: {element_visible: "h1"}}
  - type: screenshot
    file: page.png
```

遵循以下执行规则：

- 完整引用保留 JSON 类型；嵌入文本的引用只接受标量，CLI 覆盖值仍为字符串。
- 浏览器脚本源码按字面量处理。使用函数表达式，通过 `args` 传入数据，并显式返回 JSON。省略 args 与传入 null 的含义不同。
- if、while、wait、poll 和 assert 共用对象形式的条件。自定义 JS 判断函数必须返回布尔值。
- extract 前先等待页面达到所需就绪状态。HTTP 读取使用 request，数组遍历使用 foreach，持续刷新结果直到终态使用 poll。
- 先提交任务，再轮询。读取重试应显式配置在具体查询步骤上；子步骤失败不会重放已完成的分支或迭代。
- 使用 foreach.collect 收集每项结果，使用顶层 outputs 导出。通过 assert 明确业务失败规则。
- 每次执行都会创建新的浏览器状态。登录后保存状态，在后续流程中显式加载同一文件；会话过期时按应用的登录方式处理。

## 查看结果

`run --json` 向 stdout 输出一个报告，日志写入 stderr。检查 `status: passed|failed`、`errors` 和 `outputs`；成功退出码为 0，失败为 1。API 调用返回相同结构的报告。

通过错误路径和保留的截图、HTML 证据定位失败。详细执行轨迹可选，并有容量限制。业务数据中的 `failed` 计数不会自动使执行失败，需要通过断言明确该规则。

执行修改后的 YAML 前应进行静态校验。静态校验不能证明认证有效、状态文件共享正确、页面已经就绪或基线可用。只执行用户授权的针对性检查和应用流程。
