# Harness Layer Progression / Harness 层级推进

> **Note (v0.7.1):** The "skill" names in this document (e.g. `harness-engineering`,
> `brainstorm-to-brief`) are **internal role labels** used by the state machine
> (`layers.py` `LAYER_MAP`) for template rendering and orchestrator dispatch.
> They are NOT loadable SKILL.md files. End users interact via CLI commands:
> `harness governed-start`, `harness layer advance`, `harness gate check`.

> **注意 (v0.7.1)：** 本文档中的"skill"名称（如 `harness-engineering`、`brainstorm-to-brief`）是状态机（`layers.py` `LAYER_MAP`）用于模板渲染和编排器调度的**内部角色标签**。它们不是可加载的 SKILL.md 文件。最终用户通过 CLI 命令交互：`harness governed-start`、`harness layer advance`、`harness gate check`。

## Rule / 规则

Use this file as the source of truth for ordering local harness governance skills.

将此文件作为本地 harness 治理技能排序的真相来源。

Do not infer layer order from folder names, plugin order, marketplace order, or the order of skills shown in a session.

不要从文件夹名称、插件顺序、市场顺序或会话中显示的技能顺序推断层级顺序。

## Canonical Progression / 标准推进

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

Fact Discovery 是条件性的，当未知事物否则会变成假设时，可以中断任何层。对于新的外部集成、webhook、API 调用、持久化状态、认证、授权、运行时/部署行为或计费/支付行为，在现有持久化事实或契约证明之前，均推定存在实质性未知。记录事实后，返回需要它的层。

## Layer Map / 层级映射

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
| `readiness` | `implementation-readiness-gate` | `implementation-detail-timing`, `contract-growth-control`, `governed-implementation-entry` | Target-local boundaries, contracts, verification commands, AGENTS.md rules, baseline checks, and the Implementation Entry Record are known. |
| `implementation` | `governed-implementation-entry` | `implementation-readiness-gate`, `code-quality-drift-guard`, `agent-mistake-guard` | Implementation Entry Record exists as the mechanical credential for code/config changes that stay inside approved boundaries and satisfy existing contracts. |
| `verification` | `review-next-governance` | `code-quality-drift-guard`, `harness-status-dashboard` | Fresh evidence from tests, checks, probes, screenshots, traces, or explicit failure records. |
| `review-next` | `review-next-governance` | `document-gardener`, `harness-status-dashboard`, `autonomous-ready-loop` | Done archive, scheduler ready queue, blocked items, not-now items, risks, and evidence are written to stable state. |

## Cross-Cutting Skills / 横切技能

> These are internal role labels for the state machine and orchestrator.
> At runtime, classification is handled by `harness governed-start`,
> not by loading a separate skill file.

> 这些是状态机和编排器的内部角色标签。
> 运行时，分类由 `harness governed-start` 处理，
> 而非加载单独的 skill 文件。

| Skill | Layer relationship |
|---|---|
| `skill-use-transparency` | Meta-rule before any skill selection; not a harness layer. |
| `harness-engineering` | Router and layer selector; now implemented as `harness governed-start` CLI command. |
| `planning-with-files` | Persistence fallback when no project queue, NEXT.md, checkpoint, or repo planning system exists. |
| `autonomous-ready-loop` | Execution mode for ready queues; it selects work but must still respect the layer map. |
| `execution-prompt-authoring` | Prompt-pack authoring and audit for approved plans, gate lists, change packets, role-isolated workflows, fresh workers, subagent audits, and integrator handoffs; it is not a harness layer and does not approve scope. |
| `harness-status-dashboard` | Status/reporting view over queues, verification freshness, and long-running runs. |
| `document-gardener` | Documentation and queue hygiene after artifacts move, drift, or conflict. |
| `agent-mistake-guard` | Guardrail capture when repeated AI mistakes need durable prevention. |
| `code-quality-drift-guard` | Implementation and verification guard against sprawl, duplicate helpers, orphan checks, and naming drift. |
| `debugging-checklist` | Human handoff fallback, not the primary agent debugging workflow when a stronger workflow is available. |

## Execution Mode Routing / 执行模式路由

Execution modes do not create new harness layers. They decide how work at the current layer is executed.

执行模式不会创建新的 harness 层。它们决定当前层的工作如何执行。

