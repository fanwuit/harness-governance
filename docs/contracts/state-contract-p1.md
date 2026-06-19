# Contract: State Contract P1 Enhancements

## Behaviour
- The system MUST expose `harness check state-contract`.
  Verified by `pytest tests/test_commands/test_check_cmd.py`.
- The system MUST include state-contract evidence in `harness check all`.
  Verified by `pytest tests/test_commands/test_check_cmd.py`.
- The verification gate MUST fail when state-contract evidence is missing.
  Verified by `pytest tests/test_state_machine/test_gates.py` or an equivalent
  focused gate test.
- `harness init` MUST create a downstream state-contract scaffold test when
  not running with `--minimal`.
  Verified by `pytest tests/test_commands/test_init.py`.
- `harness init --minimal` MUST NOT create the scaffold.
  Verified by `pytest tests/test_commands/test_init.py`.

## Fields
| Field | Type | Required | Notes |
|---|---|---|---|
| check | any | yes | Must be `state-contract` for the standalone check result. |
| passed | any | yes | True only when all state-contract requirements pass. |
| findings | any | yes | Contains error findings for missing evidence files or terms. |
| inspected | any | yes | Number of state-contract requirements inspected. |

## Failure Cases
- Missing required evidence files or terms MUST produce error findings with
  target paths that point at the missing evidence.
- JSON output MUST remain valid and include state-contract findings when the
  aggregate check fails.
- The verification gate MUST report state-contract failures alongside other
  verification hook failures.

## Scope
- In scope: check adapter, check command registration, check-all aggregation,
  verification hook, init scaffold, docs/tests.
- Out of scope: automatic writer/consumer static analysis, release hook changes,
  broader interactive UX changes, and external service verification.
