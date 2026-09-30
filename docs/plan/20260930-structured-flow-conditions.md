# T02 统一数据与页面条件实施计划
最后修改时间: 2026-09-30 16:54:11

## Review status

Accepted

## Flow mode and stage

标准模式 / standard，计划 / Plan 已接受，当前为实现阶段 / Implementation。用户明确“没有未决事项就开始实现”，据此接受本计划。

前置依赖：[T01 Verification](../verification/20260930-runtime-result-context.md) 已接受。本计划定义 T02 的条件契约、实施范围和针对性验证方式。

## Current behavior

- `ConditionalStep._evaluate_condition()` 根据字符串是否含冒号区分页面条件和 JS，包含 URL、对象字面量或三元表达式的 JS 可能被误判。
- if 仅向条件函数传递 Page，无法直接读取 RuntimeContext 中的结构化数据。
- `_execute_step()` 预先替换 condition/while 中的模板，导致缺失字段在存在性判断前报错，也会让 while 固定使用进入循环时的数据。
- `_execute_loop()` 调用 ConditionalStep 的私有方法；没有供后续等待、轮询和断言使用的公共条件入口。
- validate 递归检查步骤，但不检查条件结构或操作符。

## Proposed contracts

### 1. 单一结构化条件语法

condition 和 while 都使用对象，每个条件节点必须恰好包含一个操作符。节点结构固定，操作数、页面参数和 JS args 可以引用输入及 results；整个节点不能通过字符串模板动态生成。

```yaml
- type: if
  condition:
    all:
      - exists: "{{results.record.file}}"
      - eq: ["{{results.record.enabled}}", true]
      - in: ["{{results.record.status}}", [ready, completed]]
      - page:
          element_visible: "#submit"
  then:
    - type: click
      selector: "#submit"

- type: loop
  while:
    not:
      eq: ["{{results.counter}}", 3]
  max_iterations: 4
  steps:
    - type: evaluate
      args: "{{results.counter}}"
      script: "counter => counter + 1"
      save_as: counter
```

示例中的 record/counter 需由前序步骤保存。新增离线 example 会包含初始化步骤，保证可以直接运行。

支持的节点为 `eq`、`ne`、`in`、`exists`、`all`、`any`、`not`、`page`、`js`。不接受旧冒号字符串、裸 JS 表达式或布尔值作为条件节点，也不猜测字符串类型。

### 2. 数据判断和类型规则

| 节点 | 参数 | 规则 |
| --- | --- | --- |
| `eq` | 恰好两个操作数的数组 | 按 JSON 类型比较；对象/数组递归比较 |
| `ne` | 恰好两个操作数的数组 | eq 的逻辑否定 |
| `in` | `[待判断值, 集合]` | 集合必须解析为数组，使用与 eq 相同的比较规则 |
| `exists` | 一个完整 `{{...}}` 引用 | 路径可读取为 true；未定义的根、字段、下标或不可继续访问的路径为 false |

- JSON 数字视为同一类型，`1` 与 `1.0` 相等；布尔与数字区分，`true` 不等于 `1`，`false` 不等于 `0`，该规则适用于嵌套值及 in。
- 对象比较不依赖键顺序；数组比较依赖顺序；不同 JSON 类型的值不相等。不进行文本、数字或布尔的隐式转换。
- exists 检查路径是否存在，不判断值的真假：已定义的 null、false、0、空字符串、空数组和空对象均为 true。检查非 null 可组合 exists 与 ne。
- exists 只将缺失引用错误转成 false；非法路径、循环引用及其他解析错误仍失败。参数必须是合法完整引用，不接受文本拼接或任意常量。
- 其他节点遇到缺失引用均失败，不隐式转为 null 或 false。调用方可以用 all 中先执行 exists 来保护后续判断。
- 操作数沿用 T01 的模板、快照和不透明结果规则。CLI `--var` 仍为文本，数值或布尔比较使用 YAML 原生输入或明确的脚本转换。

### 3. 组合与短路

- all/any 接收非空的条件数组，按 YAML 顺序执行；all 在首个 false 后停止，any 在首个 true 后停止。
- not 接收一个条件对象，返回其逻辑否定。空数组、数组形式的 not、多操作符节点和未知操作符均校验失败。
- validate 检查整个树的结构，包括可能被短路跳过的节点；运行时只解析和求值实际访问的节点，不提前替换整棵条件树。
- 条件错误是执行失败，不是 false。有效结构中未被短路访问的缺失引用或 JS 运行错误不会触发。

