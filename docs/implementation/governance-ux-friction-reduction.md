# Implementation: Governance UX Friction Reduction

## Summary

Implemented the dependency-free first slice:

- `harness layer answer` now replaces an existing answer for the same layer/question pair instead of appending a duplicate.
- Gate failure guidance now de-duplicates repeated missing artifacts, blocking artifacts, and confirmation items.
- Gate failure guidance now includes explicit text choices for what to do next.

## Files Changed

- `src/harness_governance/commands/layer.py`
- `src/harness_governance/commands/gate_failure.py`
- `tests/test_commands/test_layer_cmd.py`
- `tests/test_commands/test_gate_cmd.py`

## Verification Command

```bash
pytest tests/test_commands/test_layer_cmd.py tests/test_commands/test_gate_cmd.py -q
```

Result: passed.
