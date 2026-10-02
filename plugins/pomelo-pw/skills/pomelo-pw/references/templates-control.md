# 运行时与控制流程模板

[Skill 入口](../SKILL.md) | [模板索引](../templates.md)

<a id="typed-runtime-results"></a>

## 保留类型的运行时结果

```yaml
name: runtime-results
steps:
  - type: evaluate
    script: "() => [{id: 'a', enabled: false}]"
    save_as: records
  - type: evaluate
    args: "{{results.records[0]}}"
    script: "async (record) => ({id: record.id, enabled: record.enabled})"
    save_as: selected
```

通过 args 传入输入和结果引用；脚本源码按字面量处理，必须是函数表达式，并显式返回 JSON 值。完整引用保留原生类型，文本插值只接受标量。不兼容裸模块脚本或源码模板插值。

## 条件执行

<a id="handle-optional-ui-elements"></a>

## 处理可选界面元素

```yaml
name: handle-cookie-banner
variables:
  url: "https://example.com"

steps:
  - type: navigate
    url: "{{url}}"

  # Cookie 提示条存在时关闭它
  - type: if
    condition:
      page: {element_visible: ".cookie-banner"}
    then:
      - type: click
        selector: ".accept-cookies"
      - type: wait
        animation_stable: true

  - type: screenshot
    file: "page-clean.png"
```

<a id="branch-on-page-state"></a>

## 根据页面状态分支

```yaml
name: conditional-flow
variables:
  base_url: "https://example.com"

steps:
  - type: navigate
    url: "{{base_url}}"

  - type: if
    condition:
      page: {url_contains: "/login"}
    then:
      - type: fill
        selector: "#email"
        value: "user@example.com"
      - type: click
        selector: "button[type='submit']"
    else:
      - type: screenshot
        file: "already-logged-in.png"

  - type: screenshot
    file: "final-state.png"
```

---

## 循环执行

<a id="scroll-through-page"></a>

## 循环滚动页面

```yaml
name: scroll-capture
variables:
  url: "https://example.com"

steps:
  - type: navigate
    url: "{{url}}"

  - type: loop
    times: 5
    steps:
      - type: scroll
        direction: down
        distance: 500
      - type: wait
        delay: 300

  - type: screenshot
    file: "bottom-of-page.png"
    full_page: true
```

<a id="load-more-pagination"></a>

## 点击加载更多完成分页

```yaml
name: load-all-items
variables:
  url: "https://example.com/items"

steps:
  - type: navigate
    url: "{{url}}"

  - type: loop
    while:
      page: {element_visible: ".load-more-button"}
    max_iterations: 20
    steps:
      - type: click
        selector: ".load-more-button"
      - type: wait
        network_idle: true

  - type: screenshot
    file: "all-items.png"
    full_page: true
```

---

<a id="combined-page-readiness"></a>

## 组合页面就绪条件

```yaml
- type: wait
  condition:
    all:
      - page: {url_contains: "/items?page=2"}
      - page: {element_visible: "table tbody tr"}
      - js:
          script: "({id}) => !document.querySelector('table').inert && document.querySelector('tr').dataset.id === id"
          args: {id: "{{record.id}}"}
  timeout: 5000
  interval: 100
```

在导航或点击以及记录提取后执行。只能选择一种 wait 模式；组合条件不会提交操作，也不会刷新运行时结果。

<a id="collection-results"></a>

## 遍历结构化结果

```yaml
name: collection-results
steps:
  - type: evaluate
    script: "() => [{id: 'a', enabled: true}, {id: 'b', enabled: false}]"
    save_as: records
  - type: foreach
    items: "{{results.records}}"
    as: record
    index_as: position
    steps:
      - type: if
        condition: {eq: ["{{record.enabled}}", true]}
        then:
          - type: evaluate
            args: {record: "{{record}}", index: "{{position}}"}
            script: "payload => payload"
```

具体操作的重试配置在子步骤上；父级重试不会重放已完成的迭代。

<a id="bounded-task-polling"></a>

## 有界任务轮询

```yaml
- type: poll
  until: {in: ["{{results.task.body.status}}", [ready, failed]]}
  timeout: 30000
  interval: 1000
  max_attempts: 20
  save_as: polling
  steps:
    - type: request
      url: "/api/tasks/{{results.submitted.body.id}}"
      save_as: task
      retry: 2
      retry_delay: 250
```

在此步骤前提交任务。第一次查询立即执行；timeout 包含子步骤重试和轮询间隔。ready 和 failed 都会结束轮询，因此需要在后续处理业务结果。限制耗尽时失败；save_as 记录 attempts、elapsed_ms 和轮询体最近成功绑定的结果。

<a id="collected-outcomes-and-assertions"></a>

## 结果收集与断言

```yaml
name: collected-outcomes
variables:
  records: [{id: a}, {id: b}]
outputs:
  outcomes: '{{results.collected.items}}'
report:
  steps: true
steps:
  - type: foreach
    items: '{{records}}'
    as: record
    collect: '{{results.outcome}}'
    save_as: collected
    steps:
      - type: evaluate
        args: '{{record}}'
        script: 'record => ({id: record.id, category: "processed"})'
        save_as: outcome
  - type: assert
    condition: {eq: ['{{results.collected.iterations}}', 2]}
    message: Unexpected collection size
```

使用 --json 运行时，stdout 输出一个结构化报告，日志写入 stderr。收集和导出需要显式配置；业务失败分类需要通过断言使执行失败。详细轨迹输出需主动开启，并受容量限制；显式导出保持完整。
