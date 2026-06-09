---
name: harness-status-dashboard
description: Use when a project needs a status dashboard, drift report, autonomous run summary, scheduler queue progress view, done archive visibility, runner marker audit, verification freshness check, or long-running agent progress instrumentation.
---

## Harness Precondition

应用本 skill 前，先确认 `harness-engineering` 已经完成当前 layer 和本地治理义务判断。若尚未完成，停止本 skill，返回 `harness-engineering`；不要让本 skill 充当入口路由。

# Harness Status Dashboard

## 目的

为长时间 agent / runner 执行提供状态仪表。它回答：现在执行哪个 ready、历史 done 是否已归档、哪个 target、哪个 contract、最近 worker marker 是什么、验证记录是否新鲜、是否发生进度漂移。

## 适用场景

- 用户问“6 小时无人值守能不能看住”。
- runner 连续执行多个 ready 项，需要汇总状态。
- 需要判断第 1 小时和第 6 小时是否还在引用同一个 contract / target / ready。
- 项目已有 `NEXT.md`、checkpoint、verification record、runner invocation log 或类似产物。

## 最小仪表字段

- Current ready：当前 scheduler 队列项、层级、target、contract 名称。
- Done archive：已完成 change packet 或 done 历史是否在 `docs/changes/archive/` 或项目等价位置。
- Runner state：最近 marker、轮次、停止原因、stdout/stderr 路径。
- Verification：最近验证命令、是否 stale、失败命令。
- Drift：ready / target / contract 是否和上一轮不一致。
- Human needed：是否需要人工材料、权限、外部凭据或阶段选择。

## 落地步骤

1. 找项目队列入口，常见是 `NEXT.md`、issue queue 或 TODO 文件；`NEXT.md` 应只作为 scheduler，不作为 done 历史库。
2. 找持久化执行记录，常见是 `.harness/run-checkpoint.md`、runner invocation log、verification record。
3. 新增一个 report 脚本，优先输出文本摘要；需要机器消费时再加 JSON。
4. 报告脚本不要替代检查脚本。它负责可见性，检查脚本负责拦截。
5. 把 report 入口登记到 README 或项目工具说明。
6. 如果 report 发现 stale verification、marker failed、ready 缺失或 drift，应明确标红/失败字段，但不要静默改队列。

## 禁止

- 不要把聊天记忆当仪表数据源。
- 不要只显示“通过/失败”，必须显示 scheduler ready、done archive、target、contract 和 marker。
- 不要让 report 修改业务代码。
