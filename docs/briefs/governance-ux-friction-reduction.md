# Brief: Governance UX Friction Reduction

## Goal

Reduce governance interaction friction for `harness layer` and gate feedback while preserving strict gate semantics and non-interactive CLI compatibility.

## Context

`upgrade.md` identifies a P1 need to make layer questions and confirmations less repetitive and more explicit. The current system already records answers and checks gates, so this change should improve how prompts and feedback are presented rather than changing the underlying state machine.

## Non-Goals

- Do not weaken or skip any gate requirement.
- Do not add a full TTY selector dependency in this pass.
- Do not implement platform `/harness ...` slash-command behavior.
- Do not redesign the full 12-layer workflow.

## Options Considered

- Dependency-free prompt improvements.
- Full interactive selector.
- Documentation-only guidance.

## Decision/Direction

Implement a dependency-free UX slice that adds explicit choices to critical confirmations, reduces duplicate layer-answer or gate-feedback noise, and adds clearer ADR-not-required and isolation-workspace prompt wording where those flows are rendered.

## Risks/Unknowns

- Future terminal selector support may still be useful.
- Some duplicate prompts may be produced by agents rather than the CLI, so CLI de-duplication should focus on deterministic command output and session recording.
- Existing tests may depend on exact output strings.

## Success Criteria

- Existing gate/session behavior remains compatible.
- Repeated layer-answer recording for the same question does not create confusing duplicate state.
- Gate failure output does not repeat identical missing requirements.
- Critical progress confirmations present explicit choices.
- Tests cover the new behavior.

## Next Layer

Architecture.
