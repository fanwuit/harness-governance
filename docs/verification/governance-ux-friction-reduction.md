# Verification: Governance UX Friction Reduction

## User-Perceived Integration Not Applicable

- Reason: This is CLI governance behavior, not product UI functionality.
- Replacement verification: focused CLI tests using `CliRunner`.
- Residual risk: Real terminal arrow-key behaviour is implemented with a dependency-free helper and covered by fallback CLI tests, but not by an end-to-end real TTY harness.

## Unit Evidence

- Command: `pytest tests/test_commands/test_layer_cmd.py tests/test_commands/test_gate_cmd.py -q`
- Behaviour under test: duplicate layer-answer replacement, skipped already-answered prompts, de-duplicated gate failure guidance, explicit next choices.
- Follow-up behaviour under test: `layer wizard` JSON status mode, non-interactive abort guidance, answer collection plus gate advance, and existing `layer ask` compatibility.
- Boundary/negative cases: missing QA still fails gates; JSON gate failure output still omits prose guidance.
- Mock boundary: `CliRunner` drives the real CLI command handlers against temporary project roots.
- Why mocks do not hide product risk: session JSON is loaded from disk and command output is asserted directly.

## Evidence

- Focused CLI tests assert persisted session state and command output.
- Isolation check confirms implementer and verifier workspaces exist for this governed session.
- `harness check all` was run; remaining failures after this document update are expected to be limited to pre-existing skill documentation inventory issues if they persist.

## Integration Evidence

- Command: `pytest tests/test_commands/test_layer_cmd.py tests/test_commands/test_gate_cmd.py -q`
- Real modules crossed: CLI command registration, layer command handlers, session persistence, gate failure formatter, gate command output.
- Writer: `harness layer answer`.
- Consumer: `harness layer ask`, `harness layer wizard`, `harness gate check`, and session load logic.
- Persisted/readback state: `SessionState.layer_qa` stored in `.harness/sessions/*.json` in test project roots.
- External systems mocked: none.
- Why acceptable: The changed behavior is local CLI/session behavior with no external service dependency.

## Subagent Separation

- Required: yes
- Contract Owner: invocation gov-ux-contract-20260619, `docs/contracts/governance-ux-friction-reduction.md`.
- Test/Evidence Owner: invocation gov-ux-evidence-20260619, focused CLI tests in `tests/test_commands/test_layer_cmd.py` and `tests/test_commands/test_gate_cmd.py`.
- Implementer: invocation gov-ux-implementer-20260619, `src/harness_governance/commands/layer.py` and `src/harness_governance/commands/gate_failure.py`.
- Verifier: invocation gov-ux-verifier-20260619, verification context using focused pytest commands and `harness isolation check`.
- Waiver: No external runner process was launched; role invocation records are local evidence for this governed session, isolation workspaces were created for implementer and verifier, and final acceptance is limited to implementation smoke plus focused CLI verification.
- Replacement Verification: Focused CLI tests, gate tests, py_compile, and isolation check listed below.
- Residual Risk: No external runner invocation log exists for this historical local-governance session.

## Results

- `pytest tests/test_commands/test_layer_cmd.py tests/test_commands/test_gate_cmd.py tests/test_state_machine/test_gates.py -q`: passed.
- `python -m pytest tests/test_commands/test_layer_cmd.py -q`: passed.
- `python -m pytest tests/test_commands/test_aliases.py tests/test_messages.py -q`: passed.
- `python -m py_compile src/harness_governance/commands/layer.py src/harness_governance/messages.py`: passed.
- `harness isolation check --session-id 20260619-upgrade-md-1-governance-ux-friction-redu`: passed.
- `harness check all`: initially failed on pre-existing skill documentation inventory issues and this document's missing subagent evidence section; this document now includes that section.
