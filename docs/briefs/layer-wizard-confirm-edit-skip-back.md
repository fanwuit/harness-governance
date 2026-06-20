# Brief: Layer Wizard Confirm/Edit/Skip/Back

## Goal

`harness layer wizard` displays a suggested answer for each Author Question and
offers Confirm/Edit/Skip/Back. Only Confirm/Edit writes an answer that can count
toward the gate; Skip does not count; Back returns to the previous question; TTY
and non-TTY operation both work.

## Non-Goals

- Do not change the basic text-input behaviour of `harness layer ask`.
- Do not implement the full `layer_qa.source` / provenance schema in this task.
- Do not add dependencies.
- Do not implement platform-specific UI.
- Do not start Capability-Tiered Subagent Routing.

## Options Considered

- Minimal wizard patch using existing `_select_choice`.
- Dedicated Author Question interaction helper.
- Non-TTY-first implementation with TTY deferred.

## Decision/Direction

Implement a dedicated per-question interaction helper for `layer wizard`, reusing
existing selection primitives where appropriate. Keep `layer ask` compatible.

## Risks/Unknowns

- `_select_choice` may need a wrapper for question-level semantics.
- Back navigation must avoid corrupting already recorded answers.
- Suggested answers must not be recorded automatically.

## Success Criteria

- Confirm records the suggested answer.
- Edit records the edited answer.
- Skip records no answer and does not satisfy the gate.
- Back returns to the previous question.
- Non-TTY numeric input is covered by tests.
- Existing `layer ask` and `layer answer` tests continue to pass.
- Focused tests cover confirm/edit/skip/back.

## Next Layer

Architecture.