| Mode | Scope | When to use | Must not do |
|---|---|---|---|
| `manual` | Current chat or session | Human is actively steering, or the task is small enough to finish in one session. | Do not treat chat-only results as durable artifacts. |
| `autonomous` | Queue-driven fresh agent workers (subprocess or orchestrator) | Work should continue across short workers from NEXT, TODO, backlog, issue queues, or checkpoints. | Do not bypass layer progression, readiness gates, checkpointing, or autonomous stop markers. |
| `subagent-driven` | Inside one implementation session or autonomous worker | Current layer is `implementation`, readiness has passed, and implementation task packets are complete. | Do not consume raw NEXT, TODO, backlog, or checkpoint ready items directly. |
| `prompt-pack-authoring` | Approved work that needs self-contained execution prompts | A plan, gate list, queue item, change packet, or role-isolated workflow needs controller, worker, auditor, or integrator prompts before execution. | Do not treat prompt packs as scope approval, readiness evidence, or final verification. |

`autonomous-ready-loop` is an execution mode for selecting and running ready layer work. `superpowers:subagent-driven-development` is an implementation execution mode used only after readiness and packetization. `execution-prompt-authoring` prepares the prompts and execution matrix for workers, subagent audits, controllers, and integrators; it does not create a new harness layer.

`autonomous-ready-loop` 是用于选择和运行就绪层工作的执行模式。`superpowers:subagent-driven-development` 是仅在 readiness 和 packetization 之后使用的实现执行模式。`execution-prompt-authoring` 为 worker、subagent 审计、controller 和 integrator 准备提示词和执行矩阵；它不创建新的 harness 层。

Implementation Entry Record is the mechanical credential for entering product implementation. A readiness pass alone is not sufficient; the record must name target, scope, contract evidence, readiness state, packetization, verification, Review / Next state, and stop conditions before implementation changes begin.

Implementation Entry Record 是进入产品实现的机械凭证。仅通过 readiness 是不够的；记录必须在实现变更开始之前命名目标、范围、契约证据、就绪状态、packetization、验证、Review / Next 状态和停止条件。

## Transition Rules / 转换规则

1. Do not enter `implementation` before `readiness` unless the user explicitly asks for a throwaway prototype or the target project already supplies equivalent readiness rules. / 在 `readiness` 之前不要进入 `implementation`，除非用户明确要求一次性原型，或目标项目已提供等效的 readiness 规则。
2. A request to move fast, implement now, or finish the real integration is not a throwaway prototype request. Persisted data, external side effects, public contracts, or production runtime behavior exclude the prototype exception unless the user explicitly scopes the work as isolated throwaway exploration. / 要求快速推进、立即实现或完成真正集成的请求不是一次性原型请求。持久化数据、外部副作用、公共契约或生产运行时行为排除了原型例外，除非用户明确将工作范围限定为隔离的一次性探索。
3. Do not enter `contract` before `architecture` or `adr` when the contract would freeze ownership, deployment, persistence, or boundary decisions. / 当契约会冻结所有权、部署、持久化或边界决策时，不要在 `architecture` 或 `adr` 之前进入 `contract`。
4. ADR or decision state must be durable and reviewable. Chat-only agreement does not satisfy a layer exit condition when long-lived boundaries, persistence, deployment, ownership, or public contracts are involved. / ADR 或决策状态必须是持久化和可审查的。当涉及长期边界、持久化、部署、所有权或公共契约时，仅聊天中的协议不满足层退出条件。
5. When a material unknown appears, move to `fact-discovery`, record evidence, then return to the blocked layer. / 当出现实质性未知时，移至 `fact-discovery`，记录证据，然后返回被阻塞的层。
6. When contract/check/readiness work repeats without implementation progress, use `contract-growth-control`. / 当契约/检查/就绪工作重复而没有实现进展时，使用 `contract-growth-control`。
7. When implementation reveals uncontracted behavior, return to `contract` before expanding product behavior. / 当实现揭示未契约化的行为时，在扩展产品行为之前返回 `contract`。
8. When verification fails, return to the lowest layer that owns the failure cause. / 当验证失败时，返回拥有失败原因的最低层。
9. When work finishes or pauses, always enter `review-next` to record evidence, risks, and next ready layer. / 当工作完成或暂停时，始终进入 `review-next` 以记录证据、风险和下一个就绪层。

## Queue Layer Labels / 队列层标签

Use these exact labels in queue items, dashboards, and handoffs:

在队列项、仪表板和交接中使用这些精确标签：

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

如果任务跨越多个层，首先记录当前阻塞层，并在备注中提及后续层。
