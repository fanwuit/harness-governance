# Verification: Layer Wizard Confirm/Edit/Skip/Back

## Results

- `pytest tests/test_commands/test_layer_cmd.py -q`
  - Result: passed, 41 tests.
- `harness check docs --self`
  - Result: passed, 71 items.

## Evidence

- Confirm path: wizard records suggested answers through public CLI.
- Edit path: wizard records edited answer text and preserves session state.
- Skip path: wizard does not write skipped questions to `layer_qa`.
- Back path: wizard can revisit and revise the previous question.
- Non-TTY fallback: tests drive numeric choices through `CliRunner`.
- Compatibility: existing `layer ask`, `layer answer`, and previous wizard tests
  remain passing.

## User-Perceived Integration Evidence

- Evidence level: real-user acceptance
- Real User Entry: `harness layer wizard <layer>`
- User-Visible State: CLI output shows Question, Suggested answer, and
  Confirm/Edit/Skip/Back choices.
- Persistence/External State: `.harness/sessions/<session>.json` `layer_qa`
  entries are read back after CLI execution.
- Anti-Self-Proof Assertion: tests send CLI numeric choices and edited text,
  then read back persisted session answers; Skip leaves no matching answer.
- Forbidden Test Shortcuts: none; tests invoke the public CLI path.
- Command: `pytest tests/test_commands/test_layer_cmd.py -q`
- Result: passed, 41 tests.

## Unit Evidence

- Command: `pytest tests/test_commands/test_layer_cmd.py -q`
- Behaviour under test: wizard Confirm/Edit/Skip/Back and compatibility with
  existing layer commands.
- Boundary/negative cases: Skip does not record; Back revisits; non-TTY input
  exhaustion still stops at final advance selection.
- Mock boundary: Click `CliRunner` provides stdin/stdout; no internal command
  bypass is used.
- Why mocks do not hide product risk: tests call the public `harness` CLI command
  and inspect persisted session state.

## Integration Evidence

- Command: `harness check docs --self`
- Real modules crossed: command layer, session store, gate checks, docs checker.
- Writer: `harness layer wizard`
- Consumer: session loader and gate status checks in command tests.
- Persisted/readback state: `layer_qa` entries in session JSON.
- External systems mocked: none.
- Why acceptable: change is local CLI/session behaviour with no external service.

## Failures

None in the final verification run.
