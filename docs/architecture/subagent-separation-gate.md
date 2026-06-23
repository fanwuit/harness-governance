# Subagent Separation Gate Architecture

## Boundary Diagram

```text
verification markdown
  docs/verification/*.md
  docs/changes/*/verification.md
        |
        v
subagent-separation checker
  reads structured evidence and invocation logs
        |
        v
CheckResult / CheckFinding
        |
        +--> harness check subagent-separation
        +--> harness check all
        +--> harness ship
```

## Boundaries

### Firm Boundaries

- Keep the existing Click CLI and `harness check` command architecture.
- Return the existing `CheckResult` / `CheckFinding` model.
- Use document-level Markdown evidence for the first version.
- Include the check in `harness check all` and `harness ship`.

### Negotiable Boundaries

- Trigger term coverage.
- Exact field names, as long as they match the documented evidence block.
- Minimum invocation-log recognition rules.
- Error message wording.

## Owners

- `commands/check.py`: owns the check command, document scan, evidence validation, and `check all` aggregation.
- `commands/aliases.py`: owns `harness ship` release-readiness aggregation.
- `tests/test_commands/test_check_cmd.py`: owns focused checker and CLI behavior coverage.
- `tests/test_commands/test_aliases.py`: owns `ship` aggregation coverage.
- Verification documents: owned by the change author, who records role evidence and waiver details.

## Data Flow

1. A change author records a `## Subagent Separation` evidence block in a verification document.
2. The checker scans `docs/verification/*.md` and `docs/changes/*/verification.md`.
3. The checker reads invocation evidence from `.harness/invocations.ndjson` or `docs/changes/<change-id>/.invocations.ndjson`.
4. The checker emits `CheckFinding` records for missing sections, missing fields, missing role evidence, waiver gaps, and obvious role-boundary violations.
5. The checker returns a `CheckResult`.
6. `harness check all` and `harness ship` aggregate the result.

## ADR Candidates

No standalone ADR is required for the first version. The change stays inside the existing check-command boundary and does not introduce a new persistence model, public API family, deployment boundary, or external dependency.

Possible future ADR: whether subagent separation should move from document-level evidence validation into runner-enforced dispatch and provenance.
