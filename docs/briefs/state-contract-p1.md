# Brief: State Contract P1 Enhancements

## Goal
Implement two scoped P1 upgrades from `upgrade.md`:

1. Include state-contract closure in `harness check` and the verification gate.
2. Generate downstream state-contract test scaffolding during `harness init`.

## Non-Goals
- Do not implement the broader Governance UX Friction Reduction item in this pass.
- Do not change release/tag behavior.
- Do not replace the existing `harness state-contract check` command.
- Do not introduce external services, network calls, or deployment behavior.

## Options Considered
- Add state-contract only to `harness check all`.
- Add state-contract to `harness check all` and verification gate.
- Start the broader interactive UX reduction work first.

## Decision/Direction
Add a `harness check state-contract` wrapper around the existing state-contract
requirements, include it in `check all`, enforce it from the verification gate,
and have `harness init` create a small downstream test skeleton documenting the
required writer -> consumer closure tests.

## Risks/Unknowns
- The wrapper must preserve existing JSON and CLI output conventions.
- The verification gate must report state-contract failures without masking
  user-evidence failures.
- The init scaffold must be advisory test material, not a false passing test.

## Success Criteria
- `harness check state-contract` returns a structured `CheckResult`.
- `harness check all` includes state-contract findings.
- Verification gate fails when state-contract evidence is missing.
- `harness init` creates a state-contract test scaffold unless `--minimal` is used.
- Focused pytest coverage proves the new check, gate hook, and init scaffold.

## Next Layer
Architecture, because this change crosses command aggregation, gate hooks, and
project initialization scaffolding.