### 4. 页面判断

```yaml
condition:
  all:
    - page: {url_contains: "/tasks/"}
    - page: {element_visible: "h1"}
    - page: {text_contains: "Completed"}
```

page 节点也必须恰好包含一个操作符，参数解析后为非空字符串：

| 操作符 | 单次检查行为 |
| --- | --- |
| `element_exists` | Playwright locator 至少匹配一个元素 |
| `element_visible` | 首个匹配元素存在且可见 |
| `element_hidden` | 无匹配元素，或首个匹配元素不可见 |
| `url_contains` | 当前 URL 包含指定文本 |
| `url_matches` | 当前 URL 满足 Python 正则 search，非法正则为错误 |
| `text_contains` | 使用 Playwright 文本匹配规则检查 DOM 文本，不匹配 HTML 标签或属性 |

页面检查是即时探测，不增加等待、轮询或重试逻辑。多个匹配元素的可见性明确以首个元素为准。text_contains 改用文本定位，其空白归一化遵循 Playwright，原先依赖 HTML 源码匹配的 flow 需迁移。

### 5. JS 谓词和结构化参数

```yaml
condition:
  js:
    script: "({task}) => task.status === 'ready' && location.href.includes('about:')"
    args:
      task: "{{results.task}}"
```

- js 接收对象，必需非空 script，仅允许额外的 args。script 使用同步或 async 函数表达式，保持原文；输入和结果只从 args 传入。
- 复用 T01 的浏览器函数调用包装器，包括未提供 args 与显式 null 的区分。函数返回值必须为布尔，不使用 JavaScript Boolean 或 Python bool 强制转换。
- JS 执行位置是页面；results/inputs 在执行器中解析为 args 快照，不注入 window 或 sessionStorage。
- 未返回值、非布尔返回、语法错误及抛出异常都使条件失败；不为旧表达式包装函数。
- 从 evaluate 提取小型公共函数调用 helper，供 evaluate 和条件共用；evaluate 的输出、console 收集和监听器清理保持 T01 契约。

### 6. 解析时机与共享入口

- 增加公共的条件校验和 async 求值入口，接收 StepContext，供 if、while 及后续 T04/T05/T08 调用；不通过 ConditionalStep 的私有方法耦合执行器。
- 利用已有 `StepSpec.literal_params` 将 if.condition 和 loop.while 原始定义保留到条件求值阶段；子步骤的延迟准备机制继续使用 T01 实现。
- 每次求值开始获取有效输入和命名结果的快照，递归组合中的各节点使用同一份数据快照；页面状态按节点实际执行时探测。
- if 在选分支时求值；while 在每次执行循环体之前重新求值，读取上一轮子步骤已经发布的结果和当前循环作用域。
- 条件失败沿现有步骤失败路径传播，并保留节点位置。循环次数上限、控制体重试和执行报告不在 T02 改写。

### 7. 校验与错误定位

- 离线 validate 检查节点形状、已知操作符、参数个数、exists 路径语法、页面参数及 js 字段；不执行 JS，不要求动态结果已经存在。
- 对完全静态的操作数检查 JSON 和参数类型；含引用的实际类型在求值时检查。非法字面量正则可离线拒绝，带模板的正则运行时检查。
- if/loop 的 validate_params 调用同一个条件校验器，复用现有步骤递归路径。例如：`steps[2].then[1] (if): condition.all[0].in`。
- 数据操作数中的对象仍是业务数据，不作为条件 AST；不能因对象键恰好名为 all/page/js 就递归校验它。

## Implementation steps

1. 建立 `conditions.py` 的递归校验、JSON 类型相等和数据条件求值，复用现有引用解析；只公开必要的引用语法校验入口。
2. 将 T01 函数调用包装器提取到公共 helper，接入页面检查和严格布尔 JS 谓词，保留函数参数传递规则。
3. if 和 loop 声明原始条件字段并调用公共条件入口，执行器每轮重新求值 while，消除条件预先替换和私有方法调用。
4. 添加条件结构与控制流程的聚焦回归，迁移仓库中受影响的旧条件测试。
5. 迁移现有 3 个条件 example 和插件模板，新增可直接运行的离线 `structured-conditions.yaml`，更新中英文说明及 DESIGN。
6. 完成必要开发检查后停在 Implementation，交付可用的 T02 供用户测试；正式 Verification 及 T03 推进等待用户指令。

