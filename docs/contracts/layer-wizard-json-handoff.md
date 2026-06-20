# Layer Wizard JSON Handoff Contract

## C1 Pending Question Payload

The system MUST make `harness layer wizard --json <layer>` return a read-only
payload for the next unanswered Author Question.

| Field | Type | Required |
|---|---|---|
| `pending_question` | Any | yes |
| `pending_advance` | Any | yes |

When `pending_question` is not null, it contains `question`,
`suggested_answer`, and `actions` entries. Each action contains `key` and
`label`.

Verified by a CLI test asserting:
- `questions_recorded` remains `0`;
- session `layer_qa` remains unchanged;
- `pending_question.question` contains the next Author Question;
- `pending_question.suggested_answer` is present;
- `pending_question.actions` includes `confirm`, `edit`, `skip`, and `back`.

## C2 Pending Advance Payload

The system MUST make `harness layer wizard --json <layer>` return a pending
advance choice when the current layer gate has already passed.

When `pending_advance` is not null, it contains `layer` and `actions` entries.
Each action contains `key` and `label`.

Verified by a CLI test asserting:
- `gate_passed` is `true`;
- `next_layer` is present when the rigor path has a next layer;
- `pending_advance.layer` equals `next_layer`;
- `pending_advance.actions` includes `yes`, `no`, and `back`.

## C3 Existing Interactive Behaviour

The system MUST preserve existing interactive wizard behaviour.

Verified by existing wizard tests for confirm, edit, skip, back, and advance.

## Failure And Boundary Cases

- Empty input to interactive selection still stops rather than auto-advancing.
- JSON output never records answers or advances layers.
- The change does not add a new persistence path.
