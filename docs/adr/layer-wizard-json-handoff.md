# ADR: Layer Wizard JSON Handoff Is Read-Only

## Status

Accepted.

## Context

`harness layer wizard` supports a local terminal selector for Author Questions.
In agent-mediated environments, a tool PTY can render that selector but the
chat user cannot operate it directly. If an agent sends stdin to that PTY, the
result can look like author confirmation even though the author did not make
the menu choice.

## Decision

`harness layer wizard --json` will be the read-only handoff contract for
agent-mediated interfaces. It may report the current gate state, the next
pending Author Question, suggested answer, available actions, and pending
advance choice. It must not record answers or advance layers.

Real author confirmation remains a separate explicit write through existing
commands such as `harness layer answer` and `harness layer advance --confirmed`.

## Alternatives

- Keep only TTY wizard behavior.
  Rejected because it cannot hand choice control to chat users.
- Add a separate bridge command.
  Deferred because it would duplicate wizard state resolution.
- Allow agents to operate TTY menus.
  Rejected because it blurs Author Question provenance.

## Consequences

- Local TTY users keep the existing menu workflow.
- Agent/chat integrations can render a structured payload to the real author.
- Callers must perform a second explicit command after the real user chooses.
- JSON output must distinguish pending choices from recorded answers.

## Validation

- Tests assert JSON wizard output includes pending question choices without
  recording answers.
- Tests assert JSON wizard output includes pending advance choices when the gate
  has already passed.
- Existing interactive wizard tests continue to pass.
