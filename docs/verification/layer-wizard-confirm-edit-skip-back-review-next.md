# Review Next: Layer Wizard Confirm/Edit/Skip/Back

## Done Summary

`harness layer wizard` now provides per-question suggested answers and
Confirm/Edit/Skip/Back actions. Confirm/Edit record answers, Skip leaves the
question unanswered, and Back can revisit the previous question. Existing
`layer ask` and `layer answer` behaviours remain compatible.

## Evidence

- `pytest tests/test_commands/test_layer_cmd.py -q`
  - Result: passed, 41 tests.
- `harness check docs --self`
  - Result: passed, 71 items.

## Risks And Lessons

- Governance UX can block governance itself; guided Author Question UX should be
  treated as implementation-critical.
- Suggested answers must require explicit Confirm/Edit before recording.
- Contract field tables should use checker-friendly type names.
- Capability-Tiered Subagent Routing should keep interaction and independent
  verification paths explicit.

## Queue Decision

No new queue item is needed. The next priority remains
Capability-Tiered Subagent Routing in `upgrade.md`.
