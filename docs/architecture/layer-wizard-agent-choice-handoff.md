# Layer Wizard Agent Choice Handoff Architecture

## Boundaries

```text
Local terminal user
  -> harness layer wizard
  -> click TTY selector
  -> session layer_qa / layer transition

Agent-mediated user interface
  -> harness layer wizard --json
  -> structured pending prompt payload
  -> outer UI asks the real author
  -> harness layer answer / layer advance --confirmed
  -> session layer_qa / layer transition
```

Firm boundaries:
- Local TTY behavior remains interactive and may record answers directly.
- JSON output must not record answers or advance layers.
- Author confirmation is represented only by a later explicit command carrying
  the selected answer or confirmed advancement.

Negotiable boundaries:
- The exact JSON field names may evolve while tests define the first contract.
- A future dedicated bridge command can reuse the same payload shape.

## Component Responsibilities

- `commands/layer.py`: resolves wizard state, builds pending prompt payload,
  preserves interactive question and advance flows.
- `messages.py`: keeps human-readable guidance aligned with the JSON handoff.
- CLI consumers: render JSON choices to the real author and submit the selected
  answer through existing commands.

## Ownership

The harness CLI owns the wizard state contract and session persistence. External
agent/chat UIs own rendering the payload and collecting the real author's
choice.

## Data Flow

For `harness layer wizard --json`, input is the current session and optional
layer. Output is a JSON payload containing current layer status plus either:

- a pending Author Question with suggested answer and action choices; or
- a pending advance decision when the gate already passes.

No session write occurs in this JSON path.

## ADR Candidates

- Record that wizard JSON is a read-only handoff contract, not an answer
  recording API. This is a durable provenance boundary and should be captured in
  an ADR.
