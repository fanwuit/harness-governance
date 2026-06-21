# Design: capability-tier-routing

## Boundaries

- Owned files / modules:
  - `src/harness_governance/models/schemas.py`
  - `src/harness_governance/state_machine/capability_routing.py`
  - `src/harness_governance/state_machine/agent_declarations.py`
  - `src/harness_governance/state_machine/skill_chain.py`
  - `src/harness_governance/runner/orchestrator.py`
  - `src/harness_governance/commands/runner.py`
  - `src/harness_governance/runner/adapters/registry.py`
- Forbidden paths:
  - Provider-specific model ranking in harness core.
  - Release/deploy automation.
- Runtime or process boundary:
  - Harness resolves capability requirements and records provenance.
  - Platform adapters expose candidates but own concrete model/tool selection.

## Responsibilities

- `capability_routing.py`: role-to-tier policy, verifier requirement, adapter resolution helpers.
- `agent_declarations.py`: discover and parse per-agent `tiers.json` files.
- `schemas.py`: capability tier, route declaration, and invocation provenance models.
- `skill_chain.py`: persist provenance and enforce independent strong verifier closeout.
- `runner/orchestrator.py` and `commands/runner.py`: surface required tiers in prompts and metadata.

## Data Or Control Flow

1. Role is selected by runner/orchestrator.
2. Harness resolves the required capability tier from default policy or config override.
3. Agent declarations are searched for a matching role/tier adapter candidate.
4. Prompt metadata includes capability requirements and verifier constraints.
5. Invocation provenance records required/actual tier and changed-file context.
6. Review/Next gate rejects lower-tier work without an independent strong verifier.

## Alternatives Considered

- Hard-code provider/model rankings in core: rejected because it breaks platform neutrality.
- Only keep Subagent Separation document checks: rejected because it does not express role capability requirements.
- Require every role to be strong: rejected because it prevents bounded lower-cost execution.

## ADR Candidates

- Required ADR / decision note: `docs/adr/agent-directory-declarations.md`, `docs/adr/capability-tier-gate-enforcement.md`.
- Not needed because: additional provider-specific ADRs are deferred until a provider adapter changes behavior.

## Harness Constraints

- Capability routing cannot let execution/mechanical roles approve their own work.
- Adapter selection must remain platform-neutral in harness core.
- Review/Next closeout is the enforcement point for independent verifier evidence.
