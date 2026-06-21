# Contract: P0 Capability-Tiered Subagent Routing

## Behaviour

1. **CapabilityTier resolution**
   - System MUST return `EXECUTION` for `implementer` role unless overridden in config.
   - System MUST return `STRONG` for `planner`, `verifier`, `reviewer`, `contract-writer`.
   - System MUST return `MECHANICAL` for `document-gardener`.
   - System MUST accept per-role overrides from `HarnessConfig.role_capability_overrides`.
   - System MUST fall back to `STRONG` for unknown roles.
   - Verified by: `tests/test_state_machine/test_capability_routing.py::TestRoleCapabilityPolicy`

2. **Verifier requirement**
   - System MUST return `verifier_required=true` for `EXECUTION` and `MECHANICAL` tiers.
   - System MUST return `verifier_required=false` for `STRONG` tier.
   - Verified by: `tests/test_state_machine/test_capability_routing.py::TestVerifierRequirement`

3. **Agent declaration discovery**
   - System MUST scan well-known agent directories (`.claude/`, `.agents/`, `.clinerules/`, `.cursor/`, `.opencode/`, `.windsurf/`, `.`) for `tiers.json`.
   - System MUST parse valid `tiers.json` into `AgentCapabilityDeclaration`.
   - System MUST skip invalid/missing `tiers.json` without error.
   - Verified by: `tests/test_state_machine/test_agent_declarations.py::TestDiscoverDeclarations`

4. **Adapter resolution from declarations**
   - System MUST match by (role, required_tier) pair against declarations.
   - System MUST return first match in priority order.
   - System MUST return `None` when no match found.
   - Verified by: `tests/test_state_machine/test_agent_declarations.py::TestResolveAdapterFromDeclarations`

5. **Skill invocation provenance**
   - `SkillChainTracer.start_invocation()` MUST record `required_tier`, `actual_tier`, `platform`, `model_label`, `adapter`, `verifier_required`, `owner_files`, `changed_files`.
   - Provenance fields MUST be persisted to NDJSON.
   - Verified by: `tests/test_state_machine/test_skill_chain.py::TestStartInvocationProvenance`

6. **Gate enforcement at REVIEW_NEXT**
   - System MUST reject closeout when `verifier_required=true` invocations have no matching `role=verifier, actual_tier=strong` invocation.
   - System MUST reject when a call acts as both execution-tier and strong verifier.
   - Verified by: `tests/test_state_machine/test_skill_chain.py::TestGateHookCapabilityTier`

7. **Orchestrator prompt includes capability info**
   - Assembled prompt MUST contain "Capability Tier Requirements" section.
   - `role_capabilities` metadata MUST be populated on `OrchestratorPrompt`.
   - Verified by: `tests/test_subagent_runner/test_orchestrator.py`

## Failure Cases

| Condition | Expected Behaviour |
|---|---|
| No agent dir has tiers.json | Adapter resolution returns `None`, falls back to platform-generic |
| tiers.json has invalid JSON | File is silently skipped, logged as warning |
| Config override specifies unknown role | Override is ignored, policy falls back to default |
| Gate hook encounters no invocations | Passes (nothing to verify) |
| Verifier invocation has `actual_tier=execution` | Not counted as strong verifier, enforcement fails |

## Schema: tiers.json Format

```json-schema
{
  "$schema": "https://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "platform": {
      "type": "string",
      "description": "Platform identifier (e.g. claude-code, opencode)"
    },
    "adapters": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "role": { "type": "string" },
          "required_tier": {
            "type": "string",
            "enum": ["strong", "execution", "mechanical"]
          },
          "adapter": { "type": "string" },
          "model_label": { "type": "string" }
        },
        "required": ["role", "required_tier", "adapter"]
      }
    }
  },
  "required": ["platform", "adapters"]
}
```

| JSON Path | JSON Type | Required | Description |
|---|---|---|---|
| `$.platform` | string | yes | Agent platform identifier |
| `$.adapters` | array | yes | List of adapter declarations |
| `$.adapters[].role` | string | yes | Role name (e.g. implementer, verifier) |
| `$.adapters[].required_tier` | string | yes | `strong`, `execution`, or `mechanical` |
| `$.adapters[].adapter` | string | yes | Executor adapter name |
| `$.adapters[].model_label` | string | no | Opaque model identifier |

## Scope Out of Bounds

- Adapter dispatch/execution (not in this P0)
- CLI commands for capability tier inspection
- Per-platform model ranking inside harness core
