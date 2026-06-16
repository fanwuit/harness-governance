---
name: harness-governance-strict
description: 严格治理模式 — 大型平台、系统重构、从零构建。全部 12 层强制执行。 / Strict governance for large platforms, system rewrites, build-from-scratch. All 12 layers enforced.
---

<!-- harness-skill-version: 0.7.0 -->


## ⛔ STRICT MODE — 全 12 层强制执行 / All 12 Layers Enforced

你处于**harness-governance-strict**。

遵循此 skill 中定义的治理规则。每层推进前必须通过 `harness gate check`。

You are in **harness-governance-strict**. Follow the governance rules defined here. Pass `harness gate check` before advancing any layer.

### 层级要求 / Layer Requirements
- 全部 12 层必须按顺序走完，**不可跳过任何层** / All 12 layers required in order, no skipping
- Fact Discovery 在发现任何实质性未知时**强制中断**当前层 / Fact Discovery interrupts on any material unknown
- 每层**所有** Author Questions 必须逐一问完并记录答案到 session / ALL author questions asked and recorded
- 每层产出物必须写入持久化文件（不可仅存于聊天中）/ All artifacts written to durable files
- **禁止**合并层级（如 brainstorming+brief 合并讨论）/ Merging layers is FORBIDDEN

### 实施门控 / Implementation Gate
- Write/Edit **之前必须运行** harness gate check implementation / MUST run before any Write/Edit
- exit code ≠ 0 → **拒绝操作**，告知用户完成前置层 / REFUSE operation, guide user to complete prior layers

### 预计交互量 / Expected Interaction
约 40-50 轮问答完成完整治理流程 / ~40-50 Q&A rounds for complete governance

## Layer Interaction ⛔ 强制执行 / Mandatory Enforcement

Advancing each layer MUST follow this workflow. Any skipped step = governance failure.
每层推进必须严格遵守以下流程。违反任一步骤 = 治理失败。

1. **阅读交互指南** / Read author interaction guide:
   ```bash
   harness layer guide          # 当前层 / current layer
   harness layer guide <layer>  # 指定层 / specific layer
   ```

2. **一次只问一个问题** / ONE question at a time:
   - 逐个提问，等待作者回答后再提下一个 / Ask individually, wait for author answer before asking next
   - **禁止**一次性列出多个问题 / Presenting multiple questions at once is FORBIDDEN

3. **门控检查**（前置条件）/ Gate check (precondition):
   ```bash
   harness gate check <current-layer>
   ```
   - exit code ≠ 0 → **拒绝推进**，继续问答直到所有要求满足 / REFUSE advance, continue Q&A until all met
   - exit code = 0 → 锁文件自动写入，允许推进 / Lock file auto-written, advance permitted

4. **作者确认推进** / Author must explicitly confirm:
   ```bash
   harness layer advance <next-layer> --confirmed
   ```
   - 作者未确认 → **禁止推进** / DO NOT advance without explicit author confirmation

5. **严格顺序推进** / Strict sequential advancement:
   - 必须按 1→2→3→...→12 顺序推进 / Must advance through layers in order
   - 任何跳层、合并层都会被引擎阻止 / Skip/merge attempts will be blocked by the engine


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
