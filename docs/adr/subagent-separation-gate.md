# ADR: Subagent Separation Gate First Version

## Status

Accepted.

## Decision

Do not create a broader standalone architecture boundary for the first version.
Implement `harness check subagent-separation` inside the existing `harness check`
architecture.

## Rationale

The first version is a document-level evidence checker. It does not introduce a
new persistence model, public API family, deployment boundary, external
dependency, or automatic subagent dispatch mechanism.

## Alternatives Considered

- Deep invocation provenance validation.
- Automatic subagent dispatch.

## Consequences

- Short-term maintenance cost stays low.
- The first version can have false positives or false negatives because it relies
  on structured Markdown and text-level evidence.
- Stronger future guarantees should move into runner schema and automatic
  provenance enforcement.

## Validation

Validate with pytest coverage for the checker, CLI command, `check all`
aggregation, and `ship` aggregation.

