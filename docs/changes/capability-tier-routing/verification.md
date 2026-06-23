# Verification: P0 Capability-Tiered Subagent Routing

## Verification Commands

- python -m pytest tests/test_state_machine/test_capability_routing.py tests/test_state_machine/test_agent_declarations.py tests/test_state_machine/test_skill_chain.py tests/test_subagent_runner/test_orchestrator.py tests/test_subagent_runner/test_adapter_registry.py -q
- python -m pytest -q
- `harness check docs`
- `harness check all`

## Results

- passed: targeted capability routing tests in the closeout audit.
- passed: full pytest suite in the closeout audit.
- passed: `harness check docs` in the closeout audit.
- passed: `harness check all` in the closeout audit.

## User-Perceived Integration Evidence

- Evidence level: contract
- Real User Entry: Agent platform maintainer places `tiers.json` in agent config dir
- User-Visible State: harness review auto-close works, gate hook enforces verification
- Persistence/External State: tiers.json persists in agent directory
- Anti-Self-Proof Assertion: Gate hook at REVIEW_NEXT validates execution/mechanical cannot self-verify; tests use real invocation records not mocks
- Forbidden Test Shortcuts: no self-Q&A mock, no shortcut assertions
- Command: python -m pytest tests/test_state_machine/test_capability_routing.py tests/test_state_machine/test_agent_declarations.py tests/test_state_machine/test_skill_chain.py tests/test_subagent_runner/test_orchestrator.py tests/test_subagent_runner/test_adapter_registry.py -q
- Result: passed

## Subagent Separation

- Required: no
- Waiver: This closeout documents an already implemented first version and does not dispatch a new subagent.
- Replacement Verification: Targeted capability routing tests exercise role/tier resolution, agent declaration discovery, provenance persistence, orchestrator prompt metadata, and independent strong verifier enforcement.
- Residual Risk: Provider-specific model quality remains outside harness core and must be validated by each platform adapter owner.
