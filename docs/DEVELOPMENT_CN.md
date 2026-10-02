# 开发指南

[返回首页](../README_CN.md) | [架构设计](DESIGN.md) | [English](DEVELOPMENT.md)

本文面向仓库开发者。运行已安装 CLI 或在其他项目中使用 Python 包，见[使用指南](USAGE_CN.md)。

## 开发环境与检查

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

在安装 GNU Make 和 Bash 的系统上，`make check` 运行格式、lint 和类型检查，`make test` 运行测试。`make test cov=1` 还会生成 HTML 覆盖率报告。针对具体变更，可将 pytest 范围限定到相关测试文件。

## 刷新原生插件

仓库将 `pomelo-pw` skill 打包为原生插件。先校验软件包，再为可用的 Agent 客户端刷新可编辑 CLI 和已安装插件：

```bash
uv run --locked python scripts/install.py plugin check
uv tool install --editable . --force
uv run --locked python scripts/install.py plugin apply
```

应用插件更新后，重启 Agent 客户端以加载新 skill。

## 构建与发布

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
docs/                使用、参考、架构、开发指南和过程文档
scripts/             插件同步和发布辅助脚本
```

实现职责与扩展约定见[架构设计](DESIGN.md)。`docs/requirement/`、`docs/intent/`、`docs/plan/` 和 `docs/verification/` 保存历史需求、方案和验证记录；当前用法以[流程参考](FLOW_REFERENCE_CN.md)为准。
