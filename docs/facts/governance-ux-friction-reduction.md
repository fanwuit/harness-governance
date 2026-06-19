# Facts: Governance UX Friction Reduction

## Scope

This task implements the `upgrade.md` Next Action 1 item: reduce governance UX friction without weakening gate enforcement.

## Source Evidence

- `upgrade.md` lists Governance UX Friction Reduction as a P1 next action.
- The requested behaviors include selectable layer questions, agent-prefill support, batch summary confirmation, stronger confirmations only at key risk points, ADR-not-required handling, isolation workspace explanation, and duplicate question/feedback reduction.
- Existing commands already expose layer guides and layer answers through `harness layer guide`, `harness layer answer`, and `harness layer ask`.

## Assumptions

Assumption: The first implementation should focus on CLI behavior and reusable prompt rendering, not a full terminal UI framework.
Risk: A broader interactive UI could increase test complexity and break non-interactive use.

Assumption: Existing gate semantics must remain unchanged.
Risk: UX improvements that auto-answer or skip requirements would weaken governance.

Assumption: The highest-value slice is reducing duplicate prompts and making confirmations explicit.
Risk: Implementing every listed UX idea in one pass could make the change too large to verify.

## Unknowns

- Whether future platform slash-command integrations need a separate prompt format.
- Whether direction-key selection should be implemented with an external dependency or a dependency-free numbered prompt.

## Recommendation

Use a dependency-free CLI slice:

- Add reusable option-style confirmation text for risky prompts.
- Add de-duplication for repeated layer answers or repeated missing-question feedback.
- Add explicit ADR-not-required and isolation-workspace prompt text where those flows are rendered.
- Preserve all existing gate checks and session state contracts.
