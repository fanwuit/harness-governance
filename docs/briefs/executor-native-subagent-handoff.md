# Brief: Executor Removal and Native Subagent Handoff

## Goal

Harness core no longer embeds or executes platform/process agent executors. The runner should prepare, record, parse, and gate platform-native subagent handoff lifecycle records, and the old `subprocess` and `codex-cli` public runner execution paths should be removed from core.

## Context

This continues prior capability-tier/subagent routing work. The current implementation still exposes in-core execution abstractions and platform/process runners, which can collapse native subagent semantics into external process execution.

## Non-Goals

- Do not keep old `subprocess` or `codex-cli` runner compatibility mode.
- Do not add any new platform CLI executor to core.
- Do not implement plugin-based platform executors in this change.
- Do not remove unrelated `subprocess` usage for git/status/verification helpers.

## Options Considered

- Remove core executors and build native handoff.
- Keep subprocess as a compatibility fallback.
- Move platform executors to plugins.

## Decision / Direction

Use native handoff as the only governed subagent dispatch path in core. Remove core executor registry and platform/process agent execution from the public runner path. Defer any plugin-based external runner story until there is a separate, explicit need.

## Risks / Unknowns

- Breaking change for users of `harness runner start --executor subprocess` or `--executor codex`.
- Existing tests and docs currently encode old executor semantics and must be updated.
- Gate logic must avoid treating a rejected native review as a passing verification chain.

## Success Criteria

- Core has no `CodexCliExecutor`, `SubprocessAgentExecutor`, or executor registry in the public runner path.
- `adapter=subagent` produces only a native handoff request or plan, never subprocess execution.
- Runner commands can prepare handoff requests, record native spawn events, and parse native results into correlated records.
- Verification gate checks the complete native handoff chain and rejects `reject` or `insufficient_evidence` results unless the queue is explicitly blocked or returned.
- Reviewer/verifier render or prepare fails when required prompt fields are missing.
- Focused runner, handoff, parser, gate, and documentation tests are updated and pass.

## Next Layer

Architecture.
