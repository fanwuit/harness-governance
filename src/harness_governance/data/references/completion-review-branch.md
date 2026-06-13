# Completion, Review Feedback, and Branch Finish

用于吸收 verification-before-completion、receiving-code-review、requesting-code-review、finishing-a-development-branch 的工程纪律，同时保持 `review-next-governance` 对 Verification -> Review / Next 的所有权。

## Local Owner

- Owner skill: `review-next-governance`
- Supporting skills: `agent-role-isolation`, `document-gardener`, `harness-visualization`
- Stable evidence: verification commands、review feedback decision、queue/done/not-now 更新、git status 摘要

## Completion Evidence Template

声明完成前，必须有新鲜验证证据；但这不等于每次都要写持久化 verification record。小型本地改动、纯问答、只读分析或 trivial-safe-change 且没有改变稳定项目状态时，可以把 evidence 写在最终回复中。

只有以下情况才写入 stable verification record、queue、checkpoint、change packet 或 done archive：

- 跨会话、长任务或 autonomous runner 需要恢复上下文。
- 验证结果会改变 done / ready / blocked / not-now / release 等稳定状态。
- 准备 commit、PR、push、release、publish 或交付他人 review。
- 修改了 checker、`package.json` scripts、status/runner verification、contract 或验证机制本身。
- 结果是 fail、skipped、partial、flaky，或存在 residual risk。

需要持久记录时，使用：

```markdown
## Completion Evidence
- Commands run:
- Result: pass | fail | skipped
- Freshness: <本轮运行时间或本轮证据>
- Coverage: <覆盖哪个 contract / readiness / bug / review comment>
- Residual risk:
- Skipped reason:
```

规则：

- 不能只写“测试通过”。
- `skipped` 必须写原因和风险。
- 失败验证不能包装成 done；应进入 blocked、active follow-up 或 not-now。
- 如果验证改变了项目状态，更新稳定文件，不只留在聊天。
- 如果只是局部 targeted check 通过且没有 durable follow-up，在最终回复中记录命令、结果和风险即可，不要为了仪式感创建 stable verification record。

## Review Feedback Template

处理评审意见时先分类，不盲从也不防御性拒绝：

```markdown
## Review Feedback
- Source:
- Feedback:
- Classification: actionable | unclear | disagreed | not-now
- Evidence checked:
- Decision:
- Changes allowed:
- Verification:
- Result:
```

分类规则：

- `actionable`：建议清楚、范围内、有证据或符合项目规则。
- `unclear`：需要上下文、复现步骤、期望行为或 owner 确认。
- `disagreed`：技术上不成立或会破坏已固定 contract；必须说明证据。
- `not-now`：有价值但超出当前层级、scope 或优先级；写入 not-now / backlog。

评审不能直接批准 implementation。若反馈要求改行为，回到对应的 Brief、ADR、Contract 或 Readiness。

## Requesting Review Checklist

请求 review 前确认：

- scope 与 brief / task packet 一致。
- contract 和 failure path 已更新。
- verification command 已运行或无法运行的原因已记录。
- 已说明 reviewers 应重点看什么。
- 没有把自写测试通过当最终验收。

## QA / Release Readiness

QA 和 Release 只提供完成前证据，不批准新 scope 或自动 shipping。共享边界见 `harness-engineering/references/local-qa-release-monitor-retro.md`。

```markdown
## QA / Release Readiness
- Real run / smoke checked: yes | no | not-needed
- Regression or contract coverage:
- Docs/version/changelog updated: yes | no | not-needed
- CI or local checks:
- Rollback / disable path:
- User approval needed before push/deploy/publish: yes | no
- Residual risk:
```

禁止：

- 不因为 QA pass 自动进入更大实现范围。
- 不自动 tag / publish / deploy / push / open PR。
- 不把 release readiness 当作用户批准。

## Branch Finish Boundary

分支收尾只是 Review / Next 的可选执行动作，不是默认 gate。

收尾前检查：

```markdown
## Branch Finish
- Current branch:
- Git status:
- Verification:
- Review / Next updated:
- Commit requested by user/project rule: yes | no
- Push/PR requested by user/project rule: yes | no
- Blockers:
```

禁止：

- 不自动 merge / push / open PR。
- 不因为 companion branch-finish 流程建议而创建 commit。
- 不在 dirty worktree 中覆盖无关用户改动。
- 不把 branch finish 当产品完成证明；完成证明仍来自 verification 和 Review / Next。

