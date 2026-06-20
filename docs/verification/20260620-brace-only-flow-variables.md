# 统一 Flow 变量语法为双花括号 - 验证
最后修改时间: 2026-06-20 22:58:11

Review status: Accepted

## Requirement alignment

依据 `docs/requirement/20260620-brace-only-flow-variables.md` 核对：

- 已将 flow 变量语法统一为 `{{ var }}`。
- 已移除 `${var}` flow 变量替换兼容逻辑，不提供 fallback。
- JavaScript template literal 中的 `${...}` 会保持原样，不再被 Pomelo PW 变量替换处理。
- 旧 flow 中的 `${api_token}` 不再替换，符合“不向后兼容”要求。

## Spec alignment

不适用。轻量模式 / light 未创建独立 spec 文档，按 requirement / 需求核对。

## Plan alignment

不适用。轻量模式 / light 未创建独立 plan 文档，按 requirement / 需求核对。

## Actual diff summary

相关实现和文档改动：

- `src/pomelo_pw/substitution.py`
  - 删除 `${var}` 替换分支。
  - 仅使用 `{{ var }}` / `{{var}}` 正则替换。
  - 嵌套变量递归只识别 `{{`。
- `tests/test_substitution.py`
  - 测试主路径改为 `{{ }}`。
  - 增加 `${base_url}` 保持原样测试。
  - 增加 `{{ base_url }}` 空格形式测试。
- `tests/test_executor.py`、`tests/conftest.py`
  - 测试 flow 示例从 `${}` 迁移到 `{{ }}`。
- `README.md`、`docs/DESIGN.md`、`TODO.md`、`.claude/skills/pomelo-pw/skill.md`
  - 移除 `${}` 兼容推荐和说明。
  - 明确 `${}` 不再作为 flow 变量语法。
- `flows/example.yaml`
  - 示例变量引用迁移到 `{{base_url}}`。
- `CHANGELOG.md`
  - 记录 breaking change。

## Expected vs actual changed files

| 文件 | 预期 | 实际 | 结论 |
|------|------|------|------|
| `src/pomelo_pw/substitution.py` | 修改 | 修改 | 符合 |
| `tests/test_substitution.py` | 修改 | 修改 | 符合 |
| `tests/test_executor.py` | 修改 | 修改 | 符合 |
| `tests/conftest.py` | 修改 | 修改 | 符合 |
| `README.md` | 修改 | 修改 | 符合 |
| `docs/DESIGN.md` | 修改 | 修改 | 符合 |
| `.claude/skills/pomelo-pw/skill.md` | 修改 | 修改 | 符合 |
| `flows/example.yaml` | 修改 | 修改 | 符合 |
| `CHANGELOG.md` | 修改 | 修改 | 符合 |
| `TODO.md` | 修改 | 修改 | 符合，避免历史说明继续声明向后兼容 |
| `uv.lock` | 不在本需求范围 | 已有未提交 diff | 范围外，建议不要纳入本次提交 |

## Acceptance checklist

- [x] 变量替换只处理 `{{ var }}` 语法。
- [x] `${var}` 在任意字符串中保持原样。
- [x] 相关测试覆盖 `{{ var }}` 替换和 `${var}` 保留行为。
- [x] 文档或示例不再推荐 `${var}` 作为变量语法。

## Command results

- `uv run pytest tests/test_substitution.py tests/test_executor.py -q`
  - 26 passed
- `uv run ruff check src/pomelo_pw/substitution.py tests/test_substitution.py tests/test_executor.py tests/conftest.py`
  - passed
- `uv run mypy src/pomelo_pw/substitution.py tests/test_substitution.py tests/test_executor.py tests/conftest.py`
  - passed
- `uv run pytest -q`
  - 124 passed
- `uv run ruff check src tests`
  - passed
- `uv run mypy src tests`
  - success, no issues in 39 source files

## Missed or expanded scope

- 未发现需求遗漏。
- 文档更新范围略扩展到 `TODO.md` 和 `CHANGELOG.md`，用于避免历史说明继续表达 `${}` 兼容以及记录 breaking change。
- 未处理 `uv.lock`，该文件存在范围外 registry diff。

## Risks

- 这是显式破坏性变更：仍使用 `${var}` 的旧 flow 不会再替换变量，需要迁移到 `{{ var }}`。
- `uv.lock` 当前仍有大量未提交 diff，提交本功能时应排除，避免混入无关 registry 改动。

## Incomplete items

无。

## Conclusion

验证通过。实现与轻量需求一致，测试、ruff 和 mypy 均通过。建议提交时排除 `uv.lock`。
