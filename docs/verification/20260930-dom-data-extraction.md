# T07 DOM 集合与字段提取验证
最后修改时间: 2026-10-02 11:31:14

## Review status

Draft

## Flow mode and stage

标准模式 / standard，验证阶段 / Verification。Intent/Plan 已接受，Implementation 已交付；用户自行试跑通过后明确要求先完成本任务验证。本轮针对性回归、本机离线最小集成和静态检查已完成，发现的 CLI 文本摘要缺陷已修复；技术结论通过，本文 Draft 待用户审阅，不自动推进 T08 或执行 Git 写操作。

## Intent alignment

按 [T07 Intent](../intent/20260930-dom-data-extraction.md) 核对：单元素/集合提取、行内字段映射、明确缺失及多匹配行为、文本清理、原始属性与绝对 URL、当前表单值、结果直接供 foreach/条件消费。源代码、相关回归和离线示例与以上目标一致；没有业务采集器、自动分页、转换语言或兼容适配。

## Spec alignment

不适用，标准模式未创建 Spec；精确契约在 Plan 中定义。

## Plan alignment

按 [T07 Plan](../plan/20260930-dom-data-extraction.md) 核对实现与文件范围。根使用 Playwright Locator，字段为行内 CSS，单次同步 evaluate_all 完成读取；参数 JSON 编码保留 null，输出沿用现有结果快照与执行预算。实现中发现并修复的 null 传输问题已有开发检查证据；本轮示例再次确认嵌套 null/false/0 默认值正确。CLI 摘要修复已同步到 Plan 的审查记录。

## Actual diff summary

- 新增 ExtractStep、注册、针对性测试和离线提取示例。
- 更新 README、DESIGN、示例说明与本地插件文档/模板。
- 同步 T06 提交/推进记录、T07 Intent/Plan 和系列进度。
- 本轮修复 CLI 文本失败摘要：优先读取顶层 error，接着读取 failed_step.error；数据驱动执行从已有失败行读取原因并显示行标签。新增三个对应 CLI 回归，没有改变 JSON 结果结构或退出码。
- 本轮新增 Verification，并同步 T07 Intent/Plan 与系列当前阶段。

## Expected vs actual changed files

| 范围 | Plan 预期 | 实际 |
| --- | --- | --- |
| 提取实现/注册 | steps/extract.py、steps/__init__.py | 一致 |
| 提取测试 | tests/test_extract.py | 一致 |
| 离线示例 | example/public/dom-data-extraction.yaml、example/README.md | 一致 |
| 使用说明 | README.md、README_CN.md、docs/DESIGN.md、本地插件 SKILL.md/templates.md | 一致 |
| 过程状态 | T06 Intent/Plan、T07 Intent/Plan、系列入口 | 一致；T06 为上一轮提交/推进记录 |
| 正式验收 | 本项 Verification | 已创建本文件 |
| 验证发现问题的修复 | 实施时未预计 | 新增 src/pomelo_pw/cli.py、tests/test_cli.py 的小范围修复及回归，已在 Plan 记录 |

当前产品、示例与过程文档共 18 个文件有变更。output 下的验收 fixture 和证据被 Git 忽略，不属于提交范围；没有额外改动执行器、浏览器生命周期或共享结果格式。

## Acceptance criteria checklist

- [x] 支持 text、attribute、url、value。textContent 默认只去首尾空白，内部空白保留；属性与表单值保持字符串，不隐式转换。
- [x] all 按 DOM 顺序返回；字段在行内 CSS 匹配，单次同步回调读取所有字段。离线示例返回 a/b 两条记录，映射及嵌套消费正确。
- [x] 必需字段缺失失败，可选字段使用 null 或明确 default；空串、false/0/null 保留。示例及真实嵌套缺失场景通过，没有丢弃记录。
- [x] 空集合返回 []；one 的零匹配默认失败，可显式 optional；多匹配始终失败。当前 continue 场景确认零匹配失败与旧结果清除，Implementation 的真实多匹配检查证据见 Plan。
- [x] 原始 href 和绝对 URL 分离。当前示例确认 ./a.pdf、../b.docx 的原始值，以及基于 HTML base 的绝对 URL。
- [x] 结果直接供 foreach/if 使用，嵌套参数在执行时解析，无 sessionStorage 中转；结果绑定与 poll 迟到输出丢弃的针对性回归通过。
- [x] 提取不负责页面等待；示例先 wait 就绪后读取，源码中没有等待或 DOM 写操作。用户自行试跑和本轮 CLI 示例均通过。
- [x] 错误包含嵌套步骤、数组迭代及字段位置，真实失败返回退出码 1，并生成截图/HTML；continue 会运行后续检查，但最终仍失败。文本摘要现正确报告具体原因。

