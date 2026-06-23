Implementation Entry Record:
- Current layer: implementation
- Target: src/harness_governance/commands/evidence_scanner.py; src/harness_governance/commands/check.py; tests/test_commands/test_evidence_scanner.py
- Scope: Implement artifact-level evidence scanning (Playwright trace, HAR, test source selectors) and integrate into check_user_evidence.
- Contract evidence: docs/contracts/user-evidence-artifact-scanning.md
- Readiness gate: pass: contract tests prepared in tests/test_commands/test_evidence_scanner.py covering C1-C8
- Packetization: not-needed
- Verification command: pytest tests/test_commands/test_evidence_scanner.py tests/test_commands/test_check_cmd.py
- Review / Next state file: review-next pending after verification
- Stop conditions: Stop before adding non-stdlib dependencies; stop if scanner crashes on malformed artifacts; stop if existing user-evidence tests regress.

## Evidence Scanner Field Alignment

| Field | Implementation Source |
|---|---|
| repo_root | scan_evidence_artifacts(repo_root: Path, evidence_doc: Path) parameter in evidence_scanner.py |
| evidence_doc | scan_evidence_artifacts(repo_root: Path, evidence_doc: Path) parameter in evidence_scanner.py |
