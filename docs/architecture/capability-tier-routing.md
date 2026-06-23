# Architecture: P0 Capability-Tiered Subagent Routing

## Boundary Diagram

```
                              ┌─────────────────────┐
                              │   .harness/config    │
                              │  (role overrides)    │
                              └────────┬────────────┘
                                       │
┌──────────────────┐    ┌──────────────▼──────────────┐
│  Agent Dir       │    │  capability_routing.py      │
│  (tiers.json)    │───►│  - resolve_required_tier()  │
│  .claude/        │    │  - resolve_adapter()        │
│  .agents/        │    │  - build_provenance()       │
│  .opencode/      │    └──────────────┬──────────────┘
│  ...             │                   │
└──────────────────┘                   │
                         ┌─────────────▼──────────────┐
                         │  agent_declarations.py     │
                         │  - discover_declarations() │
                         │  - resolve_adapter_from_   │
                         │    declarations()          │
                         └─────────────┬──────────────┘
                                       │
              ┌────────────────────────┼────────────────────┐
              │                        │                     │
              ▼                        ▼                     ▼
  ┌────────────────────┐  ┌────────────────────┐  ┌──────────────────────┐
  │  orchestrator.py   │  │  skill_chain.py    │  │  schemas.py          │
  │  (prompt includes  │  │  - start_invoc()   │  │  CapabilityTier      │
  │   tier reqs)       │  │    with provenance │  │  ProvenanceRecord    │
  └────────────────────┘  │  - gate hook at    │  │  AgentCapabilityDecl │
                          │    REVIEW_NEXT     │  └──────────────────────┘
                          └────────────────────┘
```

## Component Responsibilities

| Component | Responsibility |
|---|---|
| `capability_routing.py` | Role→tier policy resolution, provenance building, adapter lookup |
| `agent_declarations.py` | Scan agent dirs for `tiers.json`, parse declarations, match by role+tier |
| `schemas.py` | `CapabilityTier`, `ProvenanceRecord`, `AgentCapabilityDeclaration`, `AdapterRoute`, `ROLE_CAPABILITY_POLICY` |
| `orchestrator.py` | Include tier requirements + verifier constraints in assembled prompt |
| `skill_chain.py` | Record provenance on `start_invocation`; `_gate_hook_capability_tier` at REVIEW_NEXT |
| `.agents/tiers.json` | Per-agent model candidate declaration (owned by agent platform) |

## Ownership

| Component | Owner |
|---|---|
| Harness core policy (`capability_routing.py`) | harness-governance |
| Agent declarations scanner (`agent_declarations.py`) | harness-governance |
| `tiers.json` per agent dir | Each agent platform / project |
| Gate enforcement (`skill_chain.py` hook) | harness-governance |

## Data Flow

1. User/agent installs or edits `tiers.json` in agent config dir
2. `agent_declarations.discover_declarations()` scans dirs → list of `AgentCapabilityDeclaration`
3. `capability_routing.resolve_required_tier(role, config)` → `CapabilityTier`
4. `capability_routing.resolve_adapter(role, tier, project_root)` → adapter config from declarations
5. Orchestrator embeds tier info in prompt → subagent executes
6. `SkillChainTracer.start_invocation()` records provenance (tier, adapter, model)
7. At REVIEW_NEXT gate: `_gate_hook_capability_tier` validates execution/mechanical have independent strong verifier

## ADR Candidates

1. **Agent directory declaration mechanism** — `tiers.json` format, well-known paths, discovery order (`.claude/` > `.agents/` > `.opencode/` > root). Rationale: keeps harness core platform-neutral.
2. **Gate enforcement strategy** — enforce at REVIEW_NEXT (not VERIFICATION) that execution/mechanical tier requires independent strong verifier. Rationale: REVIEW_NEXT is the final closeout gate.
