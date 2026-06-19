# ADR: Extend State Contract Closure Into Checks and Init

## Status
Accepted for this P1 implementation.

## Context
`harness state-contract check` already validates that persisted governance
state writers have corresponding check/gate consumers and regression evidence.
`upgrade.md` still lists two P1 enhancements: connect this evidence to the
standard verification/check path, and generate downstream test scaffolding.

## Decision
Keep the existing state-contract command as the requirement source, add a
`CheckResult` adapter in `src/harness_governance/commands/check.py`, include that adapter in
`harness check all`, register a verification gate hook that invokes it, and
generate a downstream scaffold test during `harness init`.

## Rationale
This keeps one requirement list while allowing all normal governance surfaces
to consume the same evidence. It also makes initialized projects inherit the
testing expectation without needing to copy harness internals.

## Alternatives
- Duplicate requirements inside `src/harness_governance/commands/check.py`: rejected because it creates drift.
- Only document the expectation: rejected because P1 asks for gate/check
  integration and scaffolding.
- Build automatic writer/consumer scanning now: deferred because it is listed
  separately as a future enhancement.

## Consequences
- Missing state-contract evidence can now block verification closure.
- `harness check all` becomes stricter.
- Initialized projects receive a scaffold that should be customized.

## Validation
Run focused tests for check command behavior, verification gate hook behavior,
init scaffold creation, and the existing state-contract command.
