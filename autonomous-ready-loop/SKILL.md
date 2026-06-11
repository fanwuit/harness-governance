---
name: autonomous-ready-loop
description: Use when Codex should run a project task queue autonomously through fresh short codex exec sessions, avoid context-window buildup, create checkpoint/handoff files, run until a project boundary rather than a fixed chat context, add or adapt an external runner, or define stop conditions for unattended ready-loop execution across NEXT.md, TODO.md, issue queues, or similar ready queues.
---

## Harness Precondition

应用本 skill 前，先确认 `harness-engineering` 已经完成当前 layer 和本地治理义务判断。若尚未完成，停止本 skill，返回 `harness-engineering`；不要让本 skill 充当入口路由。

# Autonomous Ready Loop

使用本 skill 建立或运行一个外部 harness：它反复启动新的短会话 `codex exec` worker，而不是让单个聊天线程承载全部历史。长期记忆必须来自仓库文件，而不是上一轮聊天上下文。

## 核心模式

每个队列项或有限批次启动一个短 worker：

```text
runner -> codex exec worker -> checkpoint + verification + optional commit -> runner decides continue/stop -> new codex exec worker
```

worker 每次启动后必须读取项目规则和队列文件，只执行被选中的 ready 项，退出前更新可持久化状态，并避免依赖前一轮聊天。

## 运行模式

- `BoundedBatch`：默认安全模式。使用较小 `MaxRounds`，通常 `1` 或 `2`，用于验证 runner 行为和低风险批处理。
- `RunUntilBoundary`：目标自治模式。runner 持续启动新的 `codex exec` worker，直到遇到 no-ready、blocked、boundary、failed、人工材料需求或安全上限。`MaxRounds` 在此模式下只是保险丝，不是任务目标。

当用户目标是“自动完成整个总任务”或“持续推进当前阶段”，优先设计为 `RunUntilBoundary`，而不是要求用户每几个 ready 手动重启。

## 使用流程

1. 确定队列来源和 ready 选择规则。优先使用项目已有格式，例如 `NEXT.md` 第一个 `[ready]`、GitHub issue label、`TODO.md` 或项目自己的 backlog。`NEXT.md` 应保持为 scheduler，只保留可执行 `[ready]` 和必要时短暂 `[active]`；已完成历史移动到 `docs/changes/archive/` 或项目 done 记录。
2. 确定持久化状态文件。至少需要 checkpoint 文件和队列文件；如果项目已有 verification record、ADR、schema、fixture 或 check，应优先复用。
3. 从 `assets/run-autonomous-ready-loop.ps1` 或 `assets/run-autonomous-ready-loop.sh` 复制并改造 runner 模板。
4. 编写项目专用 worker prompt，要求每个 `codex exec` worker 从仓库文件恢复状态、执行一个 ready、验证、写 checkpoint，并用 marker 结束。
   - 如果队列包含多个 gate、多个角色、subagent audit、integrator 或共享文件串行更新，先使用 `execution-prompt-authoring` 生成可审计 prompt pack。
   - 不要把复杂 runner prompt、worker prompt 或 integrator prompt 只留在聊天里。
5. 记录每一次 `codex exec` 调用。不要只保留最后一轮输出；runner 应持久化 invocation log、stdout/stderr 路径、退出码、marker 和验证摘要。
   - runner 每轮结束或写 checkpoint 后，应调用通用 `harness-visualization` 状态刷新，写入 `.harness/status.md` 和 `.harness/status.json`。
   - runner/controller 报告启动、blocked、boundary、failed、no-ready 或恢复点时，必须在 CLI/对话中展示紧凑状态面板；不要只给 status 文件路径。
   - 状态面板至少包含 Current layer、Current ready、ready queue、runner marker、round、checkpoint result、verification stale/failed、human-needed blocker 和 status 路径。端口 blocker 必须显示端口、PID、进程名和命令行。
   - 如果 Current ready 指向 task packet、change packet 或等价任务包，状态面板必须把 ready 当作大项，并显示任务包路径、完成数/总数，以及每条 checklist 的 `- [ ]` / `- [x]` 状态。
   - 业务项目只维护 scheduler queue、done archive、checkpoint、invocation log 和 change packet；不要为每个项目复制可视化刷新逻辑。
6. 如果 ready 项会进入产品实现代码，worker 必须先应用 `implementation-readiness-gate`，确认目标本地 lint/test/contract/AGENTS 基线通过。
7. 如果 ready 项已经到 `Layer: implementation`，worker 只有在满足以下条件时，才可以在本轮短会话内部使用 `superpowers:subagent-driven-development`：
   - `implementation-readiness-gate` 通过，或项目已有等价 readiness evidence。
   - ready 项已展开为自包含 implementation task packets。
   - 每个 packet 都包含 owner files、contracts、allowed assumptions、forbidden shortcuts、stop conditions、verification 和 done-when。
   - packet group 能放进当前 worker 的 context、时间和改动规模预算。
   - 如果任一条件不满足，不要启动子代理；把缺失的 readiness 或 packetization 工作写回队列/checkpoint，并用合适 marker 退出。
8. 如项目需要强约束，新增或改造机械检查，用于验证队列格式、checkpoint 新鲜度、verification record、invocation log、status JSON 或停止条件 marker。
9. 首次运行用 `BoundedBatch` 小轮数确认行为稳定；确认后使用 `RunUntilBoundary` 自动推进到边界。

## 必须停止的情况

runner 遇到以下任一情况必须停止，不得继续自动开新 worker：

- 没有 ready 项。
- worker 非零退出。
- 必需验证失败且 worker 无法自行修复。
- worker 报告 `AUTONOMOUS_BLOCKED`。
- worker 报告 `AUTONOMOUS_BOUNDARY_REACHED`。
- worker 报告 `AUTONOMOUS_FAILED`。
- 下一个队列项会切换项目阶段、扩大到产品实现，或需要人工 review。
- implementation ready 项缺少完整 task packets，且当前 worker 的职责只是补 packetization 或记录边界。
- 工作区存在 runner 无法归因到当前 worker 的无关改动或未提交改动。
- 需要外部凭据、权限、截图、网络访问或人工材料。
- 达到 `MaxRounds` 安全上限。

## Context Handoff Guard

不要把精确 context telemetry 当作唯一机制，除非当前 Codex CLI 明确暴露该指标。应在 worker prompt 中写入自我停止规则：

```text
如果 context 使用量看起来接近 70%，或当前任务已经过大，不要继续扩大范围。写入 checkpoint 和队列状态，保留或拆分未完成的 ready 项，并以 AUTONOMOUS_CONTEXT_HANDOFF 结束。
```

runner 也可以使用可观测代理指标：最大轮数、单轮最长时间、最大输出大小、最大改动文件数，以及显式 handoff marker。

## Worker Markers

要求 worker 最终回复必须包含且只包含一个 marker：

- `AUTONOMOUS_READY_DONE`：选中的 ready 项已完成，且持久化状态已更新。
- `AUTONOMOUS_CONTEXT_HANDOFF`：状态已 checkpoint，应该由新 worker 继续。
- `AUTONOMOUS_BLOCKED`：需要人工输入或外部状态变化。
- `AUTONOMOUS_BOUNDARY_REACHED`：继续执行会跨越项目边界或阶段 gate。
- `AUTONOMOUS_FAILED`：实现或验证失败，且当前 worker 未能修复。

## 参考资料

实现项目专用 runner、prompt、checkpoint 格式或检查脚本时，读取 `references/runner-contract.md`。
