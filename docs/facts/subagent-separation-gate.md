# Subagent Separation Gate Facts

## Sources

- `upgrade.md` section `1C. Subagent Separation Gate` defines the P0 objective, trigger conditions, required role matrix, invocation evidence, file ownership checks, and closure authority checks.
- `src/harness_governance/commands/check.py` already contains `check_user_evidence`, a document-level checker that validates structured Markdown evidence and is wired into `harness check all`.
- `tests/test_commands/test_check_cmd.py` covers document-level check helpers, CLI output, and `check all` aggregation patterns.

## Confirmed Facts

- The requested task is to implement `harness check subagent-separation`.
- The first version is a document-level evidence check.
- The first version must not automatically dispatch subagents.
- The checker should follow the existing `CheckResult` / `CheckFinding` pattern.
- The checker should be added to `harness check all`.
- `harness ship` should include this P0 check in release-readiness checks.

## Declared Unknowns

### Evidence Format

Assumption: The first version can use the Markdown section from `upgrade.md`:

```markdown
## Subagent Separation
- Required: yes | no
- Contract Owner:
- Test/Evidence Owner:
- Implementer:
- Verifier:
- Waiver:
```

Risk: If this format is too weak, later automation may need a richer schema, but this keeps the P0 first version compatible with the existing document-level check style.

### Trigger Strategy

Assumption: The first version can trigger on strict/P0/P1/contract/user-closure language found in change documents and verification documents.

Risk: Text triggers can produce false positives or miss implicit risk. The first version should favor explicit structured evidence and clear error messages over automatic role dispatch.

### Invocation Evidence

Assumption: The first version can look for role evidence in `.harness/invocations.ndjson` and `docs/changes/<change-id>/.invocations.ndjson`.

Risk: Existing logs may not yet contain every desired ownership field. The checker should require distinguishable role records first, and leave richer ownership provenance for later enhancement.

