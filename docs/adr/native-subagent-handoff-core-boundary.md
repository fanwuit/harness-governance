# ADR: Native Subagent Handoff Core Boundary

## Status

Accepted

## Context

Harness governance needs a platform-neutral way to dispatch reviewer, verifier, implementer, and other governed subagent roles. The previous runner design included in-core platform/process executors and an executor registry that could interpret `adapter: subagent` as an external process. That conflicts with the intended native subagent semantics and with the existing capability-tier routing boundary where adapter dispatch/execution is outside the core routing contract.

## Decision

Harness core will use a native handoff lifecycle as the only governed subagent dispatch path.

Harness core will not execute platform agents or subagents. Native spawn is owned by the main agent and the active platform. Harness core owns:

- prompt rendering from structured queue and change packet inputs,
- native handoff request preparation,
- native spawn record ingestion,
- structured result parsing,
- provenance correlation,
- verification gate validation.

Core platform/process agent executors will be removed from governed runner dispatch. Future external process runners, if needed, must live outside core and must not be used as a fallback for governed native subagent dispatch.

## Alternatives Considered

### Keep Subprocess Fallback

Rejected. It preserves the ambiguity where native subagent declarations can be executed as external processes.

### Move Platform Executors To Plugins Now

Deferred. A plugin boundary may be useful later, but this change should first remove the core ambiguity and define native handoff records.

### Keep Codex CLI In Core Under Another Name

Rejected. This keeps platform-specific execution in a platform-neutral core.

## Consequences

- Users of old external worker paths such as `runner start --executor subprocess` or `--executor codex` must migrate.
- Harness core becomes cleaner and platform-neutral.
- Platform-native spawn capability must be provided by the main agent/platform, not by harness CLI.
- Native handoff records and gate semantics become long-lived compatibility surfaces.
- A rejected or insufficient native review cannot count as successful verification unless the queue state explicitly records a block or return.

## Validation

- Search confirms core has no `CodexCliExecutor`, `SubprocessAgentExecutor`, or executor registry public runner path.
- CLI tests cover native handoff preparation, native spawn recording, and parse-result correlation.
- Gate tests cover complete handoff lifecycle validation and unacceptable verdict handling.
- Render tests cover reviewer/verifier required field failures.
- Focused pytest suites pass.
