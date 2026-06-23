# Architecture: Layer Wizard Confirm/Edit/Skip/Back

## Boundaries

Firm boundaries:
- Preserve `harness layer ask` text-input behaviour.
- Preserve `harness layer answer` public semantics.
- Preserve the current gate counting model for this task.
- Add no dependencies.
- Do not implement the full answer provenance schema here.

Negotiable boundaries:
- Helper names and internal structure.
- Suggested-answer generation strategy.
- Back navigation mechanics.
- Whether `_select_choice` is reused directly or wrapped.

## Component Responsibilities

- `src/harness_governance/commands/layer.py`
  - Owns `layer wizard` interaction flow.
  - Owns per-question action selection and answer recording.
- `src/harness_governance/messages.py`
  - Owns user-visible prompt and choice labels.
- `tests/test_commands/test_layer_cmd.py`
  - Owns behavioural coverage for confirm, edit, skip, back, and existing
    compatibility.
- `docs/*/layer-wizard-confirm-edit-skip-back.md`
  - Own durable governance evidence for this change.

## Owners

The harness-governance CLI owns the command behaviour. The session gate engine
remains the consumer of recorded answers and is not changed by this slice.

## Data Flow

```text
layer guide questions
  -> wizard builds suggested answer per question
  -> per-question selector shows Confirm/Edit/Skip/Back
  -> Confirm/Edit produce final answer
  -> _append_layer_answer writes final answer to session.layer_qa
  -> gate check counts recorded answers as before
```

Skip does not write an answer. Back adjusts the current question pointer. This
change does not add new persisted session fields.

## ADR Candidates

- No ADR required for this slice. The change adjusts CLI interaction mechanics
  without freezing a long-lived external API, storage contract, or platform
  boundary.

## Risks

- Back navigation can be confusing if it reaches an already-recorded question.
- Suggested answers can be mistaken for final answers if prompt copy is unclear.
- Non-TTY numeric input must remain deterministic for tests.
