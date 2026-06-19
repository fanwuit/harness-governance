# Contract: Governance UX Friction Reduction

## Behaviour

1. Recording an answer for the same layer and question more than once must keep one current answer for that layer/question pair.
2. The answer count reported by `harness layer answer` must count unique questions for that layer.
3. `harness layer ask` must not prompt for questions already answered in the session.
4. Gate failure guidance must not print duplicate missing artifacts, blocking artifacts, or confirmation items.
5. Critical confirmation guidance must present explicit choices in text where the CLI cannot provide a richer selector.
6. Gate pass/fail semantics must remain unchanged.

## Field Specifications

| Field | Type | Required |
|---|---|---|
| question | str | yes |
| answer | str | yes |
| timestamp | str | yes |
| questions_answered | int | yes |

## Failure Cases

- Unknown layer names still fail with the existing layer resolution error.
- Missing required questions still fail gates.
- Missing blocking artifacts still fail gates.
- Non-blocking missing artifacts remain informational unless already enforced by a gate hook.

## Existing Contracts To Extend

- `tests/test_commands/test_layer_cmd.py`
- `tests/test_commands/test_gate_cmd.py`
- `tests/test_state_machine/test_gates.py`

## Scope

- Arrow-key selector.
- Platform slash-command UX.
- Automatic gate progression.
- Changing required question thresholds.
