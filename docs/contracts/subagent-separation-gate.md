# Subagent Separation Gate Contract

## Behaviour

The system MUST provide `harness check subagent-separation`.
Verified by CLI tests.

The checker MUST scan verification Markdown for `## Subagent Separation`.
Verified by focused checker tests.

The checker MUST return `CheckResult(check="subagent-separation")`.
Verified by unit tests.

The checker MUST be included in `harness check all`.
Verified by JSON CLI aggregation tests.

The checker MUST be included in `harness ship`.
Verified by alias aggregation tests.

## Evidence Contract

The checker result MUST use the existing `CheckResult` shape:

| Field | Type | Required |
|---|---|---|
| check | any | yes |
| passed | any | yes |
| findings | any | yes |
| inspected | any | yes |

For required separation, the evidence block MUST include these Markdown labels:

- Required: `yes` or `no`, always present.
- Contract Owner: text, when `Required: yes`.
- Test/Evidence Owner: text, when `Required: yes`.
- Implementer: text, when `Required: yes`.
- Verifier: text, when `Required: yes`.
- Waiver: text, when `Required: no`, optional otherwise.
- Replacement Verification: text, when `Required: no`.
- Residual Risk: text, when `Required: no`.

```markdown
## Subagent Separation
- Required: yes
- Contract Owner:
- Test/Evidence Owner:
- Implementer:
- Verifier:
- Waiver:
```

For waived separation, the evidence block MUST include:

```markdown
## Subagent Separation
- Required: no
- Waiver:
- Replacement Verification:
- Residual Risk:
```

## Failure Cases

The checker MUST fail when a triggering document omits `## Subagent Separation`.

The checker MUST fail when `Required: yes` omits any role field.

The checker MUST fail when `Required: yes` lacks distinguishable role invocation evidence.

The checker MUST fail when `Required: no` omits waiver reason, replacement verification, or residual risk.

The checker MUST fail on obvious text-level ownership violations:

- implementer modified contract/evidence files without approval;
- test/evidence owner modified implementation files without declaration;
- verifier modified implementation files and still claims ship-ready acceptance.

The checker MUST fail when verifier and implementer are the same invocation without waiver.

The checker MUST fail when non-verifier text claims `MVP complete`, `closed loop complete`,
`ship ready`, or `release ready`.

## Scope

- Automatic subagent dispatch.
- Runner schema migration.
- AST-level or git-diff-level ownership proof.
- Complete state-machine gate hook integration.
