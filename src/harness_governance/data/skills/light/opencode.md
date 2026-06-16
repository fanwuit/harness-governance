---
name: harness-governance-light
description: 轻量治理模式 — 修 bug、小改动、配置调整。仅 6 层快速通道。 / Light governance for bug fixes, small changes, config adjustments. Fast-track 6 layers.
---

<!-- harness-skill-version: 0.7.0 -->


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


# Harness Governance (OpenCode)

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
harness check packets     # validate all change packets
harness check all         # run all checks
```

## Status

```bash
harness status
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
harness gate reset <layer> --confirmed  # reset a gate lock
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
