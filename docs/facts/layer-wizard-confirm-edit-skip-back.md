# Facts: Layer Wizard Confirm/Edit/Skip/Back

## Scope

Implement per-question selectable interaction for `harness layer wizard` Author
Questions.

## Observed Facts

- `src/harness_governance/commands/layer.py` contains `layer_wizard_cmd`.
- `layer_wizard_cmd` currently iterates Author Questions and calls
  `_prompt_author_answer(question, target)` for each unanswered question.
- `_prompt_author_answer` is text-input based.
- `_select_choice` already exists and supports TTY arrow/Enter selection with
  numeric fallback for non-TTY input.
- Current wizard selection is applied after gate check, when asking whether to
  advance to the next layer.
- `upgrade.md` records governance UX friction reduction work, but the current
  roadmap does not list per-question Confirm/Edit/Skip/Back as implemented.

## Assumptions And Risks

### Assumption

Existing wizard selection support is reusable for per-question actions.

### Risk

If `_select_choice` is only suitable for the final advance prompt, reusing it
directly may make non-TTY tests brittle or produce confusing prompts.

### Assumption

Suggested answers must remain suggestions until the author confirms or edits
them.

### Risk

If suggested answers are recorded automatically, the new UX would preserve the
self-answering failure mode it is meant to remove.

## Author Confirmation

The author confirmed the priority files, known unknowns, and existing evidence
during the `fact-discovery` layer.
