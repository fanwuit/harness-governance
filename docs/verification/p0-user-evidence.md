# P0 User Evidence Gate Verification

## Results

Passed on 2026-06-18.

## Evidence

Focused pytest, full pytest, ruff, `harness check user-evidence`, and
`harness check docs` were executed. `harness check all` still fails on
pre-existing routing/inventory findings in generated skill files; it does not
report a `user-evidence` failure.

## User-Perceived Integration Evidence
- Evidence level: real-user acceptance
- Real User Entry: `harness check user-evidence`, `harness check all`, `harness ship`, and `harness init`
- User-Visible State: CLI output reports user-evidence pass/fail and init creates `docs/verification/user-evidence-template.md`
- Persistence/External State: Markdown evidence files under `docs/verification/` and `docs/changes/*/verification.md` are read from disk
- Anti-Self-Proof Assertion: failing fixture docs, CLI findings, aggregated `check all` JSON, and ship check rows all reference the same `user-evidence` result
- Forbidden Test Shortcuts: none
- Command: `python -m pytest tests/test_commands/test_check_cmd.py tests/test_commands/test_aliases.py tests/test_commands/test_init.py`; `python -m ruff check src\harness_governance\commands\check.py src\harness_governance\commands\aliases.py src\harness_governance\commands\init.py src\harness_governance\state_machine\gates.py tests\test_commands\test_check_cmd.py tests\test_commands\test_aliases.py tests\test_commands\test_init.py`; `harness check user-evidence`
- Result: passed on 2026-06-18

## Unit Evidence
- Command: `python -m pytest tests/test_commands/test_check_cmd.py`
- Behaviour under test: document-level evidence parsing, required field validation, evidence level enforcement, Not Applicable validation, and change packet evidence detection
- Boundary/negative cases: empty required field, closure claim with `contract` evidence, missing change-packet verification, and evidence-free user-perceived verification doc
- Mock boundary: no mocks
- Why mocks do not hide product risk: tests exercise the real checker against real temporary files

## Integration Evidence
- Command: `python -m pytest tests/test_commands/test_check_cmd.py tests/test_commands/test_aliases.py tests/test_commands/test_init.py`
- Real modules crossed: CLI command routing, check aggregation, ship aggregation, init scaffolding, and gate hook registration
- Writer: `harness init` writes the user-evidence template
- Consumer: `harness check user-evidence`, `harness check all`, `harness ship`, and verification gate hook consume evidence
- Persisted/readback state: tests read generated template and Markdown evidence files back from disk
- External systems mocked: none
- Why acceptable: the feature is local filesystem and CLI behavior only

## Subagent Separation
- Required: no
- Waiver: historical P0 verification record created before the subagent-separation gate existed
- Replacement Verification: focused pytest, CLI aggregation tests, and `harness check user-evidence`
- Residual Risk: no independent verifier invocation is recorded for this historical evidence
