# 报告与数据驱动执行

[Skill 入口](../SKILL.md) | [模板索引](../templates.md)

- [断言](#assert---explicit-expectations)
- [导出与报告结构](#execution-report-and-exports)
- [数据驱动测试](#data-driven-testing)

<a id="assert---explicit-expectations"></a>

## assert - 显式预期

```yaml
- type: assert
  condition: {eq: ['{{results.summary.failed}}', 0]}
  message: Some records failed
```

使用共用的结构化条件树，支持短路求值。只有条件为 false 时才抛出 AssertionFailed，包含条件以及访问过的值和结果；求值错误仍作为执行错误处理。默认消息为 Assertion failed。不进行隐式等待或重试。

<a id="execution-report-and-exports"></a>

## 执行报告与导出

```yaml
outputs:
  outcomes: '{{results.collected.items}}'
  summary: '{{results.summary}}'
report:
  steps: true
  max_steps: 1000
  include_outputs: false
```

outputs 从最终运行时快照中显式导出命名的 JSON 值。键必须是 ASCII 标识符；缺失或无效引用会增加输出错误，其他字段仍继续导出。业务 failed/skipped 分类不会自动影响执行状态，应使用 assert 明确规则。使用 foreach.collect 保留每项结果，通过简短的 evaluate 生成自定义汇总。

run --json 向 stdout 输出一个 schema_version=1 的 JSON 文档，所有执行日志写入 stderr。成功退出码为 0，失败为 1。报告字段为 status/flow/duration_ms/outputs/steps/trace/errors/errors_dropped/artifacts/rows/row_summary。steps 包含顶层 total/executed/completed。trace 包含 enabled/entries/dropped；entries 包含 path/type/status/duration_ms 和可选 output。错误包含 path/type/kind/error_type/message/diagnostics/evidence；continue 在配置的容量范围内保留全部失败。artifacts.screenshots 列出截图，错误证据保留 HTML。报告不再包含 success/failed_step 等旧字段。validate --json 仍使用 valid/errors。

report 默认值为 steps=false、max_steps=1000、include_outputs=false、max_value_bytes=16384 和 max_errors=100。include_outputs 要求 steps=true。重试只记录一个最终逻辑步骤，控制步骤耗时包含子步骤。轨迹或错误超出容量时会统计丢弃数量，过大的值标记 omitted/bytes，消息截断也会标记。显式导出保持完整。数据驱动的每一行都有独立报告，附带 label/index 和自己的导出；行输入不会自动导出。聚合轨迹和错误包含行标识，并保持容量限制。见随包提供的[结果收集模板](templates-control.md#collected-outcomes-and-assertions)。

<a id="data-driven-testing"></a>

## 数据驱动测试

使用多组数据执行同一流程：

```yaml
name: multi-user-test
variables:
  base_url: "https://the-internet.herokuapp.com"

data:
  - _label: "user-alice"
    username: "alice@example.com"
    password: "pass1"
  - _label: "user-bob"
    username: "bob@example.com"
    password: "pass2"

on_error: continue   # 也可使用默认值 "stop"

steps:
  - type: navigate
    url: "{{base_url}}/login"
  - type: fill
    selector: "#email"
    value: "{{username}}"
  - type: screenshot
    file: "result-{{username}}.png"
```

- 每一行独立运行全部步骤。
- 输出位于 `<output>/<_label>/` 或 `<output>/row-N/`。
- 行变量覆盖流程 `variables`，CLI/API 覆盖值仍具有最高优先级。
- 结果包含 `rows` 和 `row_summary: {total, executed, passed, failed}`。

## 失败证据

错误包含嵌套操作路径、诊断详情以及可用的截图和 HTML 证据。截图列在 artifacts.screenshots 中。on_error=continue 可以保留多个失败并继续后续工作，但只要发生执行错误，最终状态仍为失败。

## 仓库集成示例

源码仓库中的 example/support/flow_capability_server.py 和 example/public/flow-capability-example.yaml 提供可选的本地集成示例，组合了分页、Cookie 恢复、HTTP 任务、收集、轮询和报告。这些文件不包含在插件包中；使用 example/README.md 的说明前，应先找到源码仓库。

默认 mixed 场景报告七份材料：ready=3、skipped=3、failed=1。failure_policy=fail 控制业务失败是否触发断言。scenario=empty/read-error/timeout 分别用于空输入、HTTP 503 查询错误和持续待处理直到轮询时间耗尽的场景。使用[随包模板](../templates.md)不需要这些测试环境。
