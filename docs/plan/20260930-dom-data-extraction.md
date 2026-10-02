# T07 DOM 集合与字段提取实施计划
最后修改时间: 2026-10-02 11:31:14

## Review status

Accepted

## Flow mode and stage

标准模式 / standard，Intent/Plan 已接受，Implementation 已交付。用户自行试跑通过并明确要求完成本任务验证；Verification 的针对性回归、离线最小集成和静态检查已通过，发现的 CLI 摘要问题已修复，验证文档 Draft 待用户审阅，当前停在 T07。

## Intent basis

依据 [T07 Intent](../intent/20260930-dom-data-extraction.md)，复用现有运行时结果、类型化引用、嵌套执行、foreach 和 poll 契约。T06 已提交为 89eb7ef；没有必须由用户决定的未决事项。

## Proposed contracts

```yaml
- type: extract
  selector: table tbody tr
  mode: all
  fields:
    id: {read: attribute, attribute: data-id}
    name: {selector: .name}
    href: {selector: a, read: attribute, attribute: href}
    url: {selector: a, read: url, attribute: href}
    status: {selector: .status, required: false, default: unknown}
  save_as: records
- type: extract
  selector: '#page-size'
  read: value
  save_as: page_size
```

- 唯一新步骤 extract，必需非空 selector，根选择器使用 page.locator；mode 默认 one，也可 all。one 默认要求恰好一个匹配，零匹配按 required/default 处理，多匹配明确失败；all 按 DOM 顺序返回数组，空集合成功返回 []。
- 无 fields 时读取标量；有 fields 时按非空对象映射记录。字段名为 ASCII identifier，可直接被结果引用消费。one 返回单值/对象，all 返回值/对象数组，没有额外结果包装。
- read 默认 text（textContent，包含隐藏文本），trim 默认 true，只去掉首尾空白，内部空白保留；trim: false 保留原文。attribute 返回原始 getAttribute 字符串；url 要求显式 attribute，以元素 baseURI（包括 HTML base）解析绝对 URL；属性空串是有效值，缺失属性按缺失规则处理，非法 URL 报错。value 读取 input/textarea/select 当前字符串值，不隐式转数字或复选框布尔值；其他元素明确失败。
- attribute 仅可与 read: attribute/url 同时使用，且这两个读取模式必须指定非空 attribute；trim 仅用于 text。有 fields 时禁止同层 read/attribute/trim，避免标量配置被忽略。
- 每个字段有可选 selector 和相同读取配置；省略 selector 读取行本身，声明时必须为非空的相对 CSS 选择器。浏览器 querySelectorAll 负责语法解析，支持 :scope；不实现 Playwright 字段选择器引擎，不跨 iframe 或穿透 Shadow DOM。字段零匹配或属性缺失默认失败，多个匹配始终失败，不取第一个、不丢弃记录。
- required 默认为 true，可显式 false；可选值缺失时返回 default，未声明 default 返回 null；default 接受任意 JSON 值，仅可用于 required: false。空串不视为缺失，false/0/null 默认值不被替换。集合模式的 required/default 控制每项标量读取缺失，空根集合仍为 []；根配置不覆盖映射字段自己的缺失规则。
- 使用 Locator.evaluate_all 的单次同步浏览器回调选定根集合、读取所有字段并校验数量；不跨字段 await，不调用等待接口，不点击或修改 DOM。页面就绪由调用方先 wait；快照只覆盖本次调用，不保证后续步骤仍观察到同一页面状态。
- schema 参数在实际执行时解析，fields 支持对象完整引用，配置值支持类型化引用；静态与解析后分别校验，未知字段配置报错。读取输出经过现有 JSON 快照校验，save_as/失败清除/不重解释模板字符串沿用 T01。
- 参数对象在 Playwright 传输边界先编码 JSON，浏览器内解码，避免参数过滤递归省略 None 键；显式 null 默认值和嵌套 JSON 字段完整保留。
- DOM 读取错误带有行序号与字段位置，沿现有步骤路径与 CLI 失败出口传播；不隐式重试，显式 retry 复用现有策略。poll 通过执行器既有预算控制提取，不添加独立超时或更改执行器。

## Implementation steps

1. 新增并注册 ExtractStep，实现配置校验、同步 DOM 快照和明确的缺失/数量/读取错误。
2. 增加参数及结果绑定、嵌套延迟解析、失败清除、poll 预算的针对性回归。
3. 新增离线 dom-data-extraction.yaml，演示文本、属性、绝对 URL、表单值、可选字段、空集合和 foreach 消费。
4. 同步中英文 README、DESIGN、示例索引与本地插件说明/模板，不安装或同步用户级插件。
5. 执行变更 Python 文件静态检查、针对性回归和离线 Chrome 最小集成，记录交付后停止。

## Files to change

- src/pomelo_pw/steps/extract.py、steps/__init__.py。
- tests/test_extract.py。
- example/public/dom-data-extraction.yaml、example/README.md。
- README.md、README_CN.md、docs/DESIGN.md、plugins/pomelo-pw/skills/pomelo-pw/{SKILL.md,templates.md}。
- T07 Intent/Plan、系列入口和 T06 Intent/Plan 当前阶段记录。

## Verification plan

