# Harness Status Contract / Harness 状态契约

## Purpose / 目的

This reference is the shared source of truth for harness status display. `harness-visualization` owns the default implementation; `harness-status-dashboard` owns interpretation and diagnosis. Runners and README should reference this contract instead of duplicating field lists.

本参考是 harness 状态显示的共享事实来源。`harness-visualization` 拥有默认实现；`harness-status-dashboard` 拥有解释和诊断。Runner 和 README 应引用此契约，而非重复字段列表。

## Required Status Fields / 必需状态字段

A status view should surface these fields when the corresponding source exists:

状态视图应在相应来源存在时展示以下字段：

- Current layer: inferred from the active or first ready scheduler item.
  当前层级：从活跃或第一个就绪的调度器条目推断。
- Current ready: scheduler item title, target, contract, evidence, and packetization when present.
  当前就绪项：调度器条目标题、目标、契约、证据及分包信息（如存在）。
- Scheduler queue: current `[ready]` and short-lived `[active]` items.
  调度器队列：当前 `[ready]` 和短暂的 `[active]` 条目。
- Legacy queue records: stale `[done]`, `[blocked]`, not-now, or non-scheduler records preserved with migration warnings.
  遗留队列记录：过时的 `[done]`、`[blocked]`、not-now 或非调度器记录，保留并附带迁移警告。
- Done archive: archived change packets or equivalent done-history location.
  完成归档：已归档的变更包或等效的完成历史位置。
- Task packet progress: active task packet path, done/total count, and checklist items.
  任务包进度：活跃任务包路径、已完成/总数计数及检查清单条目。
- Runner state: latest marker, round, exit code, checkpoint result, stdout/stderr path, and stop reason.
  Runner 状态：最新标记、轮次、退出码、检查点结果、stdout/stderr 路径及停止原因。
- Verification: latest verification summary plus missing, failed, or stale warnings.
  验证：最新验证摘要以及缺失、失败或过时警告。
- Human-needed blockers: missing materials, credentials, permissions, stage choice, or port blocker details.
  需人工处理的阻塞项：缺失材料、凭证、权限、阶段选择或端口阻塞详情。
- Status outputs: human-readable Markdown path and machine-readable JSON path when written.
  状态输出：人类可读的 Markdown 路径和机器可读的 JSON 路径（写入时）。

## CLI / Conversation Compact Panel / CLI / 对话紧凑面板

When starting a runner, refreshing status, handling blocked/boundary/no-ready markers, or answering progress questions, show a compact panel directly in CLI/conversation. Do not only provide `.harness/status.md` or `.harness/status.json` paths.

启动 runner、刷新状态、处理 blocked/boundary/no-ready 标记或回答进度问题时，应在 CLI/对话中直接展示紧凑面板。不要仅提供 `.harness/status.md` 或 `.harness/status.json` 路径。

The compact panel must include at least:

紧凑面板至少应包含：

- Current layer.
  当前层级。
- Current ready.
  当前就绪项。
- Ready queue count.
  就绪队列计数。
- Runner marker and round.
  Runner 标记和轮次。
- Checkpoint result.
  检查点结果。
- Verification stale/failed signal.
  验证过时/失败信号。
- Human-needed blocker.
  需人工处理的阻塞项。
- Status file path.
  状态文件路径。

If the blocker is a port conflict, include port, PID, process name, and command line when available.

如果阻塞项为端口冲突，应在可用时包含端口号、PID、进程名和命令行。

## Task Packet Checklist Rule / 任务包检查清单规则

`Current ready` is the scheduling item. If it points to a task packet, change packet, or equivalent task package, the panel and Markdown status must show:

`Current ready` 是调度条目。如果它指向任务包、变更包或等效的任务包，面板和 Markdown 状态必须展示：

- Task packet path.
  任务包路径。
- Task progress as done/total.
  任务进度（已完成/总数）。
- Each `## Task checklist` item with its `- [ ]` or `- [x]` state.
  每个 `## Task checklist` 条目及其 `- [ ]` 或 `- [x]` 状态。

Do not collapse task packets into a single ready-level pass/fail. If a ready item references a packet but the packet has no checklist, show a visible warning and ask for a `Task checklist`.

不要将任务包折叠为单个就绪级别的通过/失败。如果就绪条目引用了包但该包没有检查清单，应显示可见警告并要求提供 `Task checklist`。

## Boundaries / 边界

- Status views are read-only visibility. They do not mutate scheduler queue, done archive, contracts, or product code.
  状态视图是只读可见层。它们不会修改调度器队列、完成归档、契约或产品代码。
- Dashboard diagnosis is not a gate. Gate failures remain owned by readiness, contract, verification, and review-next skills.
  仪表盘诊断不是门控。门控失败仍由 readiness、contract、verification 和 review-next 技能负责。
- Business projects should provide standard sources: scheduler queue, done archive, checkpoint, invocation log, change packet, and optional config.
  业务项目应提供标准来源：调度器队列、完成归档、检查点、调用日志、变更包及可选配置。
- Business projects should not copy visualization parsing logic; they should consume the shared script output or JSON contract.
  业务项目不应复制可视化解析逻辑；它们应消费共享脚本输出或 JSON 契约。
- TUI/Web consoles should consume the JSON status after this contract is stable; they are not part of the default status implementation.
  TUI/Web 控制台应在此契约稳定后消费 JSON 状态；它们不属于默认状态实现。
