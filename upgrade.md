# Harness-Governance Upgrade Roadmap

This file is the short, current roadmap. Historical detail and completed design
notes are archived in [docs/upgrade-archive.md](docs/upgrade-archive.md).

## Current Priority

### P0. Capability-Tiered Subagent Routing

**Status:** first version done.

**Goal:** make subagent execution platform-neutral while allowing cheaper or
weaker execution agents to work only inside explicit boundaries and requiring
independent strong verification before closeout.

**Why first:**
- Subagent Separation Gate already checks for role evidence, but it does not
  decide when to dispatch subagents or what capability tier each role needs.
- The product must stay platform-independent; harness should not encode
  Codex-, Claude-, OpenCode-, or provider-specific model rankings.
- This creates the execution-side foundation for later auto-dispatch.

**Core design:**

```text
role -> required capability tier -> platform adapter -> project-confirmed model/tool
```

Required first version:
- Define platform-neutral capability tiers: `strong`, `execution`, `mechanical`.
- Define role policy: planner/contract/verifier use `strong`; implementer may use
  `execution`; document-gardener may use `mechanical`.
- Record invocation provenance: role, required tier, actual tier, platform,
  opaque model label, owner files, changed files, verifier requirement.
- Enforce that `execution` / `mechanical` work cannot close itself; an independent
  `strong` verifier must accept it.
- Keep platform model selection outside harness core. Platform adapters expose
  candidates; project config confirms tier mapping.

**Primary implementation areas:**
- `src/harness_governance/models/schemas.py`
- `src/harness_governance/config/settings.py`
- `src/harness_governance/runner/template_renderer.py`
- `src/harness_governance/runner/orchestrator.py`
- `src/harness_governance/runner/adapters/`
- `src/harness_governance/state_machine/skill_chain.py`
- `src/harness_governance/state_machine/gates.py`
- `tests/test_subagent_runner/`
- `tests/test_state_machine/test_skill_chain.py`

## Next Priority

### P0. Hybrid Routing + Author-Answer Provenance

**Status:** first version done (v0.9.0).

**Goal:** avoid routing ordinary questions into 12-layer governance while making
sure Author Questions cannot be satisfied by agent self-answers.

Required first version:
- ✅ Treat agent route recommendation as advisory; deterministic policy decides
  from structured facts.
- ✅ Force `question` / `read_only` / no-write work to `fast-path` unless a
  hard governed override applies.
- ✅ Add answer provenance to `layer_qa`: `author`, `agent_inference`,
  `author_imported`.
- ✅ Make gates count only `source=author` for Author Questions.
- ✅ Report ignored agent inferences in gate output.
- ✅ Require `--confirmed` for standard/strict layer advancement.

Primary implementation areas:
- `src/harness_governance/models/schemas.py`
- `src/harness_governance/state_machine/classification.py`
- `src/harness_governance/commands/governed_start.py`
- `src/harness_governance/session/state.py`
- `src/harness_governance/commands/layer.py`
- `src/harness_governance/state_machine/gates.py`
- `tests/STATE_CONTRACTS.md`

## Completed Or Stable Items

These remain important but are no longer the active implementation focus:

| Priority | Item | Status |
|---|---|---|
| P0 | Red flag guidance for gate failures | Done |
| P0 | User-Perceived Integration Evidence Gate | Done, with artifact scanning enhancement |
| P0 | Subagent Separation Gate | First version done: document-level evidence check |
| P1 | State Contract Closure | Done, including state-contract check and auto scan |
| P1 | Tag-only Release Verification Hook | First version done |
| P1 | Agent Preflight Assessment | First version done |
| P1 | NEXT.md Queue Closure | First version done |
| P1 | Governance UX Friction Reduction | Mostly done: ask/wizard/guidance improvements |
| P2 | Spec Quick | Done: `quick`, `list`, and `upgrade` |
| P3 | Quickstart guidance | Done |

## Backlog

- ✅ Add `harness ship` hints for release verification.
- ✅ Decide whether `harness init --tier light` should exist beyond `--minimal` — implemented `harness init --tier <tier>`.
- ✅ Document platform slash-command triggers in generated skills where applicable.
- ✅ Implement `spec quick` if lightweight specs become a repeated need — `quick`, `list`, and `upgrade` are done.

## Archive

The previous long-form roadmap, including detailed rationale and historical
implementation notes, is preserved at:

- [docs/upgrade-archive.md](docs/upgrade-archive.md)
