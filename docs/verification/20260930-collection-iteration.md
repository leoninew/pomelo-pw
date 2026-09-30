# T03 集合遍历验证
最后修改时间: 2026-09-30 20:08:02

## Review status

Draft

## Flow mode and stage

标准模式 / standard，验证阶段 / Verification。Intent/Plan 已接受，Implementation 已交付；用户明确要求“进行验证”，授权本轮执行针对性回归和离线最小集成。技术检查完成，本文待用户审阅，不自动推进下一任务或操作 Git 暂存/提交。

## Intent alignment

依据 [T03 Intent](../intent/20260930-collection-iteration.md)。独立 foreach 遍历 JSON 数组，稳定快照、局部元素和索引、串行顺序、嵌套隔离及失败定位均已实现；没有并发、流式集合、恢复、break/continue 或结果自动聚合。

| 验收项 | 结果与证据 |
| --- | --- |
| 原生数组、串行顺序、空集合和非法输入 | 通过；test_foreach 覆盖声明与解析后类型，空数组不解析缺失的子参数 |
| 当前元素及索引可用于参数和条件 | 通过；args/selector/url、exists/eq、字段/下标及原生类型回归通过，离线示例实际填写三个输入 |
| 嵌套绑定隔离、不泄漏 | 通过；同名内外遮蔽与恢复、CLI 同名覆盖、兄弟步骤及退出恢复回归通过 |
| 输入集合稳定快照 | 通过；回写源结果不改变活动遍历，结果中的模板样式字符串保持原文 |
| 失败定位、不重放此前写操作 | 通过；if/times/while/foreach 父重试边界回归通过，真实失败 HTML 仅记录 0,1，无重复或索引 2 |
| 循环模式互斥、递归校验、移除旧 foreach 适配 | 通过；次数/上限整数规则、嵌套路径及旧 foreach times/while 拒绝测试通过 |
| CLI 失败能被调用进程识别 | 通过；run --json 步骤失败/异常及 validate 校验失败退出 1，成功退出 0，失败诊断保持完整 |

请求体使用同一结构化参数引用机制；HTTP 专用步骤仍属于 T06，没有提前引入。

## Spec alignment

不适用，按 standard 模式跳过独立 Spec，精确契约由 Plan 定义。

## Plan alignment

依据 [T03 Plan](../plan/20260930-collection-iteration.md)。as/index_as 的静态标识符、0 起点、局部绑定优先级、不透明数据、控制体位于单步骤 retry 外等均符合计划。repeat 保留为 loop 的原生别名，foreach 独立注册，没有旧 foreach 转换。

离线示例初次试跑发现 navigate 不接受 about:blank。已移除新示例与 collection-results 模板中的显式导航，直接使用执行器创建的新空白页面；没有扩展 navigate 的协议或增加适配。T04 的等待取消修正见对应验证记录。

## Actual diff

| 计划范围 | 实际改动 |
| --- | --- |
| foreach、loop、注册和 StepContext | 新增独立步骤；互斥/整数校验；bindings 与配置 scopes 分开 |
| 引用、条件和执行器 | 不透明局部引用；延迟子步骤解析；串行快照遍历；控制体移出重试；错误路径 |
| 相关回归和离线例子 | test_foreach/test_loop；collection-iteration；修正多余 about:blank 导航 |
| 用户与 Agent 说明 | 中英文 README、DESIGN、example 索引、仓库插件 skill/template |
| 用户追加的 CLI 缺陷修复 | cli.py 统一 run 两种输出的失败退出行为，validate 校验失败退出 1；test_cli.py 针对性回归 |
| 阶段文档 | Intent/Plan、系列状态及本 Verification |

实际文件范围包括原计划和用户明确要求的 CLI 缺陷修复。conditions、DESIGN、README、插件及系列入口由 T03/T04 共享。本轮仅修改工作树，Git 暂存和提交由用户处理。loop.py/test_loop.py 的 CRLF 转 LF 是已交付实现为通过 diff 空白检查而进行的限定格式化。

dist/material-parse-all-v2.yaml 是用户明确要求的辅助迁移文件，受 Git 忽略；原始材料脚本保留。v2 仍以 T01/T02 能力作为迁移基线，没有额外重写其业务逻辑。

