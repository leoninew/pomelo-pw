# Pomelo PW - 改进计划

## Phase 1: 立即实施 🔥

### 1. 变量替换转义 (P0 - Bug Fix) ✅ COMPLETED

**问题**: JS 模板字符串中的 `${token}` 会被误认为 flow 变量

**解决方案**: 采用双花括号语法 `{{ }}`
- `{{ var }}` - flow 变量替换
- `${ }` - 保持原样（JS/Shell 等）
- 向后兼容：同时支持 `${}` 和 `{{}}`
- **策略**: 如果字符串包含 `{{ }}`，则只处理 `{{ }}`，忽略 `${ }`

**示例**:
```yaml
variables:
  api_token: "abc123"

steps:
  - type: evaluate
    script: "const token = '{{api_token}}'; fetch(`/api?token=${token}`)"
```

**已完成**:
- ✅ 实现双花括号语法支持
- ✅ 保持向后兼容
- ✅ 添加单元测试（15 个测试全部通过）
- ✅ 更新文档（README.md, skill.md）
- ✅ 创建示例文件（flows/example-js-eval.yaml）

**文件**: `src/pomelo_pw/substitution.py`, `tests/test_substitution.py`

---

### 2. 失败时上下文信息 (P0 - 调试体验) ✅ COMPLETED

**价值**: 调试效率提升 10 倍

**自动收集**:
- 当前 URL
- 错误截图 (`./flow/error-step-N.png`)
- HTML 快照 (`./flow/error-step-N.html`)
- Console 错误日志
- Network 失败请求
- 页面可见文本摘要

**输出格式**:
```json
{
  "error": "Element not found: .submit-btn",
  "context": {
    "url": "https://example.com/login",
    "screenshot": "./flow/error-step-3.png",
    "html_snapshot": "./flow/error-step-3.html",
    "console_errors": ["[ERROR] Failed to load resource"],
    "network_errors": [{"url": "/api/user", "status": 500}],
    "visible_text": "Login failed. Please try again.",
    "step_index": 3,
    "step_type": "click"
  }
}
```

**已完成**:
- ✅ 实现 ErrorContextCollector 类
- ✅ 集成到 FlowExecutor
- ✅ 自动收集 console/network 错误
- ✅ 失败时自动截图和保存 HTML
- ✅ 控制台和 JSON 输出支持
- ✅ 更新文档（README.md）
- ✅ 创建测试 flow（flows/test-error-context.yaml）

**文件**: `src/pomelo_pw/error_context.py`, `src/pomelo_pw/executor.py`

---

## Phase 1 总结 ✅

**v0.2.0 已完成**:
1. ✅ 变量替换转义 - 支持 `{{ }}` 语法，避免 JS/Shell 冲突
2. ✅ 失败时上下文信息 - 自动收集错误截图、HTML、console/network 错误

**测试状态**: 51/51 通过
**类型检查**: 通过 mypy strict mode
**文档**: 已更新 README.md, skill.md

---

## Phase 2: 短期实施 (1-2 周)

### 3. 增强 SPA 等待能力
**新增 wait 参数**:
```yaml
- type: wait
  url_contains: "/dashboard"      # URL 包含
  
- type: wait
  url_pattern: "^/user/\\d+$"     # URL 正则匹配
  
- type: wait
  network_idle: true               # 网络空闲
  timeout: 10000
  
- type: wait
  animation_stable: true           # 动画稳定
  
- type: wait
  route_stable: true               # 路由稳定
  duration: 500                    # 稳定持续时间
```

**文件**: `src/pomelo_pw/steps/wait.py`

---

### 4. Step 级 Retry
**功能**:
```yaml
steps:
  - type: click
    selector: ".flaky-button"
    retry: 3                       # 失败重试 3 次
    retry_delay: 1000              # 重试间隔 1 秒
    
  - type: fill
    selector: "input"
    value: "test"
    retry_on:                      # 仅在特定错误时重试
      - "timeout"
      - "element_not_found"
```

**文件**: `src/pomelo_pw/steps/base.py`, `src/pomelo_pw/executor.py`

---

## Phase 3: 中期实施 (2-4 周)

### 5. 页面快照/Locator 探索
**新增命令**:
```bash
pomelo-pw explore <url>            # 交互式探索模式
pomelo-pw record <url>             # 录制模式，生成 YAML
```

**功能**:
- 点击元素自动生成最佳 selector
- 实时显示多种 selector 选项（id、class、text、role、xpath）
- 录制模式：点击操作自动生成 YAML 步骤
- 参考 Playwright Inspector

**文件**: 新增 `src/pomelo_pw/explorer.py`, `src/pomelo_pw/recorder.py`

---

### 6. 登录态复用
**新增 steps**:
```yaml
# 保存登录态
- type: save-state
  file: ".auth/login-state.json"

# 加载登录态
- type: load-state
  file: ".auth/login-state.json"
```

**实现**: 使用 Playwright 的 `context.storage_state()`

**文件**: 新增 `src/pomelo_pw/steps/save_state.py`, `src/pomelo_pw/steps/load_state.py`

---

## Phase 4: 长期实施 (1-2 月)

### 7. 截图 Baseline Diff
**功能**:
```yaml
- type: screenshot
  file: "homepage.png"
  baseline: "baselines/homepage.png"
  threshold: 0.1                   # 允许 10% 差异
  diff_output: "diffs/homepage-diff.png"
```

**技术**: 使用 `pixelmatch` 或 `Pillow` 做像素对比

**文件**: 扩展 `src/pomelo_pw/steps/screenshot.py`

---

## 额外功能 (待评估)

### 8. 条件执行和循环
```yaml
- type: click
  selector: ".next-page"
  if: "page_count > 1"

- type: loop
  times: 5
  steps:
    - type: scroll
      distance: 500
```

### 9. 数据驱动测试
```yaml
data:
  - {username: "user1", password: "pass1"}
  - {username: "user2", password: "pass2"}

steps:
  - type: fill
    selector: "#username"
    value: "{{username}}"
```

### 10. 并发执行
```yaml
parallel:
  - flow: "test-login.yaml"
  - flow: "test-signup.yaml"
  max_workers: 2
```

---

## 实施原则

1. **向后兼容**: 新功能不破坏现有 flow 文件
2. **渐进增强**: 功能可选，默认行为保持简单
3. **文档先行**: 每个功能都要更新 README 和 skill.md
4. **测试覆盖**: 核心功能必须有单元测试
5. **性能优先**: 不影响现有 flow 的执行速度

---

## 版本规划

- **v0.2.0**: Phase 1 (变量转义 + 失败上下文)
- **v0.3.0**: Phase 2 (SPA 等待 + Retry)
- **v0.4.0**: Phase 3 (Explorer + 登录态)
- **v0.5.0**: Phase 4 (Baseline Diff)
