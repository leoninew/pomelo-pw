# 流程模板索引

[Skill 入口](SKILL.md)

按任务选择具体模板，链接直接指向对应片段。模板中的 URL、选择器和示例数据需按实际应用调整；带 `name` 和 `steps` 的示例可作为完整流程，其余片段需放入已有流程。

## 浏览器操作与认证

| 模板 | 适用场景 |
| --- | --- |
| [简单导航与截图](references/templates-browser.md#simple-navigation-and-screenshot) | 打开指定页面并保存截图 |
| [登录流程](references/templates-browser.md#login-flow) | 填写账号密码、提交并等待登录后的页面 |
| [保存登录状态](references/templates-browser.md#save-login-state) | 登录成功后将 Cookie 和 localStorage 写入文件 |
| [复用登录状态](references/templates-browser.md#reuse-login-state) | 新流程加载已有认证状态，访问需要登录的页面 |
| [表单提交](references/templates-browser.md#form-submission) | 填写字段、勾选复选框并等待提交结果 |
| [响应式检查](references/templates-browser.md#responsive-testing) | 在桌面和移动视口分别截图 |
| [基线采集与比较](references/templates-browser.md#baseline-comparison) | 显式生成截图基线，后续运行比较并输出差异 |
| [SPA 导航等待](references/templates-browser.md#spa-navigation-wait) | 点击导航后等待 URL、网络和动画稳定 |
| [元素操作重试](references/templates-browser.md#flaky-element-with-retry) | 为偶发超时的点击或等待配置步骤级重试 |
| [常用选择器写法](references/templates-browser.md#common-selector-patterns) | 按 ID、角色、文本、测试属性或 CSS 定位元素 |

保存和复用流程必须解析到同一状态文件；模板统一使用 `output_dir: output/auth`。基线模板首次运行使用 `--var baseline_mode=capture`，后续省略该参数进行比较。详细约定见[登录状态复用](references/browser-and-http.md#login-state-reuse)和[截图基线比较](references/browser-and-http.md#screenshot---baseline-comparison)。

## 数据传递与控制流程

| 模板 | 适用场景 |
| --- | --- |
| [保留类型的运行时结果](references/templates-control.md#typed-runtime-results) | evaluate 返回 JSON，通过 args 和 results 在步骤间传递数据 |
| [处理可选界面元素](references/templates-control.md#handle-optional-ui-elements) | 提示条或弹窗存在时执行关闭分支 |
| [根据页面状态分支](references/templates-control.md#branch-on-page-state) | 根据是否处于登录页选择操作 |
| [循环滚动页面](references/templates-control.md#scroll-through-page) | 固定次数滚动后采集完整页面 |
| [点击加载更多完成分页](references/templates-control.md#load-more-pagination) | 加载按钮可见时重复点击，并设置最大迭代次数 |
| [组合页面就绪条件](references/templates-control.md#combined-page-readiness) | 在同一等待期限内同时检查 URL、元素和应用状态 |
| [遍历结构化结果](references/templates-control.md#collection-results) | foreach 串行处理数组，通过 item 和 index 绑定当前项 |
| [有界任务轮询](references/templates-control.md#bounded-task-polling) | 提交任务后反复查询，直到成功、业务失败或限制耗尽 |
| [结果收集与断言](references/templates-control.md#collected-outcomes-and-assertions) | collect 收集逐项结果，outputs 导出，assert 检查预期 |

页面状态就绪使用 `wait`；需要重新请求并更新运行时结果时使用 `poll`。先提交任务，再轮询；具体操作的重试放在子步骤上。详细约定见[运行时与控制流程](references/runtime-and-control.md)和[报告与导出](references/reporting.md#execution-report-and-exports)。

## HTTP、DOM 与数据驱动执行

| 模板 | 适用场景 |
| --- | --- |
| [使用浏览器会话提交 HTTP 请求](references/templates-data.md#browser-session-http-submission) | 使用当前 Cookie 调用接口，提交任务并查询响应 |
| [DOM 记录与表单值](references/templates-data.md#dom-records-and-form-values) | 将表格行映射为结构化记录，读取表单值并遍历 |
| [多用户测试](references/templates-data.md#multi-user-test) | 使用多组账号和预期页面，逐行执行同一登录流程 |
| [多环境检查](references/templates-data.md#multi-environment-check) | 使用不同 base_url 执行同一流程，分别保留结果 |

相对请求先导航或登录；DOM 提取前先明确页面就绪条件。多组输入使用顶层 `data`，单次流程中的数组遍历使用 `foreach`。详细约定见 [HTTP 请求](references/browser-and-http.md#request---browser-session-http)、[DOM 提取](references/browser-and-http.md#extract---dom-data-snapshot)和[数据驱动测试](references/reporting.md#data-driven-testing)。
