# Contract: Review Close State Linkage

## Field Specifications

| Field | Type | Required | Notes |
|---|---|---|---|
| task_id | str | yes | CLI argument passed to `harness review close`; also the exact session id used for automatic session closure. |

## C1: Same-Id Session Closes

The system MUST mark `.harness/sessions/<task-id>.json` as closed when `harness review close <task-id>` succeeds and that session exists.

Verified by: CLI test reads the session file after `review close` and asserts `status == "closed"` and `closed_at` is set.

## C2: Queue Closure Remains Intact

The system MUST keep existing queue closure behavior: a matching `NEXT.md` item is marked `[done]` and receives `Closed`, `Evidence`, and `Risk` lines.

Verified by: existing queue closure test continues to pass.

## C3: Checkpoint Closure Remains Intact

The system MUST keep existing checkpoint behavior: evidence, risk, stop reason, and next resume source are written to `.harness/run-checkpoint.md`.

Verified by: existing checkpoint test continues to pass.

## C4: Missing Session Is Non-Fatal

The system MUST NOT fail `harness review close <task-id>` when no matching session file exists.

Verified by: CLI test runs `review close` without a matching session and asserts exit code `0`.

## C5: No Fuzzy Session Closure

The system MUST NOT close sessions whose id does not exactly equal `<task-id>`.

Verified by: same missing-session test may include an unrelated active session and assert it remains active.
