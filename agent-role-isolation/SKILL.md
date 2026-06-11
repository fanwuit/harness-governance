---
name: agent-role-isolation
description: Use when a task involves task decomposition, planning, TDD, test writing, contract writing, implementation, review, verification, or when the user requires separation between planner/tester/implementer/reviewer roles to avoid AI self-confirmation, self-satisfaction, or tests being shaped by the same agent that writes the implementation.
---

## Harness Precondition

应用本 skill 前，先确认 `harness-engineering` 已经完成当前 layer 和本地治理义务判断。若尚未完成，停止本 skill，返回 `harness-engineering`；不要让本 skill 充当入口路由。

# Agent Role Isolation

## Overview

Use this skill to prevent one agent context from planning, testing, implementing, and accepting its own work. The goal is role isolation with durable handoffs, not ceremony.

中文友好：保留必要英文角色名，并在首次出现时给出中文解释。

## Trigger Check

Before coding or changing tests, decide whether the current task touches more than one role:

- `Planner`（规划者）：拆任务、定义目标、非目标、成功标准和风险。
- `Contract/Test Writer`（契约/测试编写者）：先固定可失败的 schema、fixture、probe、test 或 check。
- `Implementer`（实现者）：只实现满足既有契约的最小改动。
- `Reviewer/Verifier`（审查/验证者）：用新上下文或独立 pass 审查 diff、失败路径、验证输出和漏测风险。

If two or more roles are involved, apply this workflow. If the project has stricter local rules, follow the stricter rule.

If a companion workflow already uses subagents, reviewers, or TDD helpers, still apply this workflow when the task matches the trigger. Companion workflows can execute role separation, but they do not replace the local obligation to classify roles, constrain handoffs, and verify independently.

## Hard Rules

- Do not let the same agent context both create acceptance tests and declare final acceptance of the implementation.
- Do not rewrite failing tests just to fit the implementation.
- Do not treat "the tests I just wrote pass" as final verification.
- Do not let an implementer expand scope beyond the planner's explicit success criteria.
- Do not keep role handoffs only in chat when the project has a queue, brief, ADR, fixture, schema, test, or check location.
- Do not skip this skill because another workflow has a similar role split. State how that workflow satisfies this skill's role isolation requirements.

## Workflow

1. Classify the current work.
   - State which roles are required.
   - State the current engineering layer if the project uses layers such as Brief, Contract, Implementation, Verification, or Review / Next.

2. Create a planner handoff before implementation.
   - Include objective, non-goals, owner files or subsystems, success criteria, forbidden shortcuts, verification commands, and stop conditions.
   - Keep it short enough for a fresh agent to execute without chat history.
   - If the handoff must become prompts for multiple fresh workers, parallel subagent audits, a controller, or an integrator, use `execution-prompt-authoring` to produce an auditable prompt pack before execution.
   - When parallel work is proposed, require an execution matrix from `execution-prompt-authoring/references/parallel-execution-matrix.md` before any file-changing work starts.

3. Fix tests or contracts before implementation when behavior is not already covered.
   - Prefer existing test/check style.
   - Include at least one relevant failure path when risk is not trivial.
   - Record whether the test is expected to fail before implementation.

4. Constrain the implementer.
   - Implement only the smallest change needed to satisfy the fixed contract.
   - Treat requests to edit tests as review events: explain why the test is wrong, stale, or over-specified before changing it.

5. Verify independently.
   - Use a fresh command output, independent review pass, or new agent context where available.
   - Review for missing failure paths, scope creep, brittle tests, and mismatch between success criteria and implementation.

6. Record the result.
   - Update the project's queue, known-mistakes file, ADR, fixture, schema, or check registration when the conclusion affects future work.
   - State remaining risk if a truly independent reviewer was not available.

## Minimal Handoff Template

```markdown
Role isolation:
- Planner:
- Contract/Test Writer:
- Implementer:
- Reviewer/Verifier:

Task:
- Objective:
- Non-goals:
- Owner files:
- Success criteria:
- Forbidden shortcuts:
- Verification:
- Stop conditions:
```

## Parallel Role Boundary

- Parallel agents may audit, explore, or design independent tests when owner files do not conflict.
- Shared files, shared contracts, queue/checkpoint state, README, package scripts, and the same source/test file must be serialized.
- The Integrator role must review worker outputs, verification, and owner-file boundaries before merging results.
- Parallel execution is an execution mode only; it does not replace contract, readiness, verification, or Review / Next.

## Completion Bar

Only call the task complete when:

- The required roles were either separated or the reason for not separating them is recorded.
- Contracts/tests were not weakened by the implementer without review.
- Verification uses fresh evidence.
- New process lessons are saved outside chat when they affect future agents.