## Test results

- 用户自行运行离线示例反馈“All steps completed successfully”。
- Implementation 的真实浏览器 7 个成功读取及 8 个预期失败检查见 Plan；它们是已有证据，本轮没有重新运行全套边界试跑。

所有命令在 D:/SourceCodes/mywork/pomelo-pw 执行，使用 Makefile 既有 uv run --locked --no-sync 入口；按用户范围收窄到相关文件，不调用全仓库 make check/test。

| 本轮命令/场景 | 结果 |
| --- | --- |
| pytest tests/test_extract.py tests/test_foreach.py -q | 76 passed，0.24s |
| pytest tests/test_cli.py -q | 19 passed，0.17s；含本轮新增 3 个摘要回归 |
| Ruff format --check / Ruff check / mypy：extract.py、steps/__init__.py、test_extract.py | 均通过，3 个文件 |
| Ruff format --check / Ruff check / mypy：cli.py、test_cli.py | 最终均通过，2 个文件；mypy 要求的类型标注已补齐 |
| validate example/public/dom-data-extraction.yaml --json | 退出 0，valid=true |
| run example/public/dom-data-extraction.yaml --headless --json -o output/verification-t07/20261002-112314/positive | 退出 0，11 个顶层步骤完成；生成 extracted.png，已查看 |
| nested-failure.yaml：run --headless --json | 退出 1，success=false；保留 foreach/if/extract 嵌套路径及 rows[0].fields.name，截图与 HTML 文件存在 |
| continue-failure.yaml：run --headless --json | 退出 1，success=false；6 个顶层步骤完成，旧结果清除及后续检查通过，after.png 存在 |
| invalid-schema.yaml：validate --json | 退出 1，valid=false；错误定位 steps[0].steps[0] 与 fields.link.attribute |
| 修复后 nested-failure.yaml / continue-failure.yaml：普通文本 run | 均退出 1，最终摘要含原始读取原因，没有 Unknown error；continue 仍运行后续截图 |
| 修复后 data-failure.yaml：普通文本 run | 退出 1，第一行通过、第二行失败；摘要含 Row second 及原始读取原因 |

验收 fixture 与证据位于 output/verification-t07/20261002-112314/。CLI 子进程均已结束，浏览器随执行关闭。Ruff 曾产生本地缓存写入警告，最后使用 --no-cache 的只读检查通过，没有更改配置或忽略规则。

## Missed or expanded scope

验证发现 CLI 最终文本摘要忽略已有失败原因，必须当轮解决；范围增加 cli.py 与 test_cli.py，修复及相关检查已通过。没有增加报告格式、断言能力或 T08 实现。

未运行全量测试、覆盖率、外部网站或真实材料解析，没有改写 dist 脚本、安装/升级依赖或同步用户级插件。没有实际检查内容被误写为通过。

## Risks and incomplete items

- 字段选择器为行内 CSS，不跨 frame/Shadow DOM；根选择器使用 Playwright。
- 文本与表单值保留字符串；提取不承担页面就绪等待。
- 快照只覆盖一次同步读取，不能阻止后续页面异步更新。
- 只验证受控的本机场景，不能替代真实业务选择器与规则验收。
- 本轮限定范围内没有必须修复的遗留事项；技术检查通过，Verification 为 Draft，待用户审阅。

## Conclusion

T07 限定范围内验证通过。95 项相关回归、5 个 Python 文件静态检查、离线示例、嵌套错误证据、CLI 失败退出码及 continue 行为均通过。发现的 CLI 文本摘要缺陷已当轮修复并回归验证；没有遗留必须修复事项。

当前停在 Verification，等待用户审阅，不自动进入 T08，不修改暂存区或创建提交。
