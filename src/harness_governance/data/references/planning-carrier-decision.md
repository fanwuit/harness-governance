# Planning Carrier Decision / 规划载体决策

For choosing between project queue, planning files, change packet, execution prompt pack, or task packet, avoiding multiple sources of truth for the same task.

用于选择 project queue、planning files、change packet、execution prompt pack 或 task packet，避免同一任务同时产生多套 source of truth。

## Decision Table / 决策表

| Situation | Carrier | Owner skill | Notes |
|---|---|---|---|
| 项目已有 `NEXT.md`、issue queue、checkpoint 或 scheduler | Project queue | `review-next-governance` / project rules | 不再额外创建 `task_plan.md`，除非用户明确要求。 |
| 复杂多步任务，但项目没有队列系统 | Planning files | `planning-with-files` | 使用 `task_plan.md`、`findings.md`、`progress.md`。 |
| 任务跨多个 harness layer，或需要 proposal/design/contracts/verification 合并存档 | Change packet | `harness governed-start` / `harness packet init` | 使用本项目 `docs/changes/<id>/` 模板，不兼容 `openspec/`。 |
| 已批准计划需要交给 fresh workers、subagents 或 integrator | Execution prompt pack | `execution-prompt-authoring` | 只打包执行提示词，不批准 scope。 |
| Implementation ready，但需要拆给 worker 执行 | Task packet | `governed-implementation-entry` / `execution-prompt-authoring` | 必须包含 owner files、contracts、stop conditions、verification、done-when。 |
| 只是一次性小修或单命令问题 | No durable carrier | Current owner skill | 仍在最终回复中记录验证和风险。 |

## Priority Rules / 优先级规则

1. Existing project queue takes priority over new planning files. / 现有 project queue 优先于新建 planning files。
2. Change packet carries cross-layer context but does not approve implementation. / Change packet 承载跨层上下文，但不批准 implementation。
3. Execution prompt pack appears only after a plan or packet is approved. / Execution prompt pack 只在计划或 packet 已批准后出现。
4. Task packet serves only implementation execution; it does not replace readiness or the Implementation Entry Record. / Task packet 只服务 implementation 执行，不替代 readiness 或 Implementation Entry Record。
5. If two carriers both apply, choose the one that can become the subsequent single source of truth, and place only a link at the other location. / 如果两个 carrier 都适用，选择能成为后续唯一 source of truth 的那个，并在另一个位置只放链接。

## Verification / 验证

After choosing, check:

选择完成后检查：

- Is there only one primary source of truth? / 是否只有一个主 source of truth。
- Is the current harness layer recorded? / 是否记录当前 harness layer。
- Is there a next layer candidate or stop condition? / 是否有下一层候选或 stop condition。
- Are no external workflow default artifact paths adopted? / 是否没有采用外部 workflow 的默认 artifact 路径。
