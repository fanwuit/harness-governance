---
name: harness-visualization
description: Use when a project needs to initialize harness visualization, bootstrap harness status config, generate a read-only harness status view, summarize scheduler queue progress, preserve legacy done records, summarize done archive and task packet checklists, audit autonomous runner markers, inspect checkpoint visibility, or produce machine-readable status JSON for agents or dashboards.
---

# Harness Visualization

## Harness Precondition

应用本 skill 前，先确认 `harness-engineering` 已经完成当前 layer 和本地治理义务判断。若尚未完成，停止本 skill，返回 `harness-engineering`；不要让本 skill 充当入口路由。

## Purpose

把 harness 执行状态变成可读、可机器消费的仪表层。它只观察项目状态，不推进队列、不修改业务代码、不替代 verification check。

## Quick Start

优先运行 bundled script：

```bash
node harness-visualization/scripts/harness-status.mjs --repo <project> --init
node harness-visualization/scripts/harness-status.mjs --repo <project>
node harness-visualization/scripts/harness-status.mjs --repo <project> --format json
node harness-visualization/scripts/harness-status.mjs --repo <project> --write-md --write-json
```

运行 `--write-md --write-json` 后，必须把当前状态以 CLI/对话紧凑面板展示出来；不要只告诉用户文件路径。

## Prompt Triggers

当用户写 `$harness-visualization init`、`use harness-visualization init`、`初始化 harness visualization` 或类似请求时：

1. 先遵守 `harness-engineering` 入口路由。
2. 在目标项目运行 `harness-status.mjs --repo <project> --init`。
3. 再运行 `harness-status.mjs --repo <project> --write-md --write-json` 生成当前状态。
4. 只报告缺失的状态源；不要伪造 `NEXT.md` ready 项、change packet、checkpoint 或 invocation log。

默认读取：

- Queue：`NEXT.md`
- Checkpoint：`.harness/run-checkpoint.md`
- Invocation log：`.harness/codex-exec-invocations.ndjson`
- Change packets：`docs/changes/*/tasks.md`
- Done archive：`docs/changes/archive/*/tasks.md`
- Config：`.harness/harness-status.config.json`

## Status Contract

Dashboard 必须至少显示：

- Current layer：从 scheduler queue 中 `[active]` / `[ready]` item 的 `Layer:` 推断。
- Scheduler queue：`NEXT.md` 中当前可调度的 `[ready]` 和短暂 `[active]` 数量与条目。
- Legacy queue records：旧队列里残留的 `[done]`、`[blocked]`、not-now 或其他非 scheduler 状态，必须保留显示并给出迁移 warning，不能静默丢弃。
- Task packets：活跃 change packet `tasks.md` checkbox 完成度，不把 archive 当作当前 packet。
- Done archive：`docs/changes/archive/<YYYY-MM-DD>-<change-id>/tasks.md` 完成历史摘要。
- Runner：最近 marker、轮次、退出码、checkpoint stop reason。
- Verification：最近验证摘要，以及缺失/失败/stale warning。
- Warnings：缺失 queue、缺失 task packet、无 checkpoint、无法解析的 invocation log。

CLI/对话紧凑面板必须至少包含 Current layer、Current ready、ready queue 数量、runner marker、runner round、checkpoint result、verification stale/failed、human-needed blocker、status 文件路径。若 blocker 是端口占用，显示端口、PID、进程名和命令行。

当 Current ready 指向 task packet、change packet 或等价任务包时，面板必须把 ready 作为大项，并读取任务包 checklist：显示任务包路径、完成数/总数，以及每条 `- [ ]` / `- [x]`。任务包没有 checklist 时要明确 warning，不要把 ready 级别状态误当作 task 级进度。

## Project Integration

通用 layer 负责解析、刷新和展示；业务项目只提供状态源：

- 在 `NEXT.md` 或等价队列中只保留可执行 `[ready]`，必要时保留短暂 `[active]`，并为条目写 `Layer:`、`Change:`、`Packetization:`、`Evidence:`。
- 复杂任务使用 `docs/changes/<id>/tasks.md` checkbox 记录 packet 进度。
- 完成后的复杂任务移动到 `docs/changes/archive/<YYYY-MM-DD>-<id>/`，让 dashboard 从 archive 读取 done 历史；迁移前旧 `NEXT.md` 的 `[done]` 仍会显示为 legacy records。
- autonomous runner 每轮写 `.harness/run-checkpoint.md` 和 `.harness/codex-exec-invocations.ndjson`。
- 路径不符合默认约定时，运行 `--init` 后只改 `.harness/harness-status.config.json`。
- 人看 `.harness/status.md`，agent 或后续 TUI/Web UI 读 `.harness/status.json`。

## Boundaries

- 不要把 dashboard 当作 gate；gate/check 失败仍由对应 readiness、contract、verification 规则处理。
- 不要静默修改队列状态；`--write-md` 和 `--write-json` 只写 status 输出。
- 不要从聊天记录恢复状态；只读取 repo 文件。
- 不要要求每个业务项目复制刷新逻辑；把自动刷新接在通用 runner 或通用命令上。
- 不要在本 skill 中实现 TUI/Web UI；先稳定 JSON contract，再由项目或独立工具消费。
- 不要只生成 Markdown/JSON 而不在 CLI/对话中展示状态面板。

## Common Mistakes

| Mistake | Correction |
|---|---|
| 只显示 pass/fail | 同时显示 layer、scheduler queue、done archive、packet、runner marker 和 verification。 |
| 只给 status 文件路径 | 刷新 status 后直接展示 CLI/对话状态面板。 |
| dashboard 自动改 NEXT | 只报告 warning；由 agent 或人按治理流程更新队列。 |
| 把 `[done]` 长期留在 NEXT | 保留显示为 legacy record，并迁移到 `docs/changes/archive/` 或项目 done 记录。 |
| 每个项目重写解析逻辑 | 复用脚本输出 JSON，让项目 UI 消费统一状态。 |
| 缺失 checkpoint 仍声称无人值守安全 | 标记 warning，并要求 runner 补持久记录。 |

## Hard visual rule
- 以 `Current ready` 作为调度大项（不是单个 task）。
- 当 `Task packets:` 指向任务文件时，面板必须读取 `## Task checklist` 中的 `- [ ]` / `- [x]`。
- 面板与 `.harness/status.md` 都应显示 `Task packet`、`Task progress`、逐项 `Tasks` 列表及 `[ ]/[x]` 状态。
- 当 ready 大项存在但 packet 无 checklist 时，必须给出可见 warning，并提示补齐 `Task checklist`。
