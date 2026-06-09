---
name: contract-growth-control
description: Use when a project using contract-first, harness engineering, ADR/schema/example/check workflows, or autonomous agents risks over-contracting; decide whether to add another contract artifact, move to implementation, mark blocked, or ask for human confirmation.
---

## Harness Precondition

应用本 skill 前，先确认 `harness-engineering` 已经完成当前 layer 和本地治理义务判断。若尚未完成，停止本 skill，返回 `harness-engineering`；不要让本 skill 充当入口路由。

# Contract Growth Control

## Purpose

Prevent contract-first work from turning into endless governance. Use this skill before adding ADRs, schemas, examples, fixtures, probes, check scripts, wrappers, readiness gates, or other contract artifacts when implementation is lagging behind.

## Decision Rule

Default to implementation once enough contract and readiness evidence exists.

Before adding a contract artifact, answer:

```text
Implementation unlock: <the next smallest implementation file, command, behavior, or target-local slice this contract enables>
Why existing evidence is insufficient: <specific missing assertion or failure path>
Reuse check: <why an existing contract/check cannot be extended instead>
```

If any answer is vague, do not add the contract. Choose implementation, blocked, or human confirmation.

## Continuous Contract Limit

For one product line or focus:

- Allow at most 2 consecutive contract/check tasks.
- The 3rd task must be one of:
  - smallest implementation slice,
  - explicit blocked record,
  - human confirmation to continue contract work.

Do not reset the count by renaming the same line as ADR, readiness, schema, example, or governance.

## No-Ready Selection

When the project queue has no ready item:

1. If contracts plus target-local readiness already cover a next step, select the smallest implementation slice.
2. If implementation would cross a product gate, mark blocked.
3. Add a new contract only when it names a concrete Implementation unlock and cannot reuse existing artifacts.

## Contract Growth Justification

When a new contract artifact is still necessary, write a durable justification in the project’s normal status location, such as `NEXT.md`, an ADR, a brief, or a readiness gate.

Include:

- `Next minimum product slice`
- `Implementation unlock`
- `Why existing contracts or checks are insufficient`
- `New artifact names`
- `Verification command`
- `Product scope that remains forbidden`

## Mechanical Guard

If the project has check scripts, add or update one to enforce the local rule. At minimum it should fail when new schema/example/check artifacts are added without the justification fields above.

If detecting consecutive contract tasks is too project-specific, document the rule in the queue and require the next selection record to state whether the limit has been reached.

## Output

When reporting, state:

- whether contract growth is allowed,
- the implementation slice it unlocks,
- whether the consecutive contract limit is reached,
- whether you selected implementation, blocked, or human confirmation,
- what verification ran.
