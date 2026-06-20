# Contract: Layer Wizard Confirm/Edit/Skip/Back

## Field Specifications

### Question interaction result

| Field | Type | Required | Description |
|---|---|---|---|
| action | str | yes | Author-selected action for the current question: confirm, edit, skip, or back. |
| answer | str | conditional | Final answer for Confirm/Edit; absent for Skip/Back. |
| question | `str` | yes | Author Question text being handled. |
| suggested_answer | `str` | yes | Suggested answer shown before author action. |

## Behaviour

### C1: Suggested answer display

The system MUST show a suggested answer for each unanswered Author Question in
`harness layer wizard`.

Verified by: focused wizard CLI tests in `tests/test_commands/test_layer_cmd.py`.

### C2: Confirm records suggested answer

The system MUST record the suggested answer when the author explicitly chooses
Confirm.

Verified by: session `layer_qa` assertions after wizard input.

### C3: Edit records edited answer

The system MUST prompt for replacement text and record that edited answer when
the author chooses Edit.

Verified by: session `layer_qa` assertions after wizard input.

### C4: Skip does not record

The system MUST NOT write a `layer_qa` entry for a skipped question.

Verified by: gate/check assertions showing insufficient answers after skip.

### C5: Back navigates to previous question

The system MUST allow Back to return to the previous question without crashing
or corrupting recorded answers.

Verified by: wizard input sequence covering Back then Confirm/Edit.

### C6: Existing commands remain compatible

The system MUST preserve existing `layer ask` and `layer answer` behaviours.

Verified by: existing `test_ask_*` and `test_answer_*` tests.

## Failure Cases

- Skip must not write to `layer_qa`.
- Back at the first question must not crash.
- Empty edit input must abort or refuse recording; it must not record an empty
  answer.
- Non-TTY input exhaustion must preserve abort guidance.
- Suggested answers must not be recorded without explicit Confirm/Edit action.

## Scope

In scope:
- `harness layer wizard` Author Question interaction.
- TTY and non-TTY action selection.
- Focused tests in `tests/test_commands/test_layer_cmd.py`.

Out of scope:
- `harness layer ask` interaction changes.
- `harness layer answer` interaction changes.
- Gate counting semantics.
- Full answer provenance schema (`source`, `recorded_via`, `author_action`).
- Capability-Tiered Subagent Routing.
- New dependencies.
