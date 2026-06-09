---
name: harness-visualization
description: Use when a project needs to initialize harness visualization, bootstrap harness status config, generate a read-only harness status view, summarize ready queue progress, summarize task packet checklists, audit autonomous runner markers, inspect checkpoint visibility, or produce machine-readable status JSON for agents or dashboards.
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
- Config：`.harness/harness-status.config.json`

## Status Contract

Dashboard 必须至少显示：

- Current layer：从 active/ready queue item 的 `Layer:` 推断。
- Ready queue：`[ready]`、`[active]`、`[blocked]`、`[done]` 数量和条目。
- Task packets：change packet `tasks.md` checkbox 完成度。
- Runner：最近 marker、轮次、退出码、checkpoint stop reason。
- Verification：最近验证摘要，以及缺失/失败/stale warning。
- Warnings：缺失 queue、缺失 task packet、无 checkpoint、无法解析的 invocation log。

## Project Integration

通用 layer 负责解析、刷新和展示；业务项目只提供状态源：

- 在 `NEXT.md` 或等价队列中为条目写 `Layer:`、`Change:`、`Packetization:`、`Evidence:`。
- 复杂任务使用 `docs/changes/<id>/tasks.md` checkbox 记录 packet 进度。
- autonomous runner 每轮写 `.harness/run-checkpoint.md` 和 `.harness/codex-exec-invocations.ndjson`。
- 路径不符合默认约定时，运行 `--init` 后只改 `.harness/harness-status.config.json`。
- 人看 `.harness/status.md`，agent 或后续 TUI/Web UI 读 `.harness/status.json`。

## Boundaries

- 不要把 dashboard 当作 gate；gate/check 失败仍由对应 readiness、contract、verification 规则处理。
- 不要静默修改队列状态；`--write-md` 和 `--write-json` 只写 status 输出。
- 不要从聊天记录恢复状态；只读取 repo 文件。
- 不要要求每个业务项目复制刷新逻辑；把自动刷新接在通用 runner 或通用命令上。
- 不要在本 skill 中实现 TUI/Web UI；先稳定 JSON contract，再由项目或独立工具消费。

## Common Mistakes

| Mistake | Correction |
|---|---|
| 只显示 pass/fail | 同时显示 layer、ready、packet、runner marker 和 verification。 |
| dashboard 自动改 NEXT | 只报告 warning；由 agent 或人按治理流程更新队列。 |
| 每个项目重写解析逻辑 | 复用脚本输出 JSON，让项目 UI 消费统一状态。 |
| 缺失 checkpoint 仍声称无人值守安全 | 标记 warning，并要求 runner 补持久记录。 |
