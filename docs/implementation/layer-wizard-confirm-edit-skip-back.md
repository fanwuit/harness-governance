Implementation Entry Record:
- Current layer: implementation
- Target: src/harness_governance/commands/layer.py; src/harness_governance/messages.py; tests/test_commands/test_layer_cmd.py
- Scope: Add per-question Confirm/Edit/Skip/Back interaction to harness layer wizard while preserving layer ask and layer answer compatibility.
- Contract evidence: docs/contracts/layer-wizard-confirm-edit-skip-back.md
- Readiness gate: pass
- Packetization: not-needed
- Verification command: pytest tests/test_commands/test_layer_cmd.py -q; harness check docs --self
- Review / Next state file: upgrade.md
- Stop conditions: stop before touching files outside approved owner list; stop if scope requires provenance schema, gate counting changes, new dependencies, or Capability-Tiered Subagent Routing.

## Implementation Summary

- Added a dedicated wizard Author Question interaction helper.
- Added deterministic suggested answers for current common layers.
- Confirm records suggested answers.
- Edit records edited answers.
- Skip records no answer.
- Back returns to the previous pending question.
- Existing `layer ask` and `layer answer` flows remain unchanged.

## Verification

- `pytest tests/test_commands/test_layer_cmd.py -q`
  - Result: passed, 41 tests.
- `harness check docs --self`
  - Result: passed, 71 items.
