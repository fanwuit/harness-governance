# Layer Wizard Agent Choice Handoff Brief

## Goal

`harness layer wizard` must let real authors make Author Question choices in
agent-mediated environments instead of letting an agent-operated tool PTY count
as author confirmation.

## Non-Goals

- Do not remove or degrade the existing local terminal TTY menu.
- Do not treat suggested answers as author-approved without a submitted choice.
- Do not build a full chat UI; expose a CLI contract that an outer UI or agent
  can bridge.

## Options Considered

1. Keep only the current TTY menu.
   This preserves local behavior but does not solve agent-mediated workflows.
2. Extend `wizard --json` to expose pending choices.
   This gives outer tools a structured handoff but must not record answers by
   itself.
3. Add a separate agent bridge command.
   This is explicit but duplicates wizard state logic.

## Decision

Extend wizard JSON behavior to include the next pending Author Question,
suggested answer, available actions, and next advance choice when applicable.
Keep interactive recording and advancement unchanged.

## Risks And Unknowns

- Outer tools still need to render the structured payload and submit the chosen
  answer with existing commands.
- The JSON payload must make clear that choices are pending, not confirmed.

## Success Criteria

- `harness layer wizard --json` exposes a pending Author Question and choices
  without recording an answer.
- The JSON payload exposes the advance decision when the current gate already
  passes.
- Existing TTY and non-TTY wizard tests continue to pass.
- Tests cover the agent handoff payload.

## Next Layer

Architecture.
