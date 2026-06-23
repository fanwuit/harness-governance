# ADR: Capability-Tier Gate Enforcement at REVIEW_NEXT

## Decision

Enforce execution/mechanical self-verification prohibition at the
REVIEW_NEXT layer gate, not at VERIFICATION. The gate hook checks that
every invocation with `verifier_required=true` has a corresponding
strong verifier invocation.

## Rationale

REVIEW_NEXT is the final closeout gate — the last opportunity to catch
verification policy violations before a task is archived. Enforcing at
VERIFICATION would be premature: lower-tier work may still be pending
verification at that point.

## Consequences

- Verification may pass even when self-verification exists
- REVIEW_NEXT catches the violation and blocks closeout
- Execution/mechanical work cannot be closed without independent strong
  verifier proven in the skill chain
