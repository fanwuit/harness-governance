# Brainstorming: Review Close State Linkage

## Option A: Close Matching Session In `review close`

- Best when: `harness review close <task-id>` is the canonical closeout command.
- Benefit: Keeps the existing user command and extends it to close the same-id session.
- Cost: Small dependency from review command to session store.
- Risk: Closing anything other than an exact session id could close the wrong work.
- Evidence needed: CLI test proving checkpoint, queue, and session all close from one command.

## Option B: Add A Separate State Sync Command

- Best when: drift repair is the primary use case.
- Benefit: Could batch-fix old queue/session/checkpoint divergence.
- Cost: Users still need to remember a second command after normal closeout.
- Risk: It does not solve future drift at the source.
- Evidence needed: sync command tests for multiple stale states.

## Option C: Rewrite Closeout Around A Service

- Best when: multiple closeout commands need shared transaction-like behavior.
- Benefit: Clearer long-term ownership for checkpoint, queue, and session writes.
- Cost: Larger blast radius across CLI modules and tests.
- Risk: Unnecessary refactor for the observed bug.
- Evidence needed: broader regression coverage across review, session, status, and runner commands.

## Recommendation

Choose Option A.

The queue linkage already exists in `review_close_cmd`, so the smallest durable fix is to add exact session closure to the same command. Missing sessions and missing queue items should remain non-fatal so checkpoint-only usage keeps working.

## Non-Goals

- Do not fuzzy-match session ids from titles.
- Do not make `NEXT.md` mandatory for `review close`.
- Do not rewrite queue parsing or status rendering.
- Do not add a new state sync command in this slice.

## Next Layer Candidate

Brief, then architecture/contract for the exact CLI behavior.
