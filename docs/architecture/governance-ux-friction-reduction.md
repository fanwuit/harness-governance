# Architecture: Governance UX Friction Reduction

## Boundaries

- `commands/layer.py` owns user-facing layer interaction commands and session answer recording.
- `commands/gate_failure.py` owns reusable failed-gate guidance text.
- `state_machine/gates.py` owns gate evaluation and should keep enforcement semantics unchanged.
- `messages.py` owns localized/bilingual message strings.
- Tests under `tests/test_commands/` own CLI behavior coverage.

## Component Responsibilities

- Layer command:
  - Record author answers.
  - Avoid duplicate answers for the same layer/question pair.
  - Render follow-up guidance after `layer ask`.
- Gate failure formatter:
  - Present missing requirements and required actions.
  - Avoid duplicate missing items or confirmation lines.
- Gate engine:
  - Continue reporting the same pass/fail decision.
  - Provide data for display without changing threshold semantics.

## Owners

- CLI command behavior: `src/harness_governance/commands/`.
- Gate semantics: `src/harness_governance/state_machine/`.
- Message catalog: `src/harness_governance/messages.py`.
- Regression tests: `tests/test_commands/` and `tests/test_state_machine/`.

## Data Flow

```text
author input
-> harness layer answer/ask
-> SessionState.layer_qa
-> LayerGateEngine.check
-> GateStatus
-> command/gate failure output
```

Persistence remains limited to session JSON, lock files, and documentation artifacts.

## ADR Candidates

- Accepted in this task: dependency-free prompt improvements instead of a full TTY selector.
- Deferred: adopting a terminal selector dependency for arrow-key choices.

## Review Notes

This change should not alter `LayerGateEngine.check` pass/fail semantics. Any UX de-duplication must happen either while recording answers or while formatting output.
