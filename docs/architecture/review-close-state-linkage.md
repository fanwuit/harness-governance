# Architecture: Review Close State Linkage

## Boundaries

`harness review close` remains the closeout orchestrator. It coordinates three local persistence surfaces:

- Checkpoint state in `.harness/run-checkpoint.md`.
- Queue state in `NEXT.md`.
- Governance session state in `.harness/sessions/<session-id>.json`.

## Component Responsibilities

- `commands/review.py`: owns the closeout command flow and reports command success.
- `file_ops/checkpoint.py`: owns checkpoint load/dump behavior.
- `file_ops/queue.py`: owns queue block matching and `[done]` rendering.
- `session/store.py`: owns loading and saving session state.
- `commands/session_cmd.py`: remains the explicit manual session CLI, not the shared implementation owner.

## Ownership Assignments

- Review command behavior: `src/harness_governance/commands/review.py`.
- Queue mutation contract: `src/harness_governance/file_ops/queue.py`.
- Session persistence contract: `src/harness_governance/session/store.py`.
- CLI regression tests: `tests/test_commands/test_verify_review_config.py`.

## Data Flow

1. User runs `harness review close <task-id>`.
2. The command writes checkpoint verification and stop reason.
3. The command marks the matching `NEXT.md` block `[done]` if one exists.
4. The command attempts to load a session whose id exactly equals `<task-id>`.
5. If that session exists and is active, the command marks it closed.
6. Missing queue item or missing session is a no-op; checkpoint closeout still succeeds.

## ADR Candidates

No formal ADR is required for this slice. The change does not introduce a new external API, storage schema, deployment boundary, or ownership model. It tightens the existing closeout command around the existing local state surfaces.
