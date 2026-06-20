# Verification: User-Evidence Artifact Scanning

## Verification Commands

```
pytest tests/test_commands/test_evidence_scanner.py -v
pytest tests/test_commands/test_check_cmd.py -v
ruff check src/harness_governance/commands/evidence_scanner.py src/harness_governance/commands/check.py tests/test_commands/test_evidence_scanner.py
mypy src/harness_governance/commands/evidence_scanner.py
```

## Results

- `pytest tests/test_commands/test_evidence_scanner.py`: 10 passed
- `pytest tests/test_commands/test_check_cmd.py`: 30 passed (no regression)
- `ruff check`: All checks passed
- `mypy`: Success, no issues found

## Evidence

Evidence covers scanner unit tests, user-evidence check regression tests,
linting, type checking, and contract-to-test mapping for C1-C8 below.

## Contract Coverage

| Contract | Test | Status |
|---|---|---|
| C1: No-artifact no-op | test_no_artifacts_no_findings | PASS |
| C2: HAR empty payload | test_har_empty_post_data | PASS |
| C3: HAR mock response | test_har_mock_response | PASS |
| C4: Trace forbidden selector | test_trace_forbidden_selector | PASS |
| C5: Trace non-user nav | test_trace_non_user_first_nav | PASS |
| C6: Test source forbidden selector | test_test_source_forbidden_selector | PASS |
| C7: Malformed graceful skip | test_malformed_artifacts_graceful, test_empty_trace_graceful | PASS |
| C8: Doc-level unchanged | test_scan_does_not_raise_on_clean_repo, existing test_check_cmd.py | PASS |

## Additional Tests

- `test_har_valid_payload_no_finding`: HAR with valid payload produces no false positive — PASS

## User-Perceived Integration Not Applicable
- Reason: This change enhances an internal CLI check (`harness check user-evidence`) for a governance tool. It has no user-visible UI, no save/publish/login flow, and no external state. The users are developers running CLI commands.
- Replacement verification: pytest + ruff + mypy on the scanner module and integration tests
- Residual risk: Low — scanner is additive and graceful; no regression on existing checks
