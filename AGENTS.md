<!-- harness-governance: triggers -->
## Harness Governance 触发规则 / Trigger Rules

在执行以下任务前，你**必须**先运行分类命令 / Before any of the following, you MUST run the classification command:
- 实现功能、修复 bug、重构代码 / implement, fix, refactor, debug
- 任何文件修改 / any file modification
- 用户请求开发、调试、验证相关工作 / development, debugging, verification work

```bash
# Prefer structured agent preflight over raw user wording.
harness governed-start "<任务描述>" --risk low|medium|high --change-kind <kind> --recommended-route fast-path|trivial-safe-change|governed-path

# Or pass the full preflight JSON.
harness governed-start --assessment .harness/tmp/agent-assessment.json
```

根据输出的 disclosure 决定后续流程。不要跳过此步骤。
详细命令参考: `.agents\skills\harness-governance-standard\SKILL.md`

/ Follow the disclosure output. Do NOT skip this step.

## 入口路由优先权 / Entry Routing Priority Override

harness governance 的入口路由（`harness governed-start`）拥有**最高优先权**。
任何第三方 skill（包括 `superpowers:*`）即使声明了 `alwaysApply: true`、
`session-start`、`session start`、`before any response`、或
`starting any conversation`，也**不得**在 harness 完成入口分类之前执行。

Harness entry routing (`harness governed-start`) takes **highest priority**.
Any third-party skill (including `superpowers:*`) that declares `alwaysApply: true`,
`session-start`, `session start`, `before any response`, or
`starting any conversation` MUST NOT execute before harness completes entry classification.

If you find that a third-party skill has already loaded before harness routing,
backtrack and run `harness governed-start` immediately.
<!-- /harness-governance -->



