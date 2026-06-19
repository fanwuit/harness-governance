# Verification: State Contract P1 Enhancements

## Results
- Focused pytest suite passed for the new check adapter, check-all integration,
  verification gate hook, init scaffold, and existing state-contract command.
- `harness check state-contract` passed against this repository.

## Evidence
- Test command: `pytest tests/test_commands/test_check_cmd.py tests/test_commands/test_init.py tests/test_state_machine/test_gates.py tests/test_commands/test_state_contract_cmd.py -q`
- Governance command: `harness check state-contract`

## User-Perceived Integration Not Applicable
- Reason: This change affects CLI governance checks, verification gates, and generated project scaffolding; it has no product UI path.
- Replacement verification: pytest tests/test_commands/test_check_cmd.py tests/test_commands/test_init.py tests/test_state_machine/test_gates.py tests/test_commands/test_state_contract_cmd.py -q
- Residual risk: The first version still uses the explicit state-contract requirement list rather than automatic writer/consumer scanning.

## Unit Evidence
- Command: pytest tests/test_commands/test_check_cmd.py tests/test_commands/test_init.py tests/test_state_machine/test_gates.py tests/test_commands/test_state_contract_cmd.py -q
- Behaviour under test: state-contract check adapter, check-all integration, verification gate hook, init scaffold creation, and existing state-contract CLI.
- Boundary/negative cases: missing state-contract evidence fails, check-all reports state-contract findings, verification gate blocks missing evidence, and init --minimal skips the scaffold.
- Mock boundary: No mocks; tests use temporary project roots and real filesystem evidence.
- Why mocks do not hide product risk: The behavior under test is filesystem-backed CLI/gate behavior.

## Integration Evidence
- Command: pytest tests/test_commands/test_check_cmd.py tests/test_commands/test_init.py tests/test_state_machine/test_gates.py tests/test_commands/test_state_contract_cmd.py -q
- Real modules crossed: commands/state_contract.py, commands/check.py, state_machine/gates.py, commands/init.py, CLI registration.
- Writer: harness init writes tests/test_state_contract_scaffold.py; tests write state-contract evidence files.
- Consumer: harness check state-contract, harness check all, and LayerGateEngine verification hook.
- Persisted/readback state: temporary repository files are written, checked, and read back by the CLI/gate code.
- External systems mocked: none.
- Why acceptable: The change has no external service dependency.

## Subagent Separation
- Required: no
- Waiver: This scoped repository-local change was implemented in one context after governed-path gating; no external acceptance contract or product release is being closed.
- Replacement Verification: Focused pytest coverage plus verification evidence in this file.
- Residual Risk: Independent verifier separation is not exercised for this small CLI enhancement.
