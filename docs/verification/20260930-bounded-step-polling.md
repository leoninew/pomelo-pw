# T05 有界步骤轮询验证
最后修改时间: 2026-10-02 09:56:33

## Review status

Draft

## Flow mode and stage

标准模式 / standard，验证阶段 / Verification。Intent/Plan 已接受，Implementation 已交付；用户查看交付后明确要求开始验证，并再次限定“进行基本的测试就行”。本轮只运行针对性回归、离线最小集成和变更文件静态检查；已有验证完成，不追加测试。技术检查完成，本文待用户审阅，不自动推进 T06，不执行 Git 暂存或提交。

## Intent alignment

依据 [T05 Intent](../intent/20260930-bounded-step-polling.md)。轮询复用运行时结果与共享条件树，在查询后检查新结果，明确区分业务终态、查询错误、次数耗尽和总超时。

| 验收项 | 判定与证据 |
| --- | --- |
| 多步骤轮询体，条件读取本轮成功结果 | 通过；回归覆盖多步骤数据传递，离线示例两个任务均在第三轮进入终态 |
| 首次立即查询，明确间隔和总时限 | 通过；旧 ready 结果仍先被新查询替换，interval 从未满足的一轮结束起等待 |
| 正常终止与耗尽失败分别表达 | 通过；末轮恰好满足成功，次数/时间耗尽失败，真实 CLI 两种失败均退出 1 |
| 查询、条件、重试和等待共享预算 | 通过；回归覆盖 retry_delay、wait、interval、内层预算；真实慢查询及慢条件在 75ms 配置下各约 94ms 退出 |
| 显式读取重试，业务失败终态不自动重试 | 通过；子查询重试仍属于同一轮，离线业务 failed 正常终止轮询并进入结果汇总 |
| 顶层/嵌套条件、轮次、最近结果和具体位置 | 通过；真实 JSON 诊断保留 2.index-0.1.attempt-2.until、attempts=2 及最近 task 结果，回归覆盖内外两层诊断 |
| 不重放提交，while 耗尽不掩盖未完成 | 通过；失败 HTML 为 submitted/read/read，无提交重放；while 仍真时失败，恰好在上限变 false 时正常完成 |
| 超时后不发布迟到结果或启动后续步骤 | 通过；真实慢查询只运行一次，后续步骤未执行，runtime 结果保持空；迟到条件异常被消费 |
| continue 模式保持整体失败与诊断 | 通过；真实 CLI 继续执行至第 4 步并生成 continued.png，整体 success=false、退出码 1，保留截图及 HTML |

## Spec alignment

不适用，standard 模式跳过独立 Spec；按 Plan 中的明确契约核对。

## Plan alignment

依据 [T05 Plan](../plan/20260930-bounded-step-polling.md)。poll 必需 until 和非空 steps，timeout/interval 为正且有限的数字，max_attempts 为可选正整数，均支持完整类型化引用。条件和子步骤延迟解析，poll 不接受父 retry，成功输出为 attempts/elapsed_ms/results。

截止时间覆盖执行体、条件、子步骤重试及等待，嵌套共享最早截止时间；返回结果的发布留在截止时间检查之后，最近成功结果独立保留。耗尽和错误沿既有顶层证据收集路径传播，JSON 中增加轮询诊断。while 末轮重新判断及 on_error=continue 的失败汇总符合实施计划，没有旧契约适配。

计划中的静态实现交付已完成，用户本轮授权进入正式运行验证。没有引入 T06 请求步骤、后台调度、恢复、自动幂等性或真实材料解析。

## Actual diff summary

- 5 个产品 Python 文件新增 poll 注册/校验、轮询进度与预算传递、调度和失败诊断，以及 while/continue 失败语义。
- 2 个测试文件新增轮询回归并更新 while 上限断言；已有控制流测试文件含 CRLF 到 LF 的格式变化，忽略行尾空白后本次语义修改为 11 行新增、10 行删除。
- 新增离线 bounded-step-polling 示例，同步中英文 README、DESIGN、示例索引和本地插件说明/模板。
- 更新 T05 Intent/Plan、系列入口及 T03/T04 接受记录；本轮新增本 Verification。没有产品代码修复；只修正辅助验收脚本中的错误证据字段名。
- dist/material-parse-all-v4.yaml 已在实现阶段改写并移至当前目录，本轮仅静态校验，不修改或运行它。

## Expected vs actual changed files

