# Subagent Separation Gate Verification

## Freshness

Verified on 2026-06-19.

## Results

Subagent-separation command coverage passed for the targeted checks below.
`harness check all` remained blocked by pre-existing routing and inventory
backlog unrelated to this gate implementation.

## Evidence

Evidence consists of the targeted pytest run, direct CLI check runs, docs check,
py_compile, and the explicit `harness check all` failure record listed below.

## Passed Commands

- `pytest tests/test_commands/test_check_cmd.py tests/test_commands/test_aliases.py`
  - Result: passed, 32 tests.
- `harness check subagent-separation`
  - Result: passed, 1 item inspected.
- `harness check docs`
  - Result: passed, 14 items inspected.
- `python -m py_compile src/harness_governance/commands/check.py src/harness_governance/commands/aliases.py`
  - Result: passed.

## Failed / Skipped Commands

- `harness check all`
  - Result: failed.
  - Owner layer: existing routing / inventory backlog, not this implementation.
  - Evidence: failures are limited to `.agents/skills/harness-governance-*` missing `## Harness Precondition` / canonical layer terms and `README.md` missing enabled skill inventory rows.
- `ruff format --check ...` and `ruff check ...`
  - Result: skipped due to unavailable tool.
  - Evidence: `ruff` was not found on PATH and `python -m ruff` reported `No module named ruff`.

## User-Perceived Integration Evidence

- Evidence level: contract
- Real User Entry: `harness check subagent-separation`, `harness check all`, and `harness ship`
- User-Visible State: CLI exposes `subagent-separation` pass/fail and aggregation rows include the check
- Persistence/External State: Markdown verification files and invocation logs are read from disk
- Anti-Self-Proof Assertion: failing fixture docs, invocation log fixtures, CLI output, `check all` JSON, and `ship` JSON all reference the same check result
- Forbidden Test Shortcuts: none
- Command: `pytest tests/test_commands/test_check_cmd.py tests/test_commands/test_aliases.py`; `harness check subagent-separation`; `harness check docs`
- Result: passed on 2026-06-19

## Subagent Separation

- Required: no
- Waiver: this implementation is the first version of the subagent-separation checker, so independent subagent enforcement did not exist before the change
- Replacement Verification: contract-first pytest, CLI checks, docs check, py_compile, and explicit `harness check all` failure record
- Residual Risk: no independent verifier invocation was recorded for this first implementation; future work can use this new gate to require it
