# Implementation: Governance UX Friction Reduction

## Summary

Implemented the dependency-free first slice:

- `harness layer answer` now replaces an existing answer for the same layer/question pair instead of appending a duplicate.
- Gate failure guidance now de-duplicates repeated missing artifacts, blocking artifacts, and confirmation items.
- Gate failure guidance now includes explicit text choices for what to do next.

Implemented the follow-up UX slice:

- `harness layer wizard` guides one layer through answer collection, gate check, and explicit `yes` / `no` / `back` advance choice.
- The wizard supports arrow-key / `j` / `k` selection on real TTYs and numbered fallback selection for non-TTY test or piped environments.
- `harness layer ask` and `harness layer wizard` avoid hanging on non-interactive empty input and report actionable `layer answer` / `wizard --json` guidance.
- Codex platform skill templates document `/harness ...` slash-style request mappings to canonical CLI commands.

## Files Changed

- `src/harness_governance/commands/layer.py`
- `src/harness_governance/commands/gate_failure.py`
- `src/harness_governance/cli.py`
- `tests/test_commands/test_layer_cmd.py`
- `tests/test_commands/test_gate_cmd.py`
- `src/harness_governance/data/skills/light/codex.md`
- `src/harness_governance/data/skills/standard/codex.md`
- `src/harness_governance/data/skills/strict/codex.md`

## Verification Command

```bash
pytest tests/test_commands/test_layer_cmd.py tests/test_commands/test_gate_cmd.py -q
```

Result: passed.

Follow-up verification:

```bash
python -m pytest tests/test_commands/test_layer_cmd.py -q
python -m pytest tests/test_commands/test_aliases.py tests/test_messages.py -q
python -m py_compile src/harness_governance/commands/layer.py src/harness_governance/messages.py
```

Result: passed.
