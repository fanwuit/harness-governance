# Verification: Review Close State Linkage

## Evidence

- Command: `python -m pytest tests/test_commands/test_verify_review_config.py -q`
- Result: passed, 12 tests
- Command: `python -m py_compile src/harness_governance/commands/review.py`
- Result: passed

## User-Perceived Integration Evidence

- Evidence level: contract
- Real User Entry: `harness review close <task-id>`
- User-Visible State: `harness status` and `harness session list` no longer show the same-id completed task as active after review close.
- Persistence/External State: `.harness/sessions/<task-id>.json` has `status: closed` and non-empty `closed_at`; `NEXT.md` matching block is `[done]`; `.harness/run-checkpoint.md` records closeout.
- Anti-Self-Proof Assertion: The positive test failed before implementation because the session remained `active`; after implementation it passes by reading persisted state.
- Forbidden Test Shortcuts: none
- Command: `python -m pytest tests/test_commands/test_verify_review_config.py -q`
- Result: passed, 12 tests, 2026-06-20

## Unit Evidence

- `test_review_close_closes_matching_session_and_queue` covers checkpoint command execution, matching queue closure, and same-id session closure.
- `test_review_close_missing_session_is_non_fatal` covers missing exact session no-op and no fuzzy closure of an unrelated session.

## Integration Evidence

- Writer: `harness review close <task-id>` writes checkpoint, queue closure, and matching session closure.
- Consumer: `harness status`, `harness session list`, runner queue readers, and future agents consume those state files.

## Subagent Separation

- Required: no
- Reason: This was a small local CLI closeout consistency fix implemented in the main context after strict governance gates; no separate subagent handoff was used.
- Alternative Verification: Contract tests exercise the public CLI and persisted readback.
- Residual Risk: Broader release verification is deferred; this slice only proves the review close state linkage path.