## Files to change

| 文件 | 预期改动 |
| --- | --- |
| `src/pomelo_pw/conditions.py` | 新增公共条件校验和求值入口 |
| `src/pomelo_pw/browser_functions.py`、`steps/evaluate.py` | 提取并复用函数调用包装器，保持 evaluate 行为 |
| `src/pomelo_pw/substitution.py` | 公开必要的完整引用/路径语法校验，复用现有解析器 |
| `src/pomelo_pw/steps/conditional.py`、`steps/loop.py` | 新条件校验、保留原始定义、接入公共求值 |
| `src/pomelo_pw/executor.py` | while 每轮读取最新运行时数据，移除私有条件方法依赖 |
| `tests/test_conditions.py` | 新增数据、页面、JS、短路和校验矩阵 |
| `tests/test_conditional.py`、`test_loop.py`、`test_executor_control_flow.py` | 迁移旧语法，增加顶层/嵌套/循环的条件回归 |
| `tests/test_executor.py`、`test_substitution.py`、`test_steps.py` | 仅补充嵌套条件路径、引用语法和公共 helper 相关回归 |
| `example/public/conditional-content.yaml`、`incremental-content.yaml`、`runtime-results.yaml` | 迁移已有条件 |
| `example/public/structured-conditions.yaml`、`example/README.md` | 新增离线数据和页面条件串联示例 |
| `README.md`、`README_CN.md`、`docs/DESIGN.md` | 说明条件语法、类型、短路及迁移影响 |
| `plugins/pomelo-pw/skills/pomelo-pw/SKILL.md`、`templates.md` | 迁移 if/while 示例和 Agent 条件说明 |

不改依赖、锁文件、发布脚本、浏览器生命周期或相邻仓库。当前 `dist/material-parse-all-p0.yaml` 没有旧 condition/while 字段，T02 不必改写其业务脚本；具体分页、遍历和轮询仍由后续任务处理。

## Verification plan

按用户最新要求，只进行针对性回归和最小集成测试，不执行全量 pytest 或全仓库质量扫描。正式 Verification 在用户看过 Implementation 结果并要求验证后进入；Plan 阶段不运行产品测试。

| 矩阵 | 重点 |
| --- | --- |
| 数据 | null/false/0/空值的存在性，深层 JSON 相等，布尔与数字区分，数组成员判断及类型错误 |
| 解析 | 缺失根/字段/下标、null 后继续访问、非法路径、循环引用、输入别名及结果字符串保持原样 |
| 组合 | 顺序和短路、受保护的缺失字段、未执行 JS、空组合、多操作符及嵌套路径 |
| 页面 | 元素缺失/隐藏/可见、多匹配首元素、URL 冒号、正则错误及 DOM 文本匹配 |
| JS | 同步/async、结构化参数、特殊字符、script 原文、参数缺省/null、非布尔返回和异常 |
| 执行 | 顶层/嵌套 if、while 首轮与后续轮次最新结果、输入优先级、局部作用域及不执行分支 |
| 静态校验 | 旧语法拒绝、未知操作符、错误参数形状、未来结果引用及业务对象不误判 |

聚焦 pytest 入口如下；若实际实现未触及某个测试文件，不扩展测试范围。

```powershell
uv run --locked --no-sync pytest tests/test_conditions.py tests/test_conditional.py tests/test_loop.py tests/test_executor_control_flow.py tests/test_executor.py tests/test_substitution.py tests/test_steps.py
```

Ruff format/lint 和 mypy 显式传入 Files to change 中实际修改的 Python 文件，不使用 `src tests scripts` 目录级命令。YAML 只校验 3 个迁移 example 和 1 个新增 example；插件说明迁移后执行已有 `python scripts/install.py plugin check`，不执行 apply。

