# pomelo-pw Makefile 自动化改进验证
最后修改时间: 2026-08-25 22:25:19

Review status: Accepted

## Requirement alignment

已按 `docs/requirement/20260825-project-automation-review.md` 核对。公共自动化入口已按 uv Python Makefile 标准重组：依赖同步、用户级 CLI/插件安装、只读质量检查、单元测试与覆盖率、发布构建职责已分离。

## Spec alignment

不适用（light / 轻量模式未创建 Spec）。

## Plan alignment

不适用（light / 轻量模式按 Requirement 实现）。

## Actual diff summary

- `Makefile` 新增 `deps`，将 `install` 改为用户级 editable tool 安装并执行插件 check/apply；`release` 仅执行 `uv build`。
- `Makefile` 的 `check` 默认执行 format check、lint 和 mypy，只有 `fix=1` 才允许自动修复；`test cov=1` 追加覆盖率参数；移除 catch-all 规则并补全帮助信息和清理范围。
- `pyproject.toml` 新增 `pytest-cov` 开发依赖，`uv.lock` 同步锁定覆盖率工具及其依赖，使 `cov=1` 可复现运行。
- Requirement 文档状态更新为 `Accepted` 并补齐 SpecFlow 时间戳；本验证文档记录本次验收结果。

## Expected vs actual changed files

| 预期文件 | 实际结果 |
| --- | --- |
| `Makefile` | 已修改，完成公共入口和参数语义标准化 |
| `pyproject.toml` | 已修改，为 `cov=1` 声明 `pytest-cov` |
| `uv.lock` | 已修改，锁定覆盖率依赖 |
| `docs/requirement/20260825-project-automation-review.md` | 已更新状态和时间戳 |
| `docs/verification/20260825-project-automation-review.md` | 已新增 |

## Acceptance checklist

- [x] 裸 `make` 只显示帮助，不执行安装、构建、发布或源码修复。
- [x] 所有命令型 target 均声明在 `.PHONY` 中，且未知 target 不再被 catch-all 规则吞掉。
- [x] `deps` 使用 `uv sync --all-groups --locked --no-install-project`。
- [x] `install` 使用 `uv tool install --editable . --force`，并在同一入口执行插件 check/apply。
- [x] `check` 默认只读，`fix=1` 才展开 Ruff 修复参数。
- [x] `test` 默认保持 134 个测试范围，`cov=1` 仅增加覆盖率输出。
- [x] `release` 仅构建 source distribution 和 wheel，不上传、不发布、不修改版本或用户目录。

## Test results

| 命令 | 结果 |
| --- | --- |
| `make deps` | passed; locked environment synchronized |
| `make` | passed; help displayed only |
| `make check` | passed; Ruff format check、Ruff lint 和 mypy 通过 |
| `make test` | passed; 134 passed |
| `make test cov=1` | passed; 134 passed，覆盖率报告写入 `htmlcov/` |
| `make release` | passed; 产出 sdist 和 wheel |
| `make --dry-run check fix=1` | passed; 展开 Ruff format 修复和 `ruff check --fix` |
| `make --dry-run install` | passed; 展开插件 check、用户级安装和 apply |
| `make --dry-run release` | passed; 仅展开 `uv build` |
| `make definitely-unknown-target` | expected failure; Make 正确报告无匹配规则 |
| `uv lock --check` | passed |
| `git diff --check` | passed |

## Scope deviation

相对 requirement 的 Makefile 目标，额外修改 `pyproject.toml` 和 `uv.lock` 以声明并锁定 `pytest-cov`。这是 `test cov=1` 可执行且可复现的必要依赖，无业务代码或 CLI 行为变更。

## Risks

- Makefile 使用 `SHELL := bash` 和 POSIX 清理命令；本次已在 Windows 的 Cygwin GNU Make 环境验证，其他 Windows 环境需要可用的 Bash/Make 前置条件。
- 未实际执行 `make install`，因为它会写入用户级 uv tool 目录并修改本机 agent plugin 状态；其命令展开已通过 dry-run 验证。

## Incomplete items

无。`make install` 的真实用户级副作用属于本次验证中明确保留的外部状态边界，不是实现缺项。

## Conclusion

交付满足 Requirement 的范围和验收标准。Makefile 入口职责清晰，质量检查默认只读，覆盖率和自动修复均需显式开启，发布入口无隐含外部发布副作用；依赖锁定、质量检查、测试、覆盖率和构建验证均通过。
