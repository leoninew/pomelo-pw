# T01 运行时结果与类型化数据引用实施计划
最后修改时间: 2026-09-30 16:05:52

## Review status

Accepted

## Flow mode and stage

标准模式 / standard，计划 / Plan 及验证交付 / Verification 已接受，后续进入 T02 Plan。

依据已接受的 [T01 Intent](../intent/20260930-runtime-result-context.md) 和 [任务系列](../intent/20260930-p0-p1-flow-capabilities.md) 编制。本任务只建立运行时数据底座，不提前实现 T02-T08 的条件、遍历、等待、请求、提取和报告能力。

用户已明确最终不做兼容适配。本计划按统一的新接口设计，移除相关旧语法分支和结果副本，迁移仓库内受影响的调用、测试和示例；不提供兼容开关或自动降级。

## Current behavior

- `StepResult.data` 同时承载 evaluate 的结果和 if/loop 的内部调度数据，尚无明确的公开输出字段。
- 顶层与嵌套步骤分别构造 StepContext，并仅传递变量快照；执行器没有共享的命名结果存储。
- `substitute_vars()` 将平面变量引用转成字符串，不识别字段路径，列表中的字典也未完整递归解析。
- README 和 DESIGN 声明 CLI 高于步骤与 flow 变量，但代码把步骤变量覆盖在已合并的 CLI 值之上，data-driven 行也会覆盖 CLI 值。
- `validate_flow()` 只检查顶层步骤，无法在运行前发现循环及分支中的绑定配置错误。

## Proposed contracts

### 1. 结果绑定与公开输出

- 使用通用步骤字段 `save_as: records`，名称为非空 ASCII 标识符，不允许模板、点路径或对结果对象内部字段的写入。
- `StepResult` 使用 output 公开数据、control 内部调度、diagnostics 诊断信息三个独立字段，并继续定义成功状态和消息。output 用缺省标记区分“没有输出”和“输出为 null”；移除混合用途的 data，不提供同名别名或旧访问方式的副本。
- `StepSpec` 声明步骤是否产生公开输出。T01 只为 evaluate 开启，后续 request/extract 使用同一契约；对无输出步骤使用 save_as 在校验时失败。
- EvaluateStep 的 output 为 JS 实际返回值，console 存入 diagnostics，不作为绑定值的一部分。if/loop 的分派信息存入 control，截图对比及浏览器状态操作的文件/计数信息存入 diagnostics；相关步骤、调用和测试直接迁移。
- 结果只允许 JSON 兼容的数据。以独立快照保存和引用对象/数组，避免参数或输入变量被步骤修改后连带改变结果存储。
- 绑定是赋值，不是追加。再次成功执行同名绑定覆盖旧值，集合输出收集由 T08 定义。
- 一次步骤执行的输入可以引用该绑定上一次成功的值；先捕获读取快照，再使待写绑定失效。参数解析或执行失败后不恢复旧绑定，避免继续执行时误用旧结果。
- 重试成功后发布一次最终结果；失败尝试和未执行步骤不发布结果，不向页面存储写入执行器状态。

### 2. 统一的类型化引用与文本拼接

| 写法 | 含义 | 输出规则 |
| --- | --- | --- |
| `{{name}}` | 当前步骤有效输入 | 整个参数仅含该引用时保留原生类型 |
| `{{item.path}}` | 输入对象的字段路径 | 与其他完整引用使用相同类型规则 |
| `{{inputs.filter}}` | 当前步骤有效输入中的字段 | 整个参数仅含该引用时保留原生类型 |
| `{{results.records}}` | 命名步骤结果 | 整个参数仅含该引用时保留原生类型 |
| `{{results.records[0].id}}` | 对象字段及数组下标 | 支持对象字段与从零开始的非负数组下标 |
| `/items/{{results.record.id}}` | 文本中的数据引用 | 标量转成文本，对象/数组插入文本明确报错 |