真实浏览器只运行离线 `structured-conditions` 和迁移后的 `runtime-results` 两个 example，使用独立产物目录；必要时用 `about:blank` 的受控 DOM 检查页面谓词。无需开发服务器、真实登录或业务解析，也不重复 T01 公共网站、状态保存及图像比较矩阵。

## Assumptions, blockers and risks

- 暂无必须由用户决定的未决事项；本计划采用以上精确语法，工作量仍估为 1-2 人日。
- 移除旧条件语法是明确的接口变化，所有外部 flow 需迁移，不提供兼容分支。
- 深层比较必须递归区分布尔和数字，直接使用 Python `==` 会产生误判；共享函数 helper 需聚焦确认 evaluate 未受影响。
- 若提前替换整个条件树，exists、短路和 while 最新结果都会失效；这些是本任务的重点验收项。
- 页面即时探测与等待是不同调用时机，T04/T05 会在该入口外定义时序；本任务不增加等待配置。
- 控制体重试及循环上限现有行为继续由后续任务修正，本次不能据此承诺写操作只执行一次或轮询耗尽失败。

## Rollback

代码、条件示例、测试及说明作为同一版本整体回退，不保留旧条件解释器或切换开关。本任务无业务状态持久化，不涉及数据库回退。

## Implementation handoff

- T02 已达到可用状态，当前停在 Implementation，等待用户自行测试。未创建 T02 Verification 文档，不推进 T03，不暂存或提交代码。
- 实现公共条件校验/求值入口，覆盖 eq/ne/in/exists、all/any/not、页面探测和严格布尔 JS 谓词；if/while 复用同一契约，while 每轮读取最新结果。
- 浏览器函数调用包装器提取至 `browser_functions.py`，evaluate 继续使用 T01 的 JSON、args、console 和监听器清理规则；旧条件字符串和裸 JS 条件直接拒绝。
- 实际产品改动为 2 个新增模块和 5 个既有模块；新增条件测试并迁移相关 5 个测试文件。`tests/test_substitution.py` 复用现有回归，未新增测试或修改该文件。
- 3 个既有条件 example、插件模板及中英文说明已迁移；新增离线 `example/public/structured-conditions.yaml`，同时更新 DESIGN 和 example 索引。
- 针对性回归：计划列出的 7 个相关测试文件共 259 项通过；修正类型标注相关的局部变量命名后，条件模块的 91 项再次通过。没有执行全量测试。
- 相关 13 个实际新增/修改的 Python 文件通过 Ruff format、Ruff lint 和 mypy；4 个新增/迁移的 YAML 通过静态校验；插件包 check 通过，未执行 apply。
- 最小集成测试仅运行 `structured-conditions` 和迁移后的 `runtime-results`，本机 Chrome headless 均通过。新示例循环 3 次后退出，嵌套分支保存 middle=2，最终 summary.count=3；参数缺省/null、源码原文、页面首元素可见性及文本匹配均通过。
- 产物目录为 `output/development-t02/20260930165108`；已查看 `conditions/conditions.png`，正文及 Count: 3 渲染正常。第二个示例不产生截图。
- 已知迁移影响：text_contains 现在匹配 DOM 文本而非 HTML 源码；多个元素的可见性以首个为准；外部旧条件 flow 需迁移为对象。循环耗尽、控制体整体重试继续由 T05/T03 处理。
- 未执行公共网站矩阵、浏览器状态/图像比较或真实业务登录及教材解析。`dist/material-parse-all-p0.yaml` 没有旧条件字段，未改写其业务脚本。
- 当前工作区也包含上一轮 T01 验收文档收尾；本次没有新增 T01 产品改动。

供用户自行试跑的最小入口：

```powershell
uv run --locked --no-sync pomelo-pw run example/public/structured-conditions.yaml --headless -v
```

## User review notes

- 用户要求按顺序推进 P0/P1 任务，并确认 T01 测试通过，当前进入 T02 Plan。
- 沿用“不做兼容适配”“当前局部任务可用后停止供用户测试”“只进行针对性测试”的约束。
- 用户明确“没有未决事项就开始实现”，本计划标记为 Accepted，进入 T02 Implementation；达到可用状态后停止供用户测试。
- 用户再次明确测试仅进行“针对性的回归和最小集成测试”，本次已按上述范围完成开发检查并停止，不自动进入正式 Verification。
