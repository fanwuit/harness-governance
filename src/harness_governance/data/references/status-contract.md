# Harness Status Contract

## Purpose

This reference is the shared source of truth for harness status display. `harness-visualization` owns the default implementation; `harness-status-dashboard` owns interpretation and diagnosis. Runners and README should reference this contract instead of duplicating field lists.

## Required Status Fields

A status view should surface these fields when the corresponding source exists:

- Current layer: inferred from the active or first ready scheduler item.
- Current ready: scheduler item title, target, contract, evidence, and packetization when present.
- Scheduler queue: current `[ready]` and short-lived `[active]` items.
- Legacy queue records: stale `[done]`, `[blocked]`, not-now, or non-scheduler records preserved with migration warnings.
- Done archive: archived change packets or equivalent done-history location.
- Task packet progress: active task packet path, done/total count, and checklist items.
- Runner state: latest marker, round, exit code, checkpoint result, stdout/stderr path, and stop reason.
- Verification: latest verification summary plus missing, failed, or stale warnings.
- Human-needed blockers: missing materials, credentials, permissions, stage choice, or port blocker details.
- Status outputs: human-readable Markdown path and machine-readable JSON path when written.

## CLI / Conversation Compact Panel

When starting a runner, refreshing status, handling blocked/boundary/no-ready markers, or answering progress questions, show a compact panel directly in CLI/conversation. Do not only provide `.harness/status.md` or `.harness/status.json` paths.

The compact panel must include at least:

- Current layer.
- Current ready.
- Ready queue count.
- Runner marker and round.
- Checkpoint result.
- Verification stale/failed signal.
- Human-needed blocker.
- Status file path.

If the blocker is a port conflict, include port, PID, process name, and command line when available.

## Task Packet Checklist Rule

`Current ready` is the scheduling item. If it points to a task packet, change packet, or equivalent task package, the panel and Markdown status must show:

- Task packet path.
- Task progress as done/total.
- Each `## Task checklist` item with its `- [ ]` or `- [x]` state.

Do not collapse task packets into a single ready-level pass/fail. If a ready item references a packet but the packet has no checklist, show a visible warning and ask for a `Task checklist`.

## Boundaries

- Status views are read-only visibility. They do not mutate scheduler queue, done archive, contracts, or product code.
- Dashboard diagnosis is not a gate. Gate failures remain owned by readiness, contract, verification, and review-next skills.
- Business projects should provide standard sources: scheduler queue, done archive, checkpoint, invocation log, change packet, and optional config.
- Business projects should not copy visualization parsing logic; they should consume the shared script output or JSON contract.
- TUI/Web consoles should consume the JSON status after this contract is stable; they are not part of the default status implementation.
