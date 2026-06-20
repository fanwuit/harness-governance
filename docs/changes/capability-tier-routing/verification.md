# Verification: P0 Capability-Tiered Subagent Routing

## User-Perceived Integration Evidence

- Evidence level: contract
- Real User Entry: Agent platform maintainer places `tiers.json` in agent config dir
- User-Visible State: harness review auto-close works, gate hook enforces verification
- Persistence/External State: tiers.json persists in agent directory
- Anti-Self-Proof Assertion: Gate hook at REVIEW_NEXT validates execution/mechanical cannot self-verify; tests use real invocation records not mocks
- Forbidden Test Shortcuts: no self-Q&A mock, no shortcut assertions
- Command: python -m pytest tests/test_state_machine/test_capability_routing.py tests/test_state_machine/test_agent_declarations.py tests/test_state_machine/test_skill_chain.py tests/test_subagent_runner/test_orchestrator.py -q
- Result: All 103 tests passed

## Results

All unit tests pass. Gate hook correctly rejects self-verification. Agent declaration discovery works across multiple directory layouts.
