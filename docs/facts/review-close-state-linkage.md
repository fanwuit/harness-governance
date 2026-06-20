# Facts: Review Close State Linkage

## Observed Facts

- `src/harness_governance/commands/review.py` implements `harness review close`.
- `review_close_cmd` writes `.harness/run-checkpoint.md` through `Checkpoint`.
- `review_close_cmd` already calls `mark_queue_item_done(config.queue_file, task_id=task_id, evidence=evidence, risks=risks)`.
- `src/harness_governance/file_ops/queue.py` marks the first matching `[active]` or `[ready]` queue block as `[done]`.
- Queue matching accepts `Session: <task_id>`, `Change: <task_id>`, or a first-line title containing `<task_id>`.
- `src/harness_governance/commands/session_cmd.py` implements `harness session close <session_id>` by setting `status` to `closed` and `closed_at` to the current UTC time.
- `tests/test_commands/test_verify_review_config.py` already covers checkpoint writes and queue closure from `harness review close`.

## Unknowns And Assumptions

Assumption: `harness review close <task-id>` should close a session only when `<task-id>` exactly matches an existing session id.
Risk: broader fuzzy matching could close the wrong active session when task titles and session ids diverge.

Assumption: missing `NEXT.md` or missing session is not an error for `review close`.
Risk: making either required would break existing checkpoint-only usage.

Assumption: current queue linkage should remain unchanged and the new work should add session linkage.
Risk: rewriting queue parsing would broaden blast radius without addressing the observed drift.
