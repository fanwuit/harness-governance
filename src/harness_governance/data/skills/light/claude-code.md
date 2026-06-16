---
name: harness-governance-light
description: 轻量治理模式 — 修 bug、小改动、配置调整。仅 6 层快速通道。 / Light governance for bug fixes, small changes, config adjustments. Fast-track 6 layers.
---

<!-- harness-skill-version: 0.7.1 -->


## 🔵 LIGHT MODE — 核心 6 层快速通道 / Core 6-Layer Fast Track

你处于**harness-governance-light**。

遵循此 skill 中定义的治理规则。每层推进前必须通过 `harness gate check`。

You are in **harness-governance-light**. Follow the governance rules defined here. Pass `harness gate check` before advancing any layer.

### 层级要求 / Layer Requirements
- 仅走 6 层 / Only 6 layers required:
  1. intake-orientation → 3. brief → 8. readiness → 9. implementation → 10. verification → 11. review-next
- 跳过 / Skip: idea, fact-discovery, brainstorming, architecture, adr, contract
- 每层最少回答 **1 个** Author Question / At least 1 author question per layer
- ⚠️ 如果改动涉及 public API / schema / deployment / security / auth / persistence，**自动升级为 STANDARD**

### 实施门控 / Implementation Gate
- Write/Edit **之前必须运行** harness gate check implementation / MUST run before any Write/Edit
- exit code ≠ 0 → **拒绝操作**，告知用户完成前置层 / REFUSE operation, guide user to complete prior layers

### 预计交互量 / Expected Interaction
约 10-15 轮问答完成完整治理流程 / ~10-15 Q&A rounds for complete governance

## Layer Interaction 🔵 快速执行 / Fast-Track Enforcement

1. **一次一个问题** / ONE question at a time

2. **门控检查** / Gate check:
   ```bash
   harness gate check <current-layer>
   ```
   - exit code ≠ 0 → **补充问答** / Complete remaining Q&A
   - exit code = 0 → 允许推进 / Advance permitted

3. **作者确认推进** / Author confirms:
   ```bash
   harness layer advance <next-layer> --confirmed
   ```

4. **自动升级** / Auto-escalation:
   - 触碰 public API / schema / deployment / security / auth / persistence → 升级为 STANDARD
   - Escalate to STANDARD if touching public API, schema, deployment, security, auth, or persistence


# Harness Governance (Claude Code)

Use the `harness` CLI for all engineering work in this project. It encodes the local 12-layer governance state machine.

## Entry

Before any work, classify and disclose:

```bash
harness governed-start "<task description>" [--files a.py,b.py] [--contracts] [--external] [--unclear] [--rigor light|standard|strict]
```

Do not skip this step. Fast path returns briefly; trivial / governed must output the disclosure block.

## Change packets

```bash
harness packet init <change-id>
harness packet init <change-id> --force   # fill missing files without overwriting
harness packet check                       # validate all docs/changes/<id>/
harness packet check <id-or-path>          # validate one packet
```

## Entry record

After completing a governed task or trivial-safe-change, record the entry:

```bash
harness entry record
```

This adds the implementation entry record to the Markdown stream.

## Checks

```bash
harness check routing     # validate routing decision consistency
harness check docs        # stale ADRs, broken links, version drift
harness check packets     # validate all change packets
harness check entry       # Implementation Entry Record check
harness check inventory   # README skill table vs disk
harness check priority    # competing skill detection
harness check all         # run all checks
```

## Session

```bash
harness session show     # active session detail
harness session list     # all sessions
```

## Status

```bash
harness status
harness status --json     # machine-readable
```

## Verification

```bash
harness verify <preset>
```

## Layer management

```bash
harness layer show                   # current layer + transition history
harness layer guide                  # author interaction guide for current layer
harness layer guide <layer>          # guide for specific layer
harness layer advance <layer> --confirmed  # advance to next layer (after gate check)
```

## Gate checks

```bash
harness gate check <layer>           # verify layer gate (exit 0=pass, 1=fail)
harness gate status                  # show lock-file status for all layers
harness gate status <layer>          # show lock-file status for one layer
harness gate timing                  # per-layer wall-clock timing analysis
harness gate reset <layer> --confirmed  # reset a gate lock
```

## Monitor

Use `/harness-governance-monitor` for project health checks (doc drift, timing, status).

```bash
harness check docs --self    # harness self-documentation checks
harness gate timing --all    # all sessions timing
```

## Review

```bash
harness review close <change-id>
```

## Config

```bash
harness config init
```

## Runner

```bash
harness runner start
```

## Subagent Dispatch

When dispatching subagents for governed work, follow these rules:

1. **Pre-render, don't compose**: Use `harness runner render --role <role>` to generate subagent prompts. Do NOT hand-compose subagent instructions from conversation history.
2. **Forbidden inputs**: Do NOT pass to subagents — conversation history, Q&A from other layers, personal commentary or opinions. Only pass structured, role-specific data.
3. **Why**: Context pollution degrades subagent reasoning accuracy. Long chat histories cause hallucinations, missed constraints, and rule violations.
4. **The subagent is a "clean worker"**: Each subagent starts fresh with only the structured inputs for its role. It is NOT a "conversation continuer" and must not inherit prior context.

子代理分派指南 / Subagent Dispatch Guide:

1. **预渲染，不要拼凑**：使用 `harness runner render --role <role>` 生成子代理提示。不要从对话历史中手工拼凑子代理指令。
2. **禁止传入**：对话历史、其他层的问答、个人评论或意见。只传入结构化的、角色特定的数据。
3. **原因**：上下文污染会降低子代理的推理准确性。过长的聊天历史会导致幻觉、遗漏约束和违反规则。
4. **子代理是"干净的工作者"**：每个子代理以结构化的角色输入为起点。它不是"对话延续者"，不得继承先前的上下文。
