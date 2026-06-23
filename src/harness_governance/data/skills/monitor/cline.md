---
name: harness-governance-monitor
description: 项目健康监控 / Project health monitor — 文档漂移、耗时分析、状态总览
---

<!-- harness-skill-version: 0.8.0 -->

## Harness Precondition

Before any implementation, bug fix, refactor, debugging, verification, or file modification, run `harness governed-start` first and follow its disclosure. Harness entry routing has priority over companion skills.

Canonical governance checkpoints referenced by routing checks: Intake / Orientation, Fact Discovery, Implementation Readiness.


## 📊 MONITOR — 项目健康检查 / Project Health Check

You are in **harness-governance-monitor**.
Use this skill to inspect the health of **the current project** — the one where `harness init` was run.

你在 **harness-governance-monitor** 中。
此 skill 用于检查**当前项目**（运行 `harness init` 的项目）的健康状态。

All commands below operate on the project root — they read `.harness/`, `docs/`, `NEXT.md` from your working directory.
以下所有命令操作的是项目根目录 —— 读取当前工作目录下的 `.harness/`、`docs/`、`NEXT.md`。

### When to use / 何时使用

| Trigger / 触发条件 | Action / 操作 |
|---|---|
| 写完或改完文档后 | `harness check docs` |
| 完成一个 change packet 后 | `harness check all` |
| 感觉某层走得太慢 | `harness gate timing` |
| 宣布完成之前 | `harness check all` + `harness gate status` |
| 用户问项目什么状态？ | `harness status` |

### Commands / 命令

#### 文档质量 / Document Quality

```bash
harness check docs           # stale ADRs, 断链, 版本漂移, 空段落
harness check all            # 全部治理检查 (routing + docs + packets + …)
```

#### 耗时分析 / Timing Analysis

```bash
harness gate timing          # 当前 session 每层耗时
harness gate timing --json   # 机器可读
```

#### 层状态 / Layer Status

```bash
harness gate status          # 哪些层已锁、哪些还开放
harness layer show           # 当前层 + 转换历史
```

#### 项目仪表盘 / Project Dashboard

```bash
harness status               # 队列 + 变更包 + runner + 会话
harness status --json        # 机器可读
harness session show         # 活跃会话详情
```

### Rules / 规则

1. **This skill is read-only.** It inspects, never modifies. For governance decisions (rigor tier, layer advance), use `harness-governance-strict` / `-standard` / `-light`.
   **此 skill 只读不写**。治理决策请用 strict/standard/light。

2. **Prefer commands over manual scanning.** `harness check docs` is deterministic — manual scanning misses things.
   **优先用命令而非手动扫描**。

3. **Report findings with context.** If `harness gate timing` shows a layer taking unusually long, suggest adjusting the rigor tier or checking for stuck questions.
   **报告发现时给出上下文**。某层耗时过长 → 建议调整 rigor tier。