| 范围 | 预期与实际 |
| --- | --- |
| 核心轮询 | src/pomelo_pw/polling.py、steps/poll.py、steps/base.py、steps/__init__.py、executor.py，符合计划 |
| 针对性测试 | tests/test_poll.py、tests/test_executor_control_flow.py，符合计划；其他两个测试文件仅运行回归 |
| 离线示例 | example/public/bounded-step-polling.yaml、example/README.md，符合计划 |
| 使用说明 | README.md、README_CN.md、docs/DESIGN.md、本地插件 SKILL.md/templates.md，符合计划 |
| 过程记录 | T05 Intent/Plan/Verification、系列入口、T03/T04 Verification 接受记录，符合授权 |
| 额外验收产物 | output/verification-t05/20261001223319 下的 fixture、辅助脚本和截图，均为忽略的验证产物 |
| v4 业务脚本 | dist/material-parse-all-v4.yaml 静态校验通过，不属于本轮代码变更或真实业务验证 |

## Test results

以下命令均从 D:/SourceCodes/mywork/pomelo-pw 执行，使用项目 Makefile 中既有的 uv run --locked --no-sync 工具入口；依据用户要求限定扫描/执行范围，没有运行全量 make test 或覆盖率。

| 命令/检查 | 结果 |
| --- | --- |
| uv run --locked --no-sync pytest tests/test_poll.py tests/test_executor_control_flow.py tests/test_loop.py tests/test_foreach.py -q | 120 passed，0.61s |
| Ruff format --check，7 个变更 Python 文件 | 通过，7 files already formatted |
| Ruff check，同一 7 个文件 | 通过 |
| mypy，同一 7 个文件 | 通过，无类型问题 |
| uv run --locked --no-sync pomelo-pw run example/public/bounded-step-polling.yaml --headless -v -o output/verification-t05/20261001223319/success | 通过，退出 0；5 个顶层步骤、2 个任务、每个 3 轮，summary 为 total=2/ready=1/failed=1 |
| uv run --locked --no-sync pomelo-pw validate dist/material-parse-all-v4.yaml | 通过，仅静态校验 |
| uv run --locked --no-sync python output/verification-t05/20261001223319/verify_boundaries.py | 通过：2 个真实 CLI 失败场景及 2 个真实浏览器异步超时场景 |
| git diff --check、git diff --cached --check | 通过 |

7 个 Python 文件为 executor.py、polling.py、steps/base.py、steps/poll.py、steps/__init__.py、tests/test_poll.py 和 tests/test_executor_control_flow.py。

实际边界证据：

- exhaustion.yaml：foreach 内轮询执行两次后耗尽，JSON 退出 1；诊断 results.task={status: pending, reads: 2}，具体路径 2.index-0.1.attempt-2.until。continue 后仍执行至第 4 步，整体失败，截图及 HTML 均保留。
- timeout.yaml：75ms 总预算在 interval 等待中耗尽，文本模式退出 1，错误包含 timed out 和 timeout=75ms。
- 慢查询：浏览器函数延迟 250ms，总预算 75ms，实际约 94ms 返回超时。随后等待在途操作完成，确认只查询一次、未执行下一步骤、未发布迟到 ready 结果。
- 慢条件：查询返回 pending 后，async until 延迟 250ms 抛错；实际约 94ms 在 until 阶段超时。迟到异常被消费，已成功发布的 task=pending 保留。
- 浏览器关闭后，在途操作集合为空，事件循环没有未取回异常。没有启动或复用开发服务器，全部场景在 about:blank 上执行。
- 初版辅助脚本误用了截图/HTML 的内部属性名 screenshot_path/html_snapshot_path；按现有 JSON 契约 screenshot/html_snapshot 修正后复跑通过。这是验收脚本问题，未改动产品输出契约，也未追加全量回归。

产物根：output/verification-t05/20261001223319。已查看 success/tasks.png、exhaustion/continued.png，显示两个终态及继续执行标记；读取 exhaustion/error-step-2.html 确认 submitted/read/read 的执行顺序。timeout 目录保留 error-step-1.png/.html。

## Missed or expanded scope

没有产品功能范围偏差。实现阶段对 on_error=continue 的修复直接保障耗尽失败不被掩盖；本轮未新增该行为以外的报告或重试功能。未执行真实 Casdoor 登录、教材解析、外部网站矩阵、全量测试或用户级插件同步，未操作相邻项目或开发服务器。

## Risks and incomplete items

- 本轮限定范围内没有必须修复的遗留项；Verification 为 Draft，等待用户接受。
- 浏览器已经发出的操作或 JS 可能在超时后继续执行，工具停止调度和发布，不能撤销副作用；查询之外的幂等性仍由调用方负责。
- 单调时钟截止时间不是硬实时保证，Windows/浏览器调度有开销；75ms 配置实测约 94ms，没有把迟到结果当作成功。
- v4 只通过静态校验，未验证生产页面并发变化、认证或真实解析。HTTP 请求、断言与全系列串联继续属于后续任务。

## Conclusion

T05 限定范围内验证通过，没有发现产品代码缺陷。针对性回归、离线示例、真实 CLI 失败退出码和异步超时边界均通过。当前停止在 Verification，等待用户审阅，不自动推进 T06，不自动暂存或提交。
