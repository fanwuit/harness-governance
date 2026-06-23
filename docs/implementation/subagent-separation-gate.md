Implementation Entry Record:
- Current layer: implementation
- Target: src/harness_governance/commands/check.py; src/harness_governance/commands/aliases.py; tests/test_commands/test_check_cmd.py; tests/test_commands/test_aliases.py
- Scope: Implement document-level subagent separation check and aggregate it in check all and ship.
- Contract evidence: docs/contracts/subagent-separation-gate.md
- Readiness gate: pass: readiness gate passed after contract tests were prepared
- Packetization: not-needed
- Verification command: pytest tests/test_commands/test_check_cmd.py tests/test_commands/test_aliases.py
- Review / Next state file: review-next pending after verification
- Stop conditions: Stop before touching files outside approved owner list; stop if implementation requires automatic subagent dispatch, runner schema migration, AST/git diff ownership proof, or contract changes.

## Subagent Separation Field Alignment

| Field | Implementation Source |
|---|---|
| Required | `## Subagent Separation` Markdown field parsed by the checker |
| Contract Owner | `## Subagent Separation` Markdown field parsed by the checker |
| Test/Evidence Owner | `## Subagent Separation` Markdown field parsed by the checker |
| Implementer | `## Subagent Separation` Markdown field parsed by the checker |
| Verifier | `## Subagent Separation` Markdown field parsed by the checker |
| Waiver | `## Subagent Separation` Markdown field parsed by the checker |
| Replacement Verification | `## Subagent Separation` Markdown field parsed by the checker |
| Residual Risk | `## Subagent Separation` Markdown field parsed by the checker |
