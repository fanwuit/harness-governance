---
name: governed-implementation-entry
description: Use when Codex is about to write or modify product code, create a new app/package/service, enter implementation after brief/contract/readiness work, or treat a task as small/simple/obvious while it still changes product behavior.
---

# Governed Implementation Entry

## Harness Precondition

应用本 skill 前，先确认 `harness-engineering` 已经完成当前 layer 和本地治理义务判断。若尚未完成，停止本 skill，返回 `harness-engineering`；不要让本 skill 充当入口路由。

## Overview

Use this as a hard entry gate before product implementation. Smallness is not evidence of safety; only an explicit throwaway-prototype scope can reduce governance, and the exception itself must be recorded.

## Hard Gate

Do not write product implementation code until an Implementation Entry Record exists.

The record must include every field below:

```text
Implementation Entry Record:
- Current layer:
- Target:
- Scope:
- Contract evidence:
- Readiness gate:
- Packetization:
- Verification command:
- Review / Next state file:
- Stop conditions:
```

If any field is missing, vague, or only implied by chat history, stop before implementation and create the missing durable record.

## Required Values

| Field | Required content |
|---|---|
| Current layer | One harness layer, usually `readiness` or `implementation`. |
| Target | Concrete app/package/service/file group being changed. |
| Scope | Minimal behavior allowed in this slice. |
| Contract evidence | Test, fixture, schema, example, probe, or check path. |
| Readiness gate | `pass` or `fail`; if `fail`, implementation is blocked. |
| Packetization | `ready`, `not-needed`, or `missing`. |
| Verification command | Fresh command required before completion claims. |
| Review / Next state file | `NEXT.md` or the project's equivalent persistent state. |
| Stop conditions | Conditions that require stopping instead of expanding scope. |

## Small Task Rule

Small, static, local, single-file, no-dependency, obvious, or demo-like work does not bypass this skill.

Only an explicit user request for a throwaway prototype may reduce the gate. If reduced, record:

- `Prototype exception: yes`
- What is skipped
- Why the skipped step is safe
- What must not be claimed, for example `product-ready`

## Packetization Rule

Choose exactly one:

- `ready`: a self-contained task packet exists with owner files, contracts, allowed assumptions, forbidden shortcuts, stop conditions, verification, and done-when.
- `not-needed`: the task is a single-session, single-target manual slice; record why this is safe.
- `missing`: stop and create the packet before implementation.

Silently skipping packetization is forbidden.

## Review / Next Rule

Before claiming completion, ensure the result is written to `NEXT.md` or the project's equivalent state file.

Record:

- Done evidence
- Verification commands and results
- Blocked items, including browser/tool failures
- Not-now scope
- Next ready layer or next ready task

If no state file exists, create one or record why the project intentionally has no persistent queue yet.

## Reverse Audit

Before any completion claim after code changes, answer:

- Did product behavior change?
- Is there contract evidence?
- Is readiness gate recorded?
- Is packetization recorded?
- Is review-next state updated?
- Are failed or skipped verifications recorded as risk or blocked?

If any answer is no, do not claim completion.

## Mechanical Check

Use `scripts/check-entry-record.mjs <markdown-file>` to check that a Markdown record contains the required Implementation Entry Record fields.

The script is a backstop only. Passing it does not prove the gate is correct; it proves required fields are present and non-empty.

## Red Flags

Stop when thinking:

- "This is too small for gate/packet/NEXT."
- "The user approved the idea, so readiness is enough."
- "The test can stand in for the gate."
- "I can mention NEXT in chat instead of writing it."
- "Packetization is obviously not needed, so I do not need to say so."
- "Browser verification failed, but the tests passed, so no need to record risk."

These are governance failures, not harmless shortcuts.

## Common Mistakes

| Mistake | Correct behavior |
|---|---|
| Treating user approval as readiness. | Record the gate separately. |
| Treating contract tests as readiness gate. | Keep contract evidence and readiness decision distinct. |
| Treating small work as an exception. | Use the same entry record; choose `Packetization: not-needed` only with a reason. |
| Leaving final state in chat. | Update `NEXT.md` or the project state file. |
| Claiming done after partial verification. | Record skipped/failed verification as risk or blocked. |