## Test results

T03/T04 首轮共同执行以下 8 个相关测试文件，共 **370 passed**，没有执行全量测试：

```powershell
uv run --locked --no-sync pytest tests/test_foreach.py tests/test_loop.py tests/test_wait.py tests/test_steps.py tests/test_conditions.py tests/test_substitution.py tests/test_executor_control_flow.py tests/test_executor.py -q
```

用户要求发现的问题当轮解决后，追加 CLI 与受影响等待的针对性回归，最终 **66 passed**。其中包含 7 个新增 CLI 用例和 2 个原生 JS 实际执行用例，不追求覆盖率，不重跑全量测试：

```powershell
uv run --locked --no-sync pytest tests/test_cli.py::TestRunCommand tests/test_cli.py::TestValidateCommand tests/test_wait.py -q
```

首轮 13 个变更 Python 文件通过 Ruff format --check、Ruff check 和 mypy；追加修复涉及的 browser_functions.py、cli.py、test_wait.py、test_cli.py 四个文件通过相同检查。工作树与暂存区 diff 空白检查通过。四个相关 YAML 和 collection-results 插件模板通过静态校验。

### Offline integration

- collection-iteration 在本机 Chrome headless 完整执行 4 个顶层步骤，内置断言确认 processed=2、filled=3，值为 red、{{literal}}、green；源数组被回写为空，迭代仍执行完整，普通 item/index 恢复为 restored/99。
- 真实 foreach 失败 fixture 配置父 retry=2，第二项报错后结果为 success=false；错误包含 2.index-1.1 (evaluate)。截图和 HTML 证据存在，HTMLParser 读取 writes=0,1，未重放成功项，也未继续到第三项。
- v2 fixture 使用本机 Chrome 和拦截路由模拟六条记录、分页、提交、503 重试及任务终态。正常汇总为 total=6/submitted=1/ready=2/failed=2/skipped=2；GET 调用计数为 task-r4=3/task-r5=1。
- v2 空列表全部计数为 0；耗尽场景在两次轮询后明确失败，summary 缺失，parse_state 保留最后一次成功读取的 pending 状态。原始前十个登录/导航步骤仅作结构一致性检查，没有执行登录。
- 同批 page-condition-wait 示例及真实等待边界检查通过，详情见 [T04 Verification](20260930-page-condition-wait.md)。
- 追加真实 CLI 子进程检查五个场景：离线 collection 示例成功退出 0；foreach 内 wait 超时退出 1 且保留 2.index-0.1 (wait)、25ms、截图和 HTML；无效配置的 run/validate 均退出 1；material v2 静态校验成功退出 0。每个 JSON 结果字段均与实际进程退出码一致。

产物根：output/verification-t03-t04/20260930191257。已查看 collection-pass/collection.png、wait-pass/ready.png 和 edges/failure/error-step-2.png，输入值、顺序和受控失败内容正常，没有内容重叠。

追加 CLI 夹具与产物位于 cli-exit-codes：failure.yaml、invalid.yaml、success/collection.png、failure/error-step-2.png/.html。等待包装修正后复跑的离线示例产物为 wait-success/ready.png。

## Missed or expanded scope

用户明确要求解决验收发现的问题，授权追加 CLI 退出码修复；没有推迟到 T08。新增示例/模板的无效导航和 T04 原生 JS 等待错误也已修正。没有运行公共网站矩阵、真实 Casdoor 登录、教材解析或相邻仓库操作，没有调整开发服务器。

## Risks and incomplete items

- 没有必须修复的 T03 遗留项；Verification 审查状态待用户接受。
- 旧 foreach 次数/条件调用必须迁移为 loop，父控制步骤 retry 不再重放控制体；没有兼容适配。
- 执行器不回滚已发生的浏览器写操作，失败项也可能已产生部分副作用；失败 fixture 中当前项 1 的写入仍保留。业务幂等由调用方负责。
- 大数组深拷贝的内存成本、外部页面/认证变化未作规模或生产验证；逐项结构化汇总与业务轮询仍属于后续任务。

## Conclusion

限定范围内技术验证通过，T03 可交付用户验收。运行检查仅覆盖本任务及共享基础行为，不能替代真实业务测试；不自动进入 T05。
