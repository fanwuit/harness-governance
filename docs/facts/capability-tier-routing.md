# Facts: P0 Capability-Tiered Subagent Routing

## Known Facts

1. **CapabilityTier enum** defined: `strong`, `execution`, `mechanical`
2. **ROLE_CAPABILITY_POLICY** defines default role→tier mapping:
   - planner/contract-writer/verifier/reviewer → strong
   - implementer → execution
   - document-gardener → mechanical
3. **capability_routing.py** implements policy resolution, provenance building, adapter resolution
4. **SkillInvocation** extended with 9 provenance fields (required_tier, actual_tier, platform, model_label, adapter, verifier_required, owner_files, changed_files)
5. **Orchestrator prompt** includes capability tier requirements + verifier constraints
6. **Gate hook** registered at REVIEW_NEXT: enforces execution/mechanical cannot self-verify
7. **Agent declarations** (`tiers.json`): per-agent directory model candidate declarations
   - Scanned from `.claude/`, `.agents/`, `.clinerules/`, `.cursor/`, `.opencode/`, `.windsurf/`, project root
   - Harness core never encodes model rankings

## Assumptions / Risks

Assumption: Role→tier default policy covers standard governance workflows.
Risk: Custom roles not in ROLE_CAPABILITY_POLICY default to STRONG, which may be unnecessarily strict.

Assumption: Agent directory `tiers.json` is the right mechanism for model candidate declaration.
Risk: Projects with no agent directories will have no adapter declarations, defaulting to platform-generic behavior.

Assumption: Gate hook at REVIEW_NEXT is sufficient enforcement point.
Risk: No enforcement at VERIFICATION layer could let self-verified work slip through.

## Task Type

Feature — new capability-tier routing subsystem.

## One-Line Intent

定义能力层级（strong/execution/mechanical）并强制执行验证分离：通过 agent 目录自动发现（tiers.json）暴露模型候选，execution/mechanical 不能自验证。