- 所有完整引用统一保留类型；未带命名空间的根标识符读取当前输入，inputs 是其显式命名空间，results 读取运行结果。支持字段和非负数组下标，不支持通配符、过滤、方法调用或任意表达式。
- inputs/results 是保留的命名空间，不允许 flow、data、步骤或 CLI 输入定义同名根变量；不为旧同名变量设置回退查找分支。
- 文本拼接中的引用统一使用 JSON 标量格式：布尔为 true/false，null 为 null，数字为数字文本，字符串原样插入。对象/数组不能拼入文本，不隐式沿用 Python repr。
- 路径语法错误、缺失字段、下标越界及在 null 上继续访问给出明确错误；最终值为 null、false、0 或空集合本身是合法数据。
- 输入定义中的模板可按同一规则递归展开，并检测循环引用；页面返回的结果字符串视为数据，不重新解释其中的 `{{...}}` 或 `${...}`。`${...}` 始终属于宿主语言。
- 原生引用值不重新作为模板解释。嵌套参数容器递归解析，但已取出的数据对象不再遍历替换。
- 普通模板参数用 `\{{` 表达字面量开头，解析后得到 `{{` 且不作为引用；脚本源码作为原文处理，业务数据统一从 args 传入。
- CLI `--var` 在本任务中仍定义为文本输入，不新增 JSON 自动解析；YAML 原生输入可通过完整引用保留类型，规则不因是否使用 inputs 前缀而改变。
- URL、selector、file 等仍须得到相应步骤需要的参数类型，工具不把对象或数组隐式转成字符串。

### 3. 运行生命周期与作用域

- 增加小型运行时上下文，按一次 `_run_once()` 创建；持有输入来源和命名结果，顶层及嵌套 StepContext 共享同一结果存储。
- data-driven 每行创建独立运行时上下文，不共享结果；浏览器生命周期和按行产物目录维持现有规则。
- 输入优先级统一为：CLI/`run_flow(variables=...)` 显式覆盖 > 当前步骤变量 > 最近的外层步骤变量 > 当前 data 行 > flow 变量。
- 父控制步骤的局部变量在其子步骤内可见，子步骤的局部变量不泄漏到后续兄弟步骤或父级。
- inputs 是当前步骤合并后的输入视图，results 是独立运行结果；save_as 不覆盖输入，无同名变量的隐式互相遮蔽。
- 已成功执行的子步骤结果可供后续步骤使用；本任务不提供分支结果事务或整组回滚。
- 不在 T01 改写控制体整体重试及循环耗尽行为；避免重放与有界终止的修正分别由 T03、T05 负责。

### 4. 解析时机与递归校验

- 使用共享的单步准备及结果发布逻辑，让顶层和嵌套步骤遵循同一数据契约；保留顶层进度、截图与失败证据行为。
- 控制步骤的 then/else/steps 保持原始步骤定义，进入具体子步骤时才合并变量、读取最新结果和解析参数。
- 通过 StepSpec 声明子步骤字段，供执行准备和递归校验识别；不把任意参数中名为 steps 的业务数据误判为子流程。
- StepSpec 明确不参与模板处理的原文字段，evaluate.script 属于此类；脚本中出现 `{{...}}` 不触发变量插值，避免数据与源码混用。
- 校验包括绑定名称、步骤输出能力、args 用法、子步骤列表结构和嵌套参数；错误路径示例为 `steps[2].then[1]`。
- 离线 validate 不执行 JS，也不因结果尚未生成拒绝合法的前置结果引用。数据是否存在以及具体类型在执行时验证。
- flow 级 output_dir 在执行前解析，只能读取输入；运行结果在此时不可用，相关引用应明确报错。既有相对路径和 CLI output 优先级不变。

### 5. evaluate 的单一函数接口

- 增加 `args` 参数，内容为单个 JSON 兼容载荷，可以是对象、数组、标量或 null；未提供和显式 null 必须区分。
- 脚本规范为同步或 async 函数表达式，统一通过 `page.evaluate` 的函数调用包装器执行；包装器接收原文 script、args 和是否提供 args 的标记，由函数自己命名参数，不拼接数据到 JS 源码。该标记用于区分 Playwright Python 默认合并的“未提供参数”和“显式 null”。
- script 不参与 flow 变量替换；需要使用输入或结果时通过 args 传入，仓库内源码插值示例随本任务迁移。
- 移除注入 module script、临时回调桥接及末尾 return 正则改写路径。旧裸模块代码迁移为 `async (args) => { ...; return value; }`，不做自动包装。
- 未提供 args 与显式 null 的参数处理有明确规则，但不根据旧脚本形式选择不同执行路径。
- console 使用页面事件收集，在完成或异常时清理监听器；不扩展为 JS 语法解析器，不继续维护模块适配测试。

