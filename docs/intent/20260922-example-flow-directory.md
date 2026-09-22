# 示例 Flow 目录重组
最后修改时间: 2026-09-22 12:55:13

## Review status

Accepted

## Background

现有 `flows/` 将面向用户的示例、实现验证用例、故意失败的错误收集示例和未配置完成的登录流程混在一起。文件名以 `test-` 开头，内容也包含虚构选择器，用户无法判断哪些 YAML 可以直接运行，哪些需要先适配目标系统。

## Goal

将示例目录重命名为 `example/`，按实际自动化场景组织一组可理解、可验证的 YAML flow，并通过 `example/README.md` 说明其用途、前置条件和运行方式。

## Non-goal

- 不增加新的 flow 步骤或修改步骤执行语义。
- 不在示例中写入真实业务账号、密码或私有 URL。
- 不修改历史需求与验证文档中的 `flows/` 引用。

## User scenarios

- 使用者需要一个网页冒烟检查，可直接运行公共页面示例。
- 使用者需要参考等待、条件、循环、数据驱动、JavaScript、视觉对比和浏览器状态能力。
- 使用者需要为自有站点编写表单或登录自动化时，能明确知道哪些变量和选择器必须替换。

## Acceptance

- 仓库根目录的 `flows/` 被 `example/` 替代。
- YAML 按 `public/`、`interactions/` 与 `state/` 主题目录组织，文件名描述业务场景而非测试目的。
- 每个示例的 `output_dir` 为 `output`，默认采用有头模式。
- `example/README.md` 提供场景表、运行命令、前置条件和状态文件依赖说明。
- `pomelo-pw list` 能发现 `example/` 下的嵌套 YAML。
- README、设计文档和内置 skill 的当前目录引用同步为 `example/`。

## Open questions

暂无需要用户确认的未决事项。

## Decisions

- 公共示例默认使用公开的 The Internet 演示站点；LinkedIn 冒烟检查保留其用户指定的公开目标。
- 登录认证不以伪造可运行流程示人，改为浏览器状态保存与复用示例，避免在仓库中保留凭据。
- 所有示例保留 CLI 变量覆盖方式，便于替换目标 URL 和选择器。

## Risk

公开演示站点可用性不受项目控制；README 将明确这些 flow 是学习和适配起点，不应直接作为生产探针。
