---
name: harness-governance-standard
description: 标准治理模式 — 日常功能开发、中等复杂度改动。12 层可用，允许适度合并。 / Standard governance for daily feature development, moderate complexity. 12 layers with flexibility.
---

<!-- harness-skill-version: 0.7.0 -->


## 🟡 STANDARD MODE — 全 12 层标准治理 / All 12 Layers Standard Governance

你处于**harness-governance-standard**。

遵循此 skill 中定义的治理规则。每层推进前必须通过 `harness gate check`。

You are in **harness-governance-standard**. Follow the governance rules defined here. Pass `harness gate check` before advancing any layer.

### 层级要求 / Layer Requirements
- 全部 12 层可用，逐层推进 / All 12 layers available, advance in order
- brainstorming 可与 brief 合并讨论 / brainstorming can merge with brief
- 每层最少回答 **半数** Author Questions / At least half of author questions per layer
- Fact Discovery 按需触发 / Fact Discovery triggered as needed

### 实施门控 / Implementation Gate
- Write/Edit **之前必须运行** harness gate check implementation / MUST run before any Write/Edit
- exit code ≠ 0 → **拒绝操作**，告知用户完成前置层 / REFUSE operation, guide user to complete prior layers

### 预计交互量 / Expected Interaction
约 20-30 轮问答完成完整治理流程 / ~20-30 Q&A rounds for complete governance

## Layer Interaction 🟡 标准执行 / Standard Enforcement

1. **阅读交互指南** / Read author interaction guide:
   ```bash
   harness layer guide          # 当前层 / current layer
   harness layer guide <layer>  # 指定层 / specific layer
   ```

2. **一次一个问题** / ONE question at a time:
   - 逐个提问，等待回答后继续 / Ask individually, wait for answer before continuing

3. **门控检查**（前置条件）/ Gate check (precondition):
   ```bash
   harness gate check <current-layer>
   ```
   - exit code ≠ 0 → **补充问答** / Complete remaining Q&A
   - exit code = 0 → 允许推进 / Advance permitted

4. **作者确认推进** / Author confirms:
   ```bash
   harness layer advance <next-layer> --confirmed
   ```

5. **允许合并** / Allowed: brainstorming 和 brief 可以合并讨论 / brainstorming+brief may merge


# Harness Governance (QoderWork)

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
