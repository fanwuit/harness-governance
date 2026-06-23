# Tests: capability-tier-routing

Status: done

## Test Owner

- Test Owner: test-writer unavailable for historical closeout; see verification.md Subagent Separation waiver.

## Test Types

- Unit: applicable
- Integration: applicable
- E2E: not applicable

## Test Files

- Path: tests/test_state_machine/test_capability_routing.py
- Path: tests/test_state_machine/test_agent_declarations.py
- Path: tests/test_state_machine/test_skill_chain.py
- Path: tests/test_subagent_runner/test_orchestrator.py
- Path: tests/test_subagent_runner/test_adapter_registry.py

## Red Green Evidence

- Expected failing command before product implementation: historical packet was completed before tests.md existed; red evidence unavailable.
- Green command: python -m pytest tests/test_state_machine/test_capability_routing.py tests/test_state_machine/test_agent_declarations.py tests/test_state_machine/test_skill_chain.py tests/test_subagent_runner/test_orchestrator.py tests/test_subagent_runner/test_adapter_registry.py -q

## Waiver

- Waiver:
- Replacement Verification:
- Residual Risk:
