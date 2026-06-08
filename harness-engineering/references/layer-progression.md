# Harness Layer Progression

## Rule

Use this file as the source of truth for ordering local harness governance skills.

Do not infer layer order from folder names, plugin order, marketplace order, or the order of skills shown in a session.

## Canonical Progression

```text
Intake / Orientation
 ->
Idea
 ->
Fact Discovery, when material unknowns exist
 ->
Brainstorming
 ->
Brief
 ->
Architecture
 ->
ADR
 ->
Contract
 ->
Implementation Readiness
 ->
Implementation
 ->
Verification
 ->
Review / Next
```

Fact Discovery is conditional and can interrupt any layer when an unknown would otherwise become an assumption. For new external integrations, webhooks, API calls, persisted state, authentication, authorization, runtime/deployment behavior, or billing/payment behavior, material unknowns are presumed until existing durable facts or contracts prove otherwise. After recording the fact, return to the layer that needed it.

## Layer Map

| Layer label | Primary local skill | Supporting local skills | Required output before moving forward |
|---|---|---|---|
| `intake-orientation` | `harness-engineering` | `codebase-orientation`, `find-docs`, `planning-with-files` | Current repo/task context, existing queue or planning source, and known constraints. |
| `idea` | `harness-engineering` | `observable-fact-discovery` | A stable statement of the user intent or problem. |
| `fact-discovery` | `observable-fact-discovery` | `find-docs`, `codebase-orientation` | Reviewable facts, samples, probes, logs, fixtures, docs citations, or explicit unknowns. |
| `brainstorming` | `brainstorm-to-brief` | `observable-fact-discovery` | Options, tradeoffs, risks, assumptions, and non-goals. |
| `brief` | `brainstorm-to-brief` | `document-gardener` | Goal, context, non-goals, success criteria, risks, and next layer. |
| `architecture` | `architecture-boundary-design` | `implementation-detail-timing`, `observable-fact-discovery` | Boundaries, responsibilities, ownership, data flow, and ADR candidates. |
| `adr` | `adr-writing` | `architecture-boundary-design`, `document-gardener` | Decision, rationale, alternatives, consequences, and validation approach. |
| `contract` | `contract-first-development` | `contract-growth-control`, `observable-fact-discovery`, `find-docs` | Executable or reviewable contracts: schema, fixture, example, probe, API shape, check, or acceptance test. |
| `readiness` | `implementation-readiness-gate` | `implementation-detail-timing`, `contract-growth-control` | Target-local boundaries, contracts, verification commands, AGENTS.md rules, and baseline checks are known. |
| `implementation` | `implementation-readiness-gate` | `code-quality-drift-guard`, `agent-mistake-guard` | Code/config changes that stay inside approved boundaries and satisfy existing contracts. |
| `verification` | `review-next-governance` | `code-quality-drift-guard`, `harness-status-dashboard` | Fresh evidence from tests, checks, probes, screenshots, traces, or explicit failure records. |
| `review-next` | `review-next-governance` | `document-gardener`, `harness-status-dashboard`, `autonomous-ready-loop` | Done, active ready queue, blocked items, not-now items, risks, and evidence are written to stable state. |

## Cross-Cutting Skills

| Skill | Layer relationship |
|---|---|
| `skill-use-transparency` | Meta-rule before any skill selection; not a harness layer. |
| `harness-engineering` | Router and layer selector; use before choosing a layer or interpreting continue/what next. |
| `planning-with-files` | Persistence fallback when no project queue, NEXT.md, checkpoint, or repo planning system exists. |
| `autonomous-ready-loop` | Execution mode for ready queues; it selects work but must still respect the layer map. |
| `execution-prompt-authoring` | Prompt-pack authoring and audit for approved plans, gate lists, change packets, role-isolated workflows, fresh workers, subagent audits, and integrator handoffs; it is not a harness layer and does not approve scope. |
| `harness-status-dashboard` | Status/reporting view over queues, verification freshness, and long-running runs. |
| `document-gardener` | Documentation and queue hygiene after artifacts move, drift, or conflict. |
| `agent-mistake-guard` | Guardrail capture when repeated AI mistakes need durable prevention. |
| `code-quality-drift-guard` | Implementation and verification guard against sprawl, duplicate helpers, orphan checks, and naming drift. |
| `debugging-checklist` | Human handoff fallback, not the primary agent debugging workflow when a stronger workflow is available. |

## Execution Mode Routing

Execution modes do not create new harness layers. They decide how work at the current layer is executed.

| Mode | Scope | When to use | Must not do |
|---|---|---|---|
| `manual` | Current chat or session | Human is actively steering, or the task is small enough to finish in one session. | Do not treat chat-only results as durable artifacts. |
| `autonomous` | Queue-driven fresh `codex exec` workers | Work should continue across short workers from NEXT, TODO, backlog, issue queues, or checkpoints. | Do not bypass layer progression, readiness gates, checkpointing, or autonomous stop markers. |
| `subagent-driven` | Inside one implementation session or autonomous worker | Current layer is `implementation`, readiness has passed, and implementation task packets are complete. | Do not consume raw NEXT, TODO, backlog, or checkpoint ready items directly. |
| `prompt-pack-authoring` | Approved work that needs self-contained execution prompts | A plan, gate list, queue item, change packet, or role-isolated workflow needs controller, worker, auditor, or integrator prompts before execution. | Do not treat prompt packs as scope approval, readiness evidence, or final verification. |

`autonomous-ready-loop` is an execution mode for selecting and running ready layer work. `superpowers:subagent-driven-development` is an implementation execution mode used only after readiness and packetization.
`execution-prompt-authoring` prepares the prompts and execution matrix for workers, subagent audits, controllers, and integrators; it does not create a new harness layer.

## Transition Rules

1. Do not enter `implementation` before `readiness` unless the user explicitly asks for a throwaway prototype or the target project already supplies equivalent readiness rules.
2. A request to move fast, implement now, or finish the real integration is not a throwaway prototype request. Persisted data, external side effects, public contracts, or production runtime behavior exclude the prototype exception unless the user explicitly scopes the work as isolated throwaway exploration.
3. Do not enter `contract` before `architecture` or `adr` when the contract would freeze ownership, deployment, persistence, or boundary decisions.
4. ADR or decision state must be durable and reviewable. Chat-only agreement does not satisfy a layer exit condition when long-lived boundaries, persistence, deployment, ownership, or public contracts are involved.
5. When a material unknown appears, move to `fact-discovery`, record evidence, then return to the blocked layer.
6. When contract/check/readiness work repeats without implementation progress, use `contract-growth-control`.
7. When implementation reveals uncontracted behavior, return to `contract` before expanding product behavior.
8. When verification fails, return to the lowest layer that owns the failure cause.
9. When work finishes or pauses, always enter `review-next` to record evidence, risks, and next ready layer.

## Queue Layer Labels

Use these exact labels in queue items, dashboards, and handoffs:

```text
intake-orientation
idea
fact-discovery
brainstorming
brief
architecture
adr
contract
readiness
implementation
verification
review-next
```

If a task spans multiple layers, record the current blocking layer first and mention later layers in notes.
