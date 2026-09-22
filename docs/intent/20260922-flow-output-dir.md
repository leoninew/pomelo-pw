# Flow YAML 输出目录支持
最后修改时间: 2026-09-22 10:38:14

## Review status

Accepted

## Background

当前只有 CLI `-o/--output` 可以指定运行产物目录。未传该参数时，CLI 会在调用执行器前计算默认目录，使 flow 自身无法声明产物位置。

## Goal

允许 flow YAML 使用顶层 `output_dir` 声明截图、失败上下文和状态文件的根目录，并支持现有 `{{variable}}` 语法。

## Non-goal

- 不增加按步骤单独指定输出目录的语法。
- 不修改 K12 项目的 `.pomelo-pw` flow 文件。
- 不改变数据驱动运行在输出根目录下按行创建子目录的行为。

## User scenarios

业务 flow 可以把 `output_dir` 写为 `.pomelo-pw/artifacts/course-adoption-{{run_id}}`，避免每次命令行重复指定输出目录。

## Acceptance

- CLI `-o/--output` 优先于 flow 的 `output_dir`。
- 未传 CLI 选项时，flow 的 `output_dir` 成为所有运行产物的根目录。
- 两者均未配置时，继续使用 `./<flow-name>/` 默认目录。
- 相对路径以执行命令时的工作目录解析。
- `pomelo-pw validate` 会拒绝非字符串或空白的 `output_dir`。

## Open questions

暂无需要用户确认的未决事项。

## Decisions

输出根目录在 `FlowExecutor` 中统一解析，复用既有 `StepContext.output_dir`，使截图、失败产物、状态文件和数据驱动子目录天然保持一致。

## Risk

直接以 `FlowExecutor.run_flow()` 调用且未传输出目录时，默认目录将从 `./output/` 统一为与 CLI 相同的 `./<flow-name>/`；这消除了两条调用路径的差异。
