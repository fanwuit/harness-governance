---
name: review-next-governance
description: Use when finishing verified work, reporting completion, updating project queues, deciding next steps, recording risks, handling blocked or not-now items, or preventing conclusions from remaining only in chat, including after optional companion verification via superpowers:verification-before-completion.
---

## Harness Precondition

应用本 skill 前，先确认 `harness-engineering` 已经完成当前 layer 和本地治理义务判断。若尚未完成，停止本 skill，返回 `harness-engineering`；不要让本 skill 充当入口路由。

# Review Next Governance

## 概览

把验证后的结果反馈回项目状态。任务完成不只是“代码改完”或“检查通过”，还要记录完成了什么、证据是什么、剩余风险是什么、下一步应该做什么，以及哪些事情暂时不做。

该 skill 覆盖 harness engineering 的这段：

```text
Verification -> Review / Next
```

## 什么时候使用

以下情况使用本 skill：

- 完整 governed path 即将声明任务完成。
- 刚跑完测试、检查、probe、截图或人工验证，且结果会影响项目状态。
- 发现了新的后续工作、风险或阻塞项。
- 用户问“接下来做什么”“继续”“现在应该做什么”。
- 需要更新 NEXT scheduler、done archive、backlog、queue、Blocked 或 Not Now。
- PoC 或 ADR 结论不能只留在聊天里。

如果只是纯问答、只读分析或 trivial-safe-change，且没有改变项目状态、没有 durable follow-up、没有 blocked/not-now 项，可以使用 chat-only closeout：说明判断依据、验证和风险，但不更新队列。

## 收口流程

1. 汇总事实
   - 本轮实际改了什么。
   - 哪些验证已经运行。
   - 哪些验证没有运行，以及原因。
   - 是否有未提交、未固定或未验证的结果。

2. 判断状态
   - Done：当前阶段已完成且有证据支持。
   - Active / Ready：下一步可以直接执行。
   - Blocked：需要外部输入、权限、依赖或人工材料。
   - Not Now：明确不进入当前阶段的事项。

3. 更新稳定位置
   - 对 chat-only closeout（纯问答、只读分析、trivial-safe-change 且无持久后续项），不要为了仪式感创建 NEXT；在最终回复记录完成内容、验证和风险即可。
   - `NEXT.md` 或等价 active queue 只作为 scheduler，保留可执行 `[ready]`，必要时只允许短暂 `[active]`。
   - 已完成事项不要长期留在 `NEXT.md`；复杂 change packet 移到 `docs/changes/archive/<YYYY-MM-DD>-<change-id>/`，并把稳定结论同步回 ADR、schema、verification、README 或项目索引。
   - blocked / not-now 不要混入 ready scheduler；优先写入项目已有 issue、backlog、roadmap，或 `.harness/blocked.md` / `.harness/not-now.md`。
   - 会影响未来工作的新发现不要只留在聊天里。
   - 如果项目有 doc-map 或文档索引，新增文档后同步登记。

4. 决定是否继续
   - 如果下一项仍属于同一 focus 且用户没有要求暂停，可以继续。
   - 如果下一项会切换阶段、扩大范围或进入产品功能编码，应先汇报并等待确认。
   - 如果没有 clear ready 项，优先新增一个补 ADR、fixture、schema、probe 或 check 的 ready 项。
   - 如果连续 ready 都是 contract/check/readiness/governance，先应用 `contract-growth-control`，不要让队列无限增长治理产物。

5. 最终回复
   - 说明完成内容。
   - 说明验证命令和结果。
   - 说明剩余风险或未做事项。
   - 说明下一步，但不要把未验证结论说成完成。

## Completion / Review / Branch Finish

声明完成、处理评审反馈、请求 review 或收尾分支前，读取 `references/completion-review-branch.md`。该 reference 固定：

- completion evidence：命令、结果、新鲜度、覆盖范围、剩余风险和 skipped 原因。
- review feedback：分类 actionable / unclear / disagreed / not-now，先查证再改。
- requesting review：说明 reviewer 应重点看什么，不把自写测试通过当最终验收。
- branch finish：只作为 Review / Next 的可选执行动作，不自动 merge / push / open PR。

## 队列与归档建议

通用队列应保持为 scheduler，而不是历史记录。推荐 `NEXT.md` 只放当前可调度项：

```markdown
## Active Queue
1. [ready] 可以直接执行的下一步。
   - Layer: 当前层级。
   - Invariant: 必须保持的事实或边界。
   - Forbidden shortcut: 不能用什么捷径冒充完成。
   - Completion level: 目标完成级别。
   - Evidence: 当前已有证据。
   - Done when: 完成条件。
```

runner 认领任务时可以短暂写 `[active]`，但完成后应从 scheduler 移出。已完成历史进入 done archive 或项目长期记录：

```text
docs/changes/archive/<YYYY-MM-DD>-<change-id>/
```

如果完成事项没有 change packet，写入项目已有 issue/roadmap/done 记录；不要为了消除队列噪声而丢掉已完成事实、验证证据或决策链接。

项目已有格式时，优先遵循项目格式。

`Layer:` 应使用 `harness-engineering/references/layer-progression.md` 中定义的标准层级标签。若当前层级不明确，先用 `harness-engineering` 判断，不要临时发明新层级名。跨多个层级的任务应先记录当前阻塞层；后续层级只写在 notes、risk 或 done-when 说明里。

对 `Layer: implementation` 的 ready 项，补充以下字段：

```markdown
- Packetization: missing | ready | not-needed
- Task packets: path 或队列 section，指向自包含 implementation packets
```

如果 `Packetization: missing`，下一步应先补 task packets，不要直接启动 `superpowers:subagent-driven-development`。如果 `Packetization: ready`，task packets 必须包含 owner files、contracts、allowed assumptions、forbidden shortcuts、stop conditions、verification 和 done-when。

## 完成级别

可按项目需要使用这些级别：

- `idea-captured`：想法已记录，但未收敛。
- `brief-fixed`：目标、非目标和成功标准已固定。
- `decision-fixed`：ADR 或等价决策已固定。
- `contract-fixed`：schema、fixture、example、probe 或 check 已固定。
- `execution-pass`：某条执行链路跑通，但未必形成长期契约。
- `verified`：实现已通过匹配验证。
- `product-ready`：达到产品交付标准。

不要把低级别结果冒充高级别完成。

## 禁止捷径

- 不要在没有新鲜验证证据时声明完成。
- 不要把“下一步可以做什么”只写在聊天里。
- 不要把 blocked 项伪装成 done。
- 不要在当前 focus 已结束时自动进入更大阶段。
- 不要因为队列为空就直接写产品代码；先补缺失的 ADR、fixture、schema、probe 或 check。
- 不要把未验证的 PoC 结论写成已完成事实。

## 输出格式

收口汇报建议包含：

```markdown
完成：
- ...

验证：
- `command` -> pass/fail

未做 / 风险：
- ...

下一步：
- ...
```

如果用户只问下一步，先读取项目队列或状态文件；没有队列时，根据 harness engineering 层级提出应补的稳定产物。