### 6. 最小使用示例

以下是本任务采用的公开接口。

```yaml
name: runtime-result-example
variables:
  tag: local
steps:
  - type: evaluate
    script: "() => [{id: 'a', enabled: false}]"
    save_as: records
  - type: evaluate
    args:
      record: "{{results.records[0]}}"
      tag: "{{tag}}"
    script: "({record, tag}) => ({id: record.id, enabled: record.enabled, tag})"
    save_as: selected
```

后续步骤可引用 `{{results.selected.id}}` 或将整个 `{{results.selected}}` 作为结构化参数。此示例不需要 sessionStorage，也不涉及集合遍历或业务条件。

## Implementation steps

1. 建立运行时上下文及公开输出契约，定义结果缺省标记、JSON 数据范围、快照及失效规则；调用及测试直接使用新 StepContext/StepResult 接口，不增加旧构造适配。
2. 使用统一的完整引用与文本拼接规则，支持字段/下标和递归参数容器，定义未声明变量及循环引用错误，移除仅为旧字符串语义存在的分支。
3. 在执行器统一单步准备与绑定发布，分层保存 CLI/行/局部输入来源；顶层、分支及循环共享结果，data-driven 行隔离结果。
4. 为 StepSpec 声明子步骤与原文字段，推迟子步骤参数解析，加入递归校验；迁移控制和诊断结果字段，不提前实现后续条件与循环能力。
5. 将 evaluate 收敛为带 args 的函数表达式路径，提供唯一 output 和诊断信息，移除模块注入、桥接及旧返回副本。
6. 更新受影响的测试和仓库示例，包括 scripted-page-check 的模块脚本；新增最小结果示例，更新中英文说明和 Agent skill，让步骤规范能发现 args/save_as。
7. 在 Implementation 交付时展示实际 diff、已运行检查、接口变更及调用方迁移影响，等待人工验收后进入 Verification。

## Files to change

| 文件 | 预期改动 |
| --- | --- |
| `src/pomelo_pw/runtime.py` | 新增运行时上下文、结果数据契约及快照操作 |
| `src/pomelo_pw/steps/base.py` | StepContext、StepResult 输出、StepSpec 能力声明及通用 save_as 校验 |
| `src/pomelo_pw/substitution.py` | 类型化命名空间引用、路径读取和递归参数解析 |
| `src/pomelo_pw/executor.py` | 生命周期、输入分层、单步准备/发布、延迟解析及递归校验 |
| `src/pomelo_pw/steps/evaluate.py` | args、单一函数路径、唯一公开输出及诊断；移除模块适配 |
| `src/pomelo_pw/steps/conditional.py`、`src/pomelo_pw/steps/loop.py` | 声明子步骤字段并迁移 control；不提前实现数据条件、集合遍历或循环耗尽修正 |
| `src/pomelo_pw/steps/screenshot.py`、`src/pomelo_pw/steps/save_state.py`、`src/pomelo_pw/steps/load_state.py` | 现有文件、计数和对比信息迁移至 diagnostics，不改变浏览器操作本身 |
| `src/pomelo_pw/cli.py` | 完善通用绑定参数发现；验证发现 data-driven 成功后文本汇总读取缺失字段，补充按数据行汇总的最小修复，不修改 JSON 输出协议 |
| `tests/test_runtime.py` | 新增结果存储、快照及生命周期测试 |
| `tests/test_substitution.py`、`tests/test_steps.py` | 统一引用和类型/路径、新函数接口；移除模块适配测试 |
| `tests/test_executor.py`、`tests/test_executor_control_flow.py`、`tests/test_data_driven.py` | 嵌套校验、输入优先级、延迟解析、失败绑定及行隔离 |
| `tests/test_conditional.py`、`tests/test_loop.py` | 控制结果迁移到 control，原有控制行为的正确性回归 |
| `tests/test_cli.py` | 步骤规范输出及通用参数发现的必要回归 |
| `example/public/runtime-results.yaml`、`example/public/scripted-page-check.yaml`、`example/README.md` | 最小结果示例及原模块示例迁移 |
| `README.md`、`README_CN.md`、`docs/DESIGN.md` | 输出、统一引用、作用域、接口变更及迁移说明 |
| `plugins/pomelo-pw/skills/pomelo-pw/SKILL.md`、`plugins/pomelo-pw/skills/pomelo-pw/templates.md` | Agent 面向新契约的说明与模板 |

