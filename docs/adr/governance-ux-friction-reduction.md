# ADR: Dependency-Free Governance UX Friction Reduction

## Status

Accepted

## Context

`upgrade.md` requests lower-friction governance interactions, including selectable prompts, agent-prefill, batch summary confirmations, stronger critical confirmations, ADR-not-required handling, isolation workspace explanation, and de-duplicated question feedback.

The CLI is also used in scripted and non-interactive contexts, so adding a full interactive terminal dependency in the first pass would increase risk.

## Decision

Implement a dependency-free first slice:

- De-duplicate repeated layer answers by layer/question.
- De-duplicate repeated missing requirement and confirmation output.
- Add explicit textual choices to critical confirmation guidance.
- Document richer selector behavior as deferred.

## Rationale

This keeps the UX change compatible with non-interactive CLI usage and avoids introducing terminal behavior that would need broader integration testing.

## Alternatives Considered

- Full TTY selector with arrow-key navigation.
  - Rejected for this pass because it adds dependency and terminal test complexity.
- Documentation-only guidance.
  - Rejected because it does not improve deterministic CLI behavior.

## Consequences

- Positive: CLI output is quieter and safer without changing gate enforcement.
- Positive: Tests remain deterministic and CI-friendly.
- Negative: Arrow-key selection is still deferred.

## Validation

- Unit/CLI tests for duplicate answer replacement.
- CLI tests for de-duplicated gate failure guidance.
- Existing gate and layer tests must continue passing.
