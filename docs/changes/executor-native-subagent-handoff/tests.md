# Tests

## Test Owner

- Test Owner: native reviewer-verifier invocation `019eeec0-3faf-7771-8817-57f659b0ad1f`.

## Test Types

- Unit: applicable
- Integration: applicable
- E2E: not applicable

## Test Files

- Path: tests/test_native_subagent_handoff.py
- Path: tests/test_commands/test_runner_cmd.py
- Path: tests/test_subagent_runner/test_cli_integration.py
- Path: tests/test_state_machine/test_capability_routing.py
- Path: tests/test_state_machine/test_skill_chain.py

## Red Green Evidence

- Expected failing command before product implementation: `pytest tests/test_native_subagent_handoff.py -q` before native handoff lifecycle support and role correlation checks.
- Green command: `pytest tests/test_native_subagent_handoff.py -q`

## Commands

- `pytest tests/test_native_subagent_handoff.py -q`
- `pytest tests/test_commands/test_runner_cmd.py tests/test_subagent_runner/test_cli_integration.py -q`
- `pytest -q`

## Coverage

- `prepare-native` writes request and prompt artifacts.
- `adapter=subprocess` is rejected for native handoff.
- Native spawn and parse completion correlate by request, agent id, and role.
- `parse-result --role reviewer` cannot complete a `reviewer-verifier` request.
- Verification gate requires render, prepare, spawn, parse completion, and acceptable verdict.
- Old process executors are no longer accepted by `runner start`.
