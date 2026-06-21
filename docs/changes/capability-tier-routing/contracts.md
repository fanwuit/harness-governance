# Contracts: capability-tier-routing

## Current behavior

Harness already has Subagent Separation evidence checks, but those checks do not
define required capability tiers for roles or enforce that lower-tier execution
is accepted by an independent strong verifier.

## Proposed behavior / contract delta

Harness resolves each subagent role to a platform-neutral capability tier:
`strong`, `execution`, or `mechanical`. Lower-tier work requires independent
strong verification before Review/Next closeout can pass.

## Contract artifacts

- Artifact: capability-tier routing contract
- Path: `docs/contracts/capability-tier-routing.md`
- Type: documentation invariant plus executable unit tests

## Acceptance checks

- `tests/test_state_machine/test_capability_routing.py`
- `tests/test_state_machine/test_agent_declarations.py`
- `tests/test_state_machine/test_skill_chain.py`
- `tests/test_subagent_runner/test_orchestrator.py`
- `tests/test_subagent_runner/test_adapter_registry.py`

## Failure cases

- Missing `tiers.json` declaration falls back to platform-generic behavior.
- Invalid `tiers.json` is skipped without crashing.
- Lower-tier invocation without strong verifier fails Review/Next gate.
- A single invocation cannot act as both lower-tier worker and strong verifier.

## Contract-first reminder

The durable contract is `docs/contracts/capability-tier-routing.md`; executable
coverage is provided by the acceptance checks above.