正式 Verification 由用户查看交付后决定。开发阶段只执行针对性回归与最小集成：静态/动态参数类型、嵌套定位、字段映射与 DOM 顺序、可选 null/false/0 默认值、文本首尾/内部空白、原始/绝对 URL、动态表单值、缺失/多匹配/非法 CSS/不支持读取失败、foreach 消费和失败结果清除。复用现有 poll 测试验证调度预算，不重复 T06 或全量测试。

## Blockers and assumptions

暂无需要用户确认的未决事项。同步字段提取限定 CSS，以一次原生 DOM 操作获得可解释的快照边界；特殊页面、Shadow DOM 和类型转换继续使用短 evaluate。提取不承担等待职责。

## Risks

- CSS 字段语法与 Playwright 根选择器语法不同，必须在说明与错误中明确；字段不跨 frame/shadow 边界。
- 文本与表单值保持字符串；业务调用方需显式转换类型，不能把空文本当成缺失字段。
- 快照不能阻止后续异步页面更新；分页和页面就绪仍须调用方声明等待条件。
- 本地示例只验证能力组合，不代表真实材料页面的字段选择器或业务规则。

## Rollback

按本项 diff 移除 extract 实现、注册、测试与示例/说明，不增加兼容适配，不执行额外 Git 写操作。

## Implementation handoff

- 新增并注册 extract：one/all、标量与字段映射、text/attribute/url/value、严格数量校验、显式缺失默认值及类型化字段引用。输出直接绑定结果，供现有 foreach/条件/poll 消费；没有修改执行器、浏览器生命周期或公共数据契约。
- 读取由单次同步 Locator.evaluate_all 回调完成；错误保留行与字段路径，原生错误转为 ExtractError。行内字段明确使用 CSS，不跨 iframe/Shadow DOM；没有自动等待、转换语言、隐式重试或兼容适配。
- 新增 tests/test_extract.py 和离线 dom-data-extraction.yaml；同步 README、DESIGN、示例说明及本地插件文档/模板。过程文档变动限于 T06 提交/推进记录、T07 当前阶段与系列进度，实际文件范围与计划一致。
- 开发回归：uv run --locked --no-sync pytest tests/test_extract.py tests/test_foreach.py -q，最终 76 passed（0.25s）；新 YAML 静态校验通过。3 个变更 Python 文件 Ruff format --check、Ruff check 和 mypy 均通过。
- 本机 Chrome 离线示例完成 11 个顶层步骤及嵌套 foreach/if 提取：返回两行记录、保留内部双空格、区分原始 href 与按 HTML base 解析的 URL、读取动态 input 值 25、保留空串和 null/false/0 默认值、空集合返回 []。截图 output/development-t07/20261002/extracted.png 已查看。
- 同一真实浏览器中的最小读取检查通过：7 个成功读取覆盖标量集合、显式 null、false、嵌套 null/0 默认值、input/textarea/select 当前值；8 个预期失败覆盖缺失根、多根、缺失字段、多字段、非法 CSS、非表单 value、非法 URL 和缺失属性。临时浏览器已关闭。
- 真实示例首轮发现 Playwright 递归省略参数对象中的 None，导致默认对象的 null 字段丢失；已在传输边界 JSON 编码/解码修复，相关回归及真实示例复测通过。测试 mock 的三处类型标注也已修正。没有遗留必须修复事项。
- 未运行全量测试、覆盖率、真实材料业务或外部站点，未改写 dist 材料脚本，未安装/同步用户级插件。本项尚未进行正式 Verification 的 CLI 失败验收；现有失败出口未修改，真实示例失败时实际退出码为 1。
- 当前停在 Implementation，供用户自行测试，不创建 Verification、不暂存或提交 T07，不自动推进 T08。

用户自行试跑：

```powershell
uv run --locked --no-sync pomelo-pw run example/public/dom-data-extraction.yaml --headless -v
```

省略 --headless 可查看浏览器。以上开发检查不代替用户正式验收。

## Verification handoff

- 用户自行试跑通过后明确要求完成 T07 Verification；本轮 76 项提取/foreach 回归和 19 项 CLI 回归通过，5 个相关 Python 文件最终格式/lint/mypy 检查通过。
- 离线示例、真实嵌套 JSON 失败、continue 后续执行及结果清除、非法字段静态校验、普通文本失败与数据驱动失败摘要通过；失败退出码均为 1，正常路径为 0，证据已收集。
- 本轮发现并修复 CLI 文本摘要忽略既有失败原因的问题，没有改变 JSON 输出或退出码。实际新增产品/测试范围为 cli.py 与 test_cli.py，详见 [T07 Verification](../verification/20260930-dom-data-extraction.md)。
- 没有遗留必须修复事项，未运行全量测试或真实材料业务。当前停在 Verification，文档 Draft 待用户审阅，不暂存/提交或推进 T08。

## User review notes

- Verification 的真实嵌套失败场景发现 CLI 文本摘要只读取顶层 error，忽略已有 failed_step.error 而显示 Unknown error。修复限于 CLI 摘要与对应回归；数据驱动摘要同样从已有失败行读取原因。实际范围新增 src/pomelo_pw/cli.py、tests/test_cli.py，没有新增执行结果格式或推进 T08。
- 用户自行试跑反馈“All steps completed successfully”，随后明确要求先完成本任务 Verification，不推进后续任务。
- 用户要求按顺序推进，局部任务完成到可用状态后停止，由用户自行测试。
- 只做针对性回归和最小集成，不追求覆盖率；本项不自动提交或进入下一任务。
