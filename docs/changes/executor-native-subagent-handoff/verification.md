# Verification

## Verification Commands

- `pytest tests/test_native_subagent_handoff.py -q`
- `pytest tests/test_commands/test_runner_cmd.py tests/test_subagent_runner/test_cli_integration.py -q`
- `pytest -q`
- `harness check all`

## User-Perceived Integration Not Applicable

- Reason: CLI/backend governance protocol change with no browser or product UI state.
- Replacement verification: full pytest, targeted runner/native handoff tests, and native reviewer-verifier lifecycle review.
- Residual risk: Low; actual platform-native spawn is intentionally outside harness core and is recorded through `record-native-spawn`.

## Results

- pytest tests/test_native_subagent_handoff.py -q
- passed: native handoff tests passed.
- pytest tests/test_commands/test_runner_cmd.py tests/test_subagent_runner/test_cli_integration.py -q
- passed: runner and subagent CLI integration tests passed.
- pytest -q
- passed: full suite passed after native role correlation fixes.
- passed: `harness check all` passed after packet schema completion.

## Reviewer Result

The first native reviewer-verifier result was `reject`; blocking issues were recorded in `.harness/native-handoffs/20260622-executor-native-subagent-handoff.ndjson` and addressed by:

- enforcing completion role/request/spawn correlation;
- allowing `parse-result --role reviewer-verifier`;
- completing this change packet so `harness check all` can validate it.

## Subagent Separation

- Required: no
- Waiver: Full four-role subagent separation was not available for this continuation; an independent native reviewer-verifier was spawned and recorded instead.
- Replacement Verification: Native reviewer-verifier invocation `019eeec0-3faf-7771-8817-57f659b0ad1f` produced a structured `reject` result and was recorded with `record-native-spawn` and `parse-result`; full pytest and targeted native handoff tests validate the follow-up fixes.
- Residual Risk: Low after follow-up fixes; actual platform-native spawn remains outside harness core by design.
