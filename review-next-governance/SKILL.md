---
name: review-next-governance
description: Use when finishing verified work, reporting completion, updating project queues, deciding next steps, recording risks, handling blocked or not-now items, or preventing conclusions from remaining only in chat, including after optional companion verification via superpowers:verification-before-completion.
---

# Review Next Governance

## 概览

把验证后的结果反馈回项目状态。任务完成不只是“代码改完”或“检查通过”，还要记录完成了什么、证据是什么、剩余风险是什么、下一步应该做什么，以及哪些事情暂时不做。

该 skill 覆盖 harness engineering 的这段：

```text
Verification -> Review / Next
```

## 什么时候使用

以下情况使用本 skill：

- 即将声明任务完成。
- 刚跑完测试、检查、probe、截图或人工验证。
- 发现了新的后续工作、风险或阻塞项。
- 用户问“接下来做什么”“继续”“现在应该做什么”。
- 需要更新 NEXT、backlog、queue、Done、Blocked 或 Not Now。
- PoC 或 ADR 结论不能只留在聊天里。

如果只是纯问答且没有改变项目状态，可以不更新队列，但仍应说明判断依据。

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
   - 优先写入项目已有的 NEXT、backlog、roadmap 或 issue。
   - 新发现不要只留在聊天里。
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

## 队列字段建议

通用队列可以使用以下分组：

```markdown
## Done In Current Phase
- 已完成且有证据支持的事项。

## Active Queue
1. [ready] 可以直接执行的下一步。
   - Layer: 当前层级。
   - Invariant: 必须保持的事实或边界。
   - Forbidden shortcut: 不能用什么捷径冒充完成。
   - Completion level: 目标完成级别。
   - Evidence: 当前已有证据。
   - Done when: 完成条件。

## Blocked
- 被外部条件阻塞的事项，以及解除阻塞需要什么。

## Not Now
- 当前阶段明确不做的事项。
```

项目已有格式时，优先遵循项目格式。

`Layer:` 应使用 `harness-engineering/references/layer-progression.md` 中定义的标准层级标签。若当前层级不明确，先用 `harness-engineering` 判断，不要临时发明新层级名。跨多个层级的任务应先记录当前阻塞层；后续层级只写在 notes、risk 或 done-when 说明里。

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
