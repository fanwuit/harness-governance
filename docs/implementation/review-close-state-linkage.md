# Implementation Entry Record: Review Close State Linkage

## Target

`harness review close <task-id>` automatic linkage across checkpoint, queue, and same-id session state.

## Scope

- `src/harness_governance/commands/review.py`
- `tests/test_commands/test_verify_review_config.py`
- Governance docs for this task

## Contract Evidence

- `docs/contracts/review-close-state-linkage.md`
- `tests/test_commands/test_verify_review_config.py`

## Readiness State

Readiness passed. Contract tests were written first; the new positive session-linkage test initially failed because the implementation did not close the matching session yet.

## Packetization

Single small CLI behavior change. No change packet directory is required for this scoped repository-local fix.

## Verification Commands

- `python -m pytest tests/test_commands/test_verify_review_config.py -q`
- `python -m py_compile src/harness_governance/commands/review.py`

## Fresh Verification

- `python -m pytest tests/test_commands/test_verify_review_config.py -q` passed: 12 tests.
- `python -m py_compile src/harness_governance/commands/review.py` passed.

## Review / Next State File

- `NEXT.md`
- `.harness/run-checkpoint.md`

## Stop Conditions

- Stop if closing a session requires fuzzy matching.
- Stop if checkpoint-only `review close` usage would become an error.
- Stop if queue parser semantics must change.

## Approved Owner Files

- `src/harness_governance/commands/review.py`
- `tests/test_commands/test_verify_review_config.py`
- `docs/facts/review-close-state-linkage.md`
- `docs/brainstorming/review-close-state-linkage.md`
- `docs/briefs/review-close-state-linkage.md`
- `docs/architecture/review-close-state-linkage.md`
- `docs/adr/review-close-state-linkage.md`
- `docs/contracts/review-close-state-linkage.md`
- `docs/implementation/review-close-state-linkage.md`