不预期修改依赖版本、锁文件、浏览器启动配置、发布脚本或相邻仓库。`docs/DESIGN.md` 若修改，应按当前阶段文档约定保留修改时间。

## Verification plan

Implementation 进行必要聚焦检查；正式 Verification 在用户看过实现摘要和风险后进入。用户已追加只进行针对性测试的约束，以下为收敛后的检查范围；历史已执行结果另见 Verification，不重复执行全量检查。

- 结果矩阵：null/false/0/空集合、嵌套对象和数组；无输出与 null 区分；成功覆盖、失败失效、重试最终发布及引用快照不发生别名修改。
- 引用矩阵：平面/字段/命名空间的统一原生类型、递归定义、文本插值、字面量转义、原文脚本、缺失和非法路径、下标越界、保留命名空间冲突及结果字符串不被重新解析。
- 执行矩阵：顶层结果到后续步骤、分支内结果到兄弟步骤、循环内覆盖绑定、局部变量不泄漏、子步骤引用刚生成结果、data-driven 行隔离。
- 优先级矩阵：CLI 与步骤、CLI 与 data 行、步骤与父局部、data 行与 flow 的冲突，并保留无 CLI 时行覆盖 flow 的现有用法。
- args 矩阵：同步/async 函数、未提供与显式 null、对象/数组、引号/换行/反斜杠、异常时监听器清理；旧裸模块脚本不再被适配执行。
- 校验矩阵：非法绑定、无输出步骤绑定、嵌套错误路径、未来结果引用不被静态拒绝、启动前 output_dir 不允许读取运行结果。

优先使用项目已有工具入口，按实际改动选择相关测试文件。T01 主体检查已完成；CLI 修复后的最后聚焦回归如下。

```powershell
uv run --locked --no-sync pytest tests/test_cli.py
uv run --locked --no-sync ruff format --check src/pomelo_pw/cli.py tests/test_cli.py
uv run --locked --no-sync ruff check src/pomelo_pw/cli.py tests/test_cli.py
uv run --locked --no-sync mypy src/pomelo_pw/cli.py tests/test_cli.py
uv run --locked --no-sync pomelo-pw validate example/public/runtime-results.yaml
```

以迁移后的 mock 测试覆盖新契约，同时在可用的本机 Chrome/Chromium 上运行 `about:blank` 的最小真实浏览器检查，核实 JS 参数序列化、监听器清理及结果绑定。不启动开发服务器，不依赖外部网站；浏览器不可用时明确记录未完成项，不声称浏览器行为已验收。

## Assumptions and blockers

- 暂无需要外部服务或用户额外参数才能编制本计划的阻塞项。
- Plan 使用上述命名空间与 save_as 契约，未默认接受任何后续任务的最终 API。
- 3-5 人日仍是估算，主要不确定性在嵌套输入作用域和受影响的仓库调用迁移；不再为双 evaluate 路径预留适配工作。

## Risks and migration

