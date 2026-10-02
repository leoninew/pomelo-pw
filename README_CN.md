# Pomelo PW

[![CI](https://github.com/leoninew/pomelo-pw/actions/workflows/ci.yml/badge.svg)](https://github.com/leoninew/pomelo-pw/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/pomelo-pw)](https://pypi.org/project/pomelo-pw/)
[![GitHub Release](https://img.shields.io/github/v/release/leoninew/pomelo-pw)](https://github.com/leoninew/pomelo-pw/releases)

[English](README.md) | [简体中文](README_CN.md)

Pomelo PW 是一个基于 Playwright 的浏览器自动化 CLI。它通过声明式 YAML flow 执行浏览器操作，让 UI 检查可以与应用代码一起维护，而不需要定制测试框架。

它适用于可重复的 UI 检查、脚本化工作流、视觉对比和由 Agent 协助的浏览器任务。Flow 会在执行前校验参数；步骤失败时，自动收集截图、页面快照、控制台错误和网络失败信息。

## 能力概览

- YAML 浏览器流程：导航、表单、等待、截图和登录状态复用
- 类型化运行时数据、DOM 提取、会话 HTTP 请求、条件、遍历、轮询和断言
- 重试、数据驱动执行、结构化报告和截图基线对比
- CLI、Python 包依赖，以及 Claude Code、Codex 和 Grok Build 原生插件

## 安装

Python 包需要 Python 3.12+。推荐使用 [uv](https://docs.astral.sh/uv/) 安装：

```bash
uv tool install pomelo-pw
pomelo-pw install
```

软件包发布于 [PyPI](https://pypi.org/project/pomelo-pw/)，Windows、macOS 和 Linux 独立可执行文件见 [GitHub Releases](https://github.com/leoninew/pomelo-pw/releases)。浏览器选择、可选依赖和包依赖方式见[使用指南](docs/USAGE_CN.md)。

## 快速开始

创建 `smoke.yaml`：

```yaml
name: example-smoke
variables:
  base_url: "https://the-internet.herokuapp.com"
steps:
  - type: navigate
    url: "{{base_url}}"
  - type: screenshot
    file: homepage.png
```

校验并运行：

```bash
pomelo-pw validate smoke.yaml
pomelo-pw run smoke.yaml --headless
```

默认产物写入执行目录下的 `smoke/`。用 `-o <目录>` 覆盖输出位置，或用 `--var key=value` 覆盖流程变量。

## 文档

| 文档 | 内容 |
| --- | --- |
| [使用指南](docs/USAGE_CN.md) | CLI、编写流程、登录状态复用、Python API 和常见运行方式 |
| [流程参考](docs/FLOW_REFERENCE_CN.md) | 步骤概览、数据引用、条件、等待、轮询、请求、提取和报告契约 |
| [示例目录](example/README.md) | 可运行 YAML、服务前置条件和组合场景 |
| [开发指南](docs/DEVELOPMENT_CN.md) | 开发环境、质量检查、插件同步、构建和发布 |
| [架构设计](docs/DESIGN.md) | 内部模块、执行生命周期、作用域、重试与超时边界 |
| [Agent skill](plugins/pomelo-pw/skills/pomelo-pw/SKILL.md) | Agent 操作说明和流程模板 |

## 许可证

MIT
