# Python 包集成

[Skill 入口](../SKILL.md) | [模板索引](../templates.md)

在其他 Python 项目中直接执行已有 YAML、无需启动子进程时，使用此方式。要求 Python 3.12+。

## 依赖与浏览器准备

在调用方项目环境中安装：

```bash
uv add pomelo-pw
uv run pomelo-pw install
```

本地开发时，如果源码位于同级目录，可使用 `uv add --editable ../pomelo-pw`。部署时固定包版本，YAML 必须遵循该版本的语法。

## 执行已有 YAML

```python
import asyncio
from pathlib import Path

from pomelo_pw.executor import FlowExecutor


async def main():
    root = Path.cwd()
    executor = FlowExecutor(work_dir=root)
    errors = executor.validate_flow_file(root / "flow.yaml")
    if errors:
        raise ValueError(errors)
    report = await executor.run_flow(
        root / "flow.yaml",
        variables={"base_url": "http://localhost:3000"},
        output_dir=root / "output",
        headless=True,
    )
    if report["status"] == "failed":
        raise RuntimeError(report["errors"])
    return report


report = asyncio.run(main())
```

已有异步入口中可直接 await run_flow。validate_flow_file 返回错误列表，不启动浏览器。执行或启动失败时 run_flow 返回报告，因此需要检查 status 和 errors，不能只依赖异常判断。

进程工作目录与调用方项目不同时，使用绝对 flow_path。work_dir 用于解析相对输出目录，不会改变相对 flow_path 的解析位置。API variables 接受 JSON 类型，CLI --var 的值仍为字符串。

浏览器模式和 output_dir 可以在流程中配置，也可以由 API 覆盖。每次执行都会创建新的浏览器状态，跨流程复用认证需要显式使用 save-state/load-state。报告遵循[与 CLI 相同的约定](reporting.md#execution-report-and-exports)。
