# T03 集合遍历实施计划
最后修改时间: 2026-09-30 20:08:02

## Review status

Accepted

## Flow mode and stage

标准模式 / standard，Intent/Plan 已接受，Implementation 已交付，当前为验证阶段 / Verification。用户已查看实现交付后明确要求“进行验证”，本轮进行针对性回归和离线最小集成，不自动推进后续任务。

前置依赖：T01 已由用户确认测试通过，T02 已交付并由用户提交。意图见 [T03 Intent](../intent/20260930-collection-iteration.md)。

## Proposed contracts

```yaml
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

- `foreach` 是独立步骤，必需 `items` 和 `steps`。`items` 接受原生 JSON 数组或完整引用；拒绝字符串、对象、null 和其他非数组值。静态校验检查声明，运行时检查解析后的值。
- `as` 默认为 `item`，`index_as` 默认为 `index`；两个字段为静态 ASCII 标识符，互不相同，不能使用保留根 `inputs`/`results`，不能通过模板动态指定。
- 索引从 0 开始，按数组顺序串行执行。空数组不准备或执行任何子步骤。子步骤仍在执行到该步骤时解析参数。
- 每次进入 foreach 固定一份 JSON 深拷贝快照，后续回写原结果不改变本次遍历范围；每轮元素绑定也独立复制。
- 元素和索引是只读的运行时局部绑定，可用 `{{item}}`/`{{inputs.item}}` 及字段、下标访问。绑定优先于普通输入和 CLI 覆盖；内层同名绑定暂时遮蔽外层，退出后恢复。普通变量优先级保持既有契约。
- 绑定数据保持不透明，其中包含模板样式的字符串不会再次解析。结果仍通过显式 save_as 发布，不自动聚合逐项结果。
- `loop` 只接受 times 或 while，必须且只能提供一种；times 为非负整数，max_iterations 仅用于 while 且为正整数。动态引用延迟检查；不接受 bool、浮点和字符串数字。repeat 仍为次数/条件循环别名，foreach 不再适配旧参数。
- 单步骤重试仅覆盖该步骤自身的执行/条件选择，控制体在重试范围外执行。子步骤可以声明自己的 retry；父 if/loop/foreach 的 retry 不重放控制体。
- 迭代内失败立即停止，错误文本含从 0 开始的集合索引、嵌套步骤路径与原错误，并沿既有截图/页面证据路径传播。已完成迭代和已完成写操作不重放。

## Implementation steps

1. 增加 ForeachStep、独立注册和声明/运行时校验，收紧 loop 的模式及整数参数校验。
2. StepContext 增加独立局部绑定；引用解析和条件求值使用不透明绑定快照，执行器传递嵌套绑定。
3. 控制体调度移出单步骤重试；增加串行集合执行和嵌套失败路径。
4. 增加离线 collection-iteration 示例，更新中英文 README、DESIGN、插件 skill/template 和示例索引。
5. 运行相关步骤、引用、条件和执行器回归；只运行新增示例及必要的受影响离线最小集成。

## Files to change

- `src/pomelo_pw/steps/foreach.py`、`steps/loop.py`、`steps/base.py`、`steps/__init__.py`。
- `src/pomelo_pw/substitution.py`、`conditions.py`、`executor.py`。
- 集合新增测试及受影响的 loop、引用、执行器测试。
- `example/public/collection-iteration.yaml`、`example/README.md`、`README.md`、`README_CN.md`、`docs/DESIGN.md`、仓库插件 skill/template。
- 本计划、T03 Intent 及系列入口。

## Verification plan

- 针对性回归：静态/动态非法输入、互斥模式、空数组、标量/对象、顺序、索引、嵌套遮蔽与恢复、CLI 同名、不透明字符串、快照回写、选择器/URL/条件/args 引用、子步骤重试及父控制体不重放、失败定位。
- 最小集成：本机 Chrome headless 运行离线 example，断言顺序和计数；受影响的 material v2 离线 fixture 覆盖正常、空列表及有界耗尽，不执行业务登录或解析。
- 仅对实际变更 Python 文件运行 Ruff format/lint 和 mypy；不跑全量测试或公共网站矩阵。

## Blockers and assumptions

暂无未决事项。遍历仅接受有限内存数组，绑定与普通配置变量分开，CLI 不可覆盖当前迭代值。v2 先作为 T01/T02 能力的迁移基线，T03 不额外重写其业务逻辑。

## Risks

- 旧 foreach times/while 调用必须改为 loop，没有兼容适配。
- 父控制步骤 retry 不再重放分支或循环体；需要重试的实际操作必须在子步骤声明。
- 深拷贝保证隔离但对大数组增加内存开销；不引入并发、流式处理、break/continue 或持久化。
- on_error 保持当前执行器策略，不能替代业务幂等设计；真实页面变动和认证需用户自行验证。

## Rollback

用户按本任务 diff 回退新增能力和调用迁移；不引入兼容开关或双契约，不操作用户 Git 暂存/提交。

## Implementation handoff

- 独立 foreach、快照遍历、局部不透明绑定、嵌套作用域和控制体重试边界已实现；中英文说明、插件模板及离线 example 已更新。
- v2 材料脚本已生成，保留原始文件；在 T03 修改前，离线正常/空列表/轮询耗尽 fixture 均通过，未执行业务登录或解析。dist 为忽略目录，v2 文件不出现在普通 git status 中。
- T03 首轮相关 6 个测试文件共 280 项通过。此后恢复 default_max_iterations 测试的类作用域并简化已由校验保证的 loop 分支；依用户“我自行测试”的新指令，不再运行回归或浏览器集成。
- 最终相关 9 个 Python 文件通过 Ruff format/lint 和 mypy。离线 collection-iteration 示例已编写，尚未试跑，交由用户测试。
- 旧 foreach times/while 必须改成 loop，父控制步骤 retry 不再重放控制体；没有兼容适配。

## Verification handoff

- T03 首轮相关 6 个测试文件共 280 项通过，9 个变更 Python 文件静态检查通过；没有运行全量测试。
- 离线 collection-iteration、v2 正常/空列表/轮询耗尽及 foreach 失败证据检查通过。
- 新增示例及 collection-results 模板的无效 about:blank 导航已移除。
- 完整结论和限制见 [T03 Verification](../verification/20260930-collection-iteration.md)。用户要求按任务分两批先后提交，并明确无需再次测试。

## User review notes

- 继续使用标准模式；用户自行提交，任务可用后停下。
- 用户限定针对性回归和最小集成，不进入全量测试或正式 Verification。
- 用户在本轮改为自行测试；此后仅进行必要静态检查，T03 的离线例子和最终回归未运行。
- 用户随后明确“进行验证”，授权本轮运行相关回归和离线最小集成；保留此前不跑全量测试、不执行真实教材解析和用户自行提交的约束。
