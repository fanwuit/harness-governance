# Brief: Review Close State Linkage

## Goal

`harness review close <session-id>` should close the task in all local state surfaces that can be matched safely: checkpoint, `NEXT.md`, and the same-id session file.

## Non-Goals

- No fuzzy session matching.
- No new state sync command.
- No requirement that `NEXT.md` exists.
- No rewrite of status, runner, or queue parsing.

## Options Considered

- Add exact session close to `review close`.
- Add a separate state sync command.
- Rewrite closeout around a shared service.

## Decision / Direction

Add exact session closure to `review_close_cmd` after checkpoint and queue updates. Missing sessions should be ignored, matching existing queue no-op behavior.

## Risks / Unknowns

- Risk: fuzzy matching could close the wrong session. Mitigation: exact `task_id == session_id` only.
- Risk: failing when no session exists could break checkpoint-only review close usage. Mitigation: missing session is a no-op.

## Success Criteria

- `harness review close <session-id>` writes checkpoint evidence and risk lines.
- Matching `NEXT.md` item is marked `[done]` and gets `Closed` / `Evidence` / `Risk` lines.
- Matching active session is marked `closed` with `closed_at`.
- Missing session does not fail the command.

## Next Layer

Architecture.