- CLI 优先级修正会改变依赖“步骤或 data 行覆盖 CLI”的 flow；这是明确的行为修正，需在实现摘要及文档中说明。
- 新增递归校验会提前拒绝原先因分支未执行而没有暴露的错误；校验不推断动态结果是否存在。
- 完整引用不再强制变成字符串，inputs/results 成为保留命名空间；依赖旧类型或同名变量的调用方必须迁移，没有兼容分支。
- 本计划仅扩展实际字段/下标引用，若需要包含点号的对象键或任意 JSONPath，应另行说明范围，不在实现中静默扩展。
- 模块注入和末尾 return 改写将移除；仓库内模块示例改为 async 函数，外部脚本调用方自行迁移。不为避免迁移而保留适配路径。
- StepResult.data 移除，公开返回、控制信息及诊断分别迁移；evaluate.script 内的输入插值迁移为 args。只迁移相关调用，不扩展截图或状态操作能力。
- 控制体重试、循环耗尽及 CLI 纯 JSON 输出仍由 T03、T05、T08 负责，不能因建立数据底座提前扩大本任务范围。

## Rollback

本任务不持久化业务状态，也不修改数据库。需要回退时，代码、示例和接口说明作为一组版本变更整体回退，调用方选择对应版本；不在新版本中保留旧路径或增加兼容开关。回退不涉及浏览器配置或业务服务。

## Implementation handoff (historical)

- T01 已达到可用状态：结果上下文、类型化引用、结构化 args、统一单步执行、递归校验及仓库调用迁移已实现。
- 开发检查：252 项 pytest 测试通过；Ruff format、Ruff lint、mypy 通过。
- 本机 Chrome 最小试跑通过：离线 runtime-results 示例完成 3 个顶层步骤及 1 个嵌套步骤；函数检查覆盖未提供 args / 显式 null、async 参数、console、非法脚本和不支持的 JSON 返回值。
- 插件包 check 通过；未执行 plugin apply，未提交代码。
- 示例直接使用浏览器初始 about:blank 页面，因为现有 navigate 只接受 HTTP(S)；未扩展导航能力。
- 必要调用迁移额外触及 tests/test_browser.py 的 _run_once 参数；未增加其他任务的产品能力。
- 尚未运行外部业务 flow 或公共网络示例。控制体整体重试、循环耗尽和 CLI 结果协议仍由 T03、T05、T08 处理。
- 按用户要求停在 Implementation，供用户自行测试；未创建 Verification 文档，不自动推进 T02。

## Verification handoff

- [T01 Verification](../verification/20260930-runtime-result-context.md) 已补齐并标记为 Accepted，用户确认 T01 测试通过。
- 13 个真实浏览器 example、CLI 聚焦 9 项测试及离线 Chrome 6 组契约检查通过；最终 CLI 修复仅复查相关文件。
- 历史全量 252 项测试发生在 CLI 修复及针对性测试约束之前，不作为最终全量回归结论。
- 用户要求的 `dist/material-parse-all-p0.yaml` 已静态校验及离线 fixture 验证，未执行真实业务解析；可选图像比较未试跑。
- 本地代码交付已有提交 `1af83db`。本次仅收尾文档并进入 T02 Plan，不执行 Git 写操作。

## User review notes

- 用户在任务拆分后要求“按顺序推进”，据此接受系列入口和 T01 Intent，并进入本计划阶段。
- 用户随后明确“但最终我们是不做兼容适配的”，本计划已移除旧模板分支、重复结果字段和模块脚本适配设计，改为统一新接口及仓库内调用迁移。
- 用户要求“开始实现”，视为接受本计划，进入 T01 Implementation。
- 用户要求当前局部任务达到可用状态后停止，留出自行测试过程；本轮完成 T01 和必要开发检查，不推进 T02 或正式 Verification。
- 用户随后要求“进行验证，可以拿 example 做基本测试”，据此进入 T01 Verification；只校验教材脚本，不运行真实解析。
- Verification 的 example 试跑发现已有 data-driven CLI 汇总缺陷：三行成功后因缺少 steps_executed 抛出 KeyError。已向用户说明，修复文本汇总分支并增加 CLI 回归；不扩展 T08 的结构化输出协议。
- 用户要求“只进行针对性的测试，不进行全量测试”，后续检查已收敛到相关文件、CLI 回归及离线浏览器契约。
- 用户要求“推进下一个任务”，并明确“T01 测试都已经通过了”；据此接受 T01 验证交付，进入 T02 Plan，不重复测试 T01。
