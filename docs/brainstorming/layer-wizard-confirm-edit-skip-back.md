# Brainstorming: Layer Wizard Confirm/Edit/Skip/Back

## Options

### Option A: Minimal wizard patch

- Best when: the existing selector is sufficient for per-question choices.
- Benefit: smallest implementation.
- Cost: action and answer prompting may remain coupled to existing wizard flow.
- Risk: brittle non-TTY tests if the final-advance selector assumptions leak into
  question prompts.
- Evidence needed: focused tests for confirm, edit, skip, back, and numeric
  fallback.

### Option B: Question interaction helper

- Best when: Author Questions need their own semantics and provenance.
- Benefit: separates suggested answer, author action, and final answer.
- Cost: modest new helper and test coverage.
- Risk: may duplicate small parts of `_select_choice` if not reused carefully.
- Evidence needed: helper tests through public `harness layer wizard` behaviour.

### Option C: Non-TTY-first implementation

- Best when: CI and scripted flows are the only priority.
- Benefit: easiest to test.
- Cost: does not fully address the user-facing arrow/Enter expectation.
- Risk: leaves the TTY UX gap unresolved.
- Evidence needed: explicit deferral and follow-up task.

## Recommendation

Choose Option B and reuse `_select_choice` where it fits. The per-question flow
needs a dedicated helper so `Confirm`, `Edit`, `Skip`, and `Back` have clear
semantics and so suggested answers cannot be recorded without author action.

## Must Do

- Add per-question actions to `harness layer wizard`.
- Confirm suggested answer records the answer.
- Edit records the edited answer.
- Skip leaves the question unanswered and does not count toward gate passage.
- Back returns to the prior unanswered question without corrupting recorded
  answers.
- Preserve TTY and non-TTY operation.

## Deferred

- Full answer provenance fields such as `source`, `recorded_via`, and
  `author_action`; those belong to the Author-Answer Provenance roadmap item.
- Platform-specific UI affordances beyond terminal selection.

## Excluded

- Pure text-only Author Question prompts in `layer wizard`.
- New dependencies.
- Automatic recording of suggested answers.

## Risks And Assumptions

- Assumption: `_select_choice` can remain the shared selection primitive.
- Risk: the current helper is tuned for final advance selection and may need a
  thin wrapper for question-specific prompts.
- Assumption: `layer ask` can remain text-input based for compatibility.
- Risk: users may expect the same UX in `layer ask`; document that `wizard` is
  the guided interaction surface.

## Next Layer Candidate

Brief.
