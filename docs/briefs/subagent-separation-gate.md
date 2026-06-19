# Subagent Separation Gate Brief

## Goal

Implement the first document-level version of `harness check subagent-separation`.
The check validates that high-risk, P0/P1, or real-user-closure changes declare a
role matrix, independent invocation evidence, file ownership boundaries, and
closure authority. It must be included in `harness check all` and `harness ship`.

## Non-Goals

- Do not automatically start subagents.
- Do not refactor runner orchestration.
- Do not introduce new dependencies.
- Do not implement AST-level or git-diff-level ownership checks.
- Do not complete all readiness / verification / review-next gate hooks in this first version.

## Options Considered

- Document-level Markdown gate.
- Deep invocation provenance gate.
- Automatic subagent dispatch.

## Decision / Direction

Use the document-level Markdown gate for the P0 first version. This matches the
existing `user-evidence` check style and keeps the first version focused on
evidence validation rather than dispatch orchestration.

## Risks / Unknowns

- Markdown text triggers can produce false positives.
- Invocation logs may not yet include all ownership fields needed for richer enforcement.
- File ownership checks will initially be text-level declarations, not diff-level proof.

## Success Criteria

- `harness check subagent-separation` exists and returns a standard `CheckResult`.
- Triggering documents fail when they omit `## Subagent Separation`.
- `Required: yes` fails when role fields or independent invocation evidence are missing.
- `Required: no` fails when waiver details are missing.
- Obvious file ownership and closure authority violations fail.
- `harness check all` includes `subagent-separation`.
- `harness ship` includes `subagent-separation`.
- Focused pytest coverage exists.

## Next Layer

Architecture.

