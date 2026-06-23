# ADR: Layer Wizard Confirm/Edit/Skip/Back

## Decision

Do not introduce a long-lived external architecture decision for this slice.
Implement the wizard interaction change as an internal CLI interaction update
using a dedicated question interaction helper.

## Rationale

The change affects terminal UX inside `harness layer wizard`; it does not freeze
an external API, persistence model, platform adapter boundary, deployment
boundary, or public schema. A focused architecture record and contract tests are
sufficient.

## Alternatives Considered

1. Minimal inline wizard patch.
2. Dedicated Author Question helper.
3. Non-TTY-first implementation with TTY deferred.

The selected direction is the dedicated helper because it keeps wizard flow
readable and leaves room for later answer provenance fields.

## Consequences

- Adds a small helper dedicated to Author Question interaction.
- Keeps `harness layer ask` and `harness layer answer` behaviour unchanged.
- Makes future `source`, `recorded_via`, and `author_action` provenance easier.
- If the helper is too narrow, the later provenance implementation may still
  need another adjustment.

## Validation

- Pytest target: `tests/test_commands/test_layer_cmd.py`
- Focused tests for Confirm/Edit/Skip/Back.
- Non-TTY numeric fallback coverage.
- Existing `layer ask`, `layer answer`, and `wizard` tests remain passing.
- `harness check docs --self`
