# Runner Contract

## 目的

`autonomous-ready-loop` 通过一次只运行一个可丢弃的 Codex worker，避免上下文窗口持续膨胀。runner 负责重复调度，仓库文件负责记忆，模型只负责一次有边界的执行尝试。

## 角色

- Runner：启动新的 `codex exec` worker，捕获输出，执行轮数/时间限制，检查 marker，并在风险出现时停止。
- Worker：读取仓库说明，执行一个 ready 项或有限批次，更新持久化文件，运行验证，并输出 marker。
- Queue file：定义下一个可执行项和阶段边界。例如 `NEXT.md`、`TODO.md`、issue export 或 backlog JSON。`NEXT.md` 应作为 scheduler，只保留可执行 `[ready]` 和必要时短暂 `[active]`。
- Done archive：保存已完成 change packet 或 done 历史，默认 `docs/changes/archive/<YYYY-MM-DD>-<change-id>/`；完成记录不要长期留在 scheduler。
- Checkpoint：记录上一个 worker 做了什么，以及下一个 worker 如何不依赖聊天历史继续。
- Invocation log：记录每一次 `codex exec` 调用的命令、开始/结束时间、退出码、marker、输出文件路径和摘要。
- Status output：由通用 `harness-visualization` 生成 `.harness/status.md` 和 `.harness/status.json`，供人类和后续 agent 查看当前 layer、scheduler queue、done archive、task packet、runner 和 verification 状态。

## 运行模式

### BoundedBatch

默认安全模式。runner 最多运行 `MaxRounds` 轮，适合初次验证、CI smoke test 或低风险批处理。推荐从 `MaxRounds=1` 开始。

### RunUntilBoundary

目标自治模式。runner 持续启动新 worker，直到达到项目边界或安全停止条件。此模式下 `MaxRounds` 是保险丝，不是任务目标；常见上限可以是 `50` 或 `100`。

使用 `RunUntilBoundary` 时，worker 仍然一次只处理一个 ready 项或明确允许的有限批次。上下文清理由“新 worker”实现，任务连续性由队列文件和 checkpoint 实现。

## 最小 Checkpoint

使用项目自己的路径，例如 `.harness/run-checkpoint.md` 或 `agents/run-checkpoint.md`。

```markdown
# Run Checkpoint

## Last Worker
- Started: <timestamp>
- Queue item: <id/title>
- Result: done | handoff | blocked | boundary | failed

## Durable State Updated
- <files or artifacts updated>

## Verification
- `<command>` -> pass | fail | not run, with reason

## Next Resume Source
- Queue: <path>
- First ready item: <id/title or none>

## Stop Reason
- <blank unless blocked/boundary/failed>
```

## 调用记录要求

runner 必须把所有 `codex exec` 调用记录持久化，不只是在终端打印最近一次输出。

建议路径：

- `.harness/codex-exec-invocations.ndjson`：每行一条结构化调用记录。
- `.harness/codex-exec/<timestamp>-stdout.txt`：单轮 stdout。
- `.harness/codex-exec/<timestamp>-stderr.txt`：单轮 stderr。
- `.harness/last-codex-message.md`：最近一轮最终回复，供 marker 解析。
- `.harness/status.md`：人类可读状态仪表。
- `.harness/status.json`：agent、TUI 或 Web UI 消费的机器状态。
- `.harness/harness-status.config.json`：仅当项目路径不符合默认约定时才需要。
- `docs/changes/archive/`：完成后的 change packet 归档目录；旧 `[done]` 队列项迁移时应先保留历史和验证证据。

每条 invocation log 至少包含：

- startedAt / finishedAt。
- round。
- queue item。
- command。
- exitCode。
- marker。
- stdout/stderr 文件路径。
- verification summary。
- commit hash 或 commit skipped reason。

如果用户要求“输出所有调用记录”，runner 应读取 invocation log 并汇总所有轮次，而不是只展示最后一轮。

## 状态刷新要求

runner 模板应在以下时机自动调用通用 `harness-visualization/scripts/harness-status.mjs --write-md --write-json`：

- worker 正常完成并跑完匹配 verification 后。
- runner 写入 timeout、failed、blocked、boundary 或 unrecognized marker checkpoint 后。
- 外部 runner 初始化项目路径时，可先运行 `--init` 生成 `.harness/harness-status.config.json`，但默认路径项目不需要配置。

业务项目不应复制可视化逻辑。业务项目只负责维护 scheduler queue、done archive、change packet、checkpoint、invocation log 和 verification 事实。

## Worker Prompt 要求

项目专用 worker prompt 应包含以下约束：

```text
只从仓库文件恢复状态。不要依赖上一轮聊天。
读取项目说明和队列来源。
只执行第一个 ready 项，除非配置明确允许有限批次。
保持改动在 ready 项边界内。
如果 ready 项进入实现代码，先运行 implementation-readiness-gate。
运行匹配验证。
退出前更新 scheduler queue、done archive、checkpoint 和必要的 verification record。
runner 会在 worker 退出后刷新 `.harness/status.md` 和 `.harness/status.json`。
只有项目规则要求自动 commit 且验证通过时，才 commit。
如果 context 看起来接近 70%，写 checkpoint 并输出 AUTONOMOUS_CONTEXT_HANDOFF。
最终回复必须且只能包含一个 AUTONOMOUS_* marker。
```

## Runner 安全默认值

- 使用 `codex exec`，不要使用交互式长聊天线程承载循环。
- 优先使用 `--sandbox workspace-write`。
- 不要把交互入口的 `--ask-for-approval` 传给 `codex exec`；非交互 worker 应依赖 `--sandbox workspace-write` 和失败退出机制。
- 不要使用 `--dangerously-bypass-approvals-and-sandbox`，除非外部环境已经单独沙箱化，且用户明确要求。
- 默认使用 `BoundedBatch` 和小 `MaxRounds`；当用户目标是自动完成当前阶段时，显式使用 `RunUntilBoundary`。
- 把 worker 的最终消息写到文件，并从该文件解析 marker。

## 继续条件

只有同时满足以下条件时，runner 才能继续启动下一轮：

- worker 成功退出。
- 最终 marker 是 `AUTONOMOUS_READY_DONE` 或 `AUTONOMOUS_CONTEXT_HANDOFF`。
- 队列中仍有 ready 项。
- 必需验证命令通过，或项目明确允许 worker 在下一轮继续修复且未超过失败阈值。
- 没有边界越界或人工输入需求。
- 尚未达到 `MaxRounds` 安全上限。

否则必须停止并报告原因。
