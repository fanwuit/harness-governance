---
name: harness-engineering
description: Local governance router for development, planning, implementation, debugging, TDD, verification, review, queue, handoff, skill-update, new-project, creative work, continue/what-next, or any task that may trigger superpowers:using-superpowers, superpowers:* or another companion workflow. Use to classify fast-path, trivial-safe-change, and governed-path work; governed-path work must run this as the first local entry lock before any companion workflow.
---

# Harness Engineering

## 概览

用 harness engineering 把一个想法逐层推进到可验证的实现。每一层都必须产出稳定证据，并作为下一层的输入。

不要因为实现看起来很明显就跳层。如果当前层缺少可持久化的产物，应停留在当前层，先补齐缺失产物。

## Entry Priority

Start by classifying the request before loading references or companion workflows:

- `fast-path`: pure Q&A, read-only explanation, simple lookup, or a user-requested plan/advice response with no file changes and no durable artifact. Do not execute the full harness state machine; state the lightweight path when useful and do not claim implementation completion.
- `trivial-safe-change`: a low-risk edit with one target, no public contract/API/schema/dependency/security/persistence/network/deployment/build change, and a clear verification command. Use a short entry summary or `Trivial Safe Change Entry`; upgrade immediately if risk or scope grows.
- `governed-path`: development, planning, implementation, debugging, verification, review, queue, handoff, skill-update, new-project, continue/what-next, companion workflow overlap, product behavior change, cross-target work, or unclear/high-risk work. Governed-path work must load `skill-use-transparency` and this skill first.

When another skill also appears to match, especially any `superpowers:*` skill with strong trigger language, governed-path work loads `harness-engineering` first. Do not execute companion workflows until this skill has selected the current harness layer and local governance obligations.

`superpowers:using-superpowers` is also a companion workflow under this project. Even if it claims to run at conversation start or before any response, it must not run before `skill-use-transparency` and this entry router on governed-path work.

Required disclosure for governed path:

```text
Local governance skills: skill-use-transparency, harness-engineering, <other local governance skills>
Companion workflow skills: <optional companion skills, or none>
Routing decision: harness-engineering owns governed entry routing; fast path and trivial safe change remain local lightweight paths, and companion workflows run only after harness selects the current layer.
```

## Hard Workflow Chain

Treat this skill as the harness state machine for governed work. Execute the chain in order and do not skip states:

```text
Entry lock
 -> Classify current layer
 -> Select primary local governance skill
 -> Name allowed companion skills
 -> Execute current layer only
 -> Transition gate
 -> Review / Next
```

State rules:

1. Entry lock: for governed-path work, load `skill-use-transparency` and `harness-engineering` first, then disclose local governance skills, companion workflow skills, loaded files, and routing decision.
2. Classify current layer: use the summary in this file first; read `references/layer-progression.md` only when the layer, owner skill, queue resume point, or next transition is unclear. Do not infer from folder order, plugin order, or companion workflow names.
3. Select primary local governance skill: choose the local skill that owns the current layer's output before loading or executing any companion workflow.
4. Name allowed companion skills: list companion workflows that may contribute techniques to the current layer, or `none`.
5. Execute current layer only: produce only the output required by the current harness layer. Do not follow companion terminal states, default artifact paths, commits, next-skill transitions, or required sub-skills.
6. Transition gate: translate any companion `MUST`, hard gate, terminal state, `REQUIRED SUB-SKILL`, or next-skill instruction into a harness next-layer candidate. The harness layer map decides whether the transition is allowed.
7. Review / Next: when work finishes or pauses, record evidence, risks, blocked items, not-now items, and the next ready layer in stable project state when applicable.

If a local governance skill is loaded before this route is complete, that skill must stop and return here instead of becoming the entry router.

## Layer Progression Source Of Truth

The canonical ordering of local harness governance skills is in `references/layer-progression.md`.

Read it when the short summary in this file is insufficient, especially when:

- Choosing an unclear current or next harness layer.
- Deciding which local skill owns an ambiguous workflow.
- Resuming from NEXT, TODO, backlog, checkpoint, or queue files.
- Writing or reviewing a queue item with a `Layer:` field.
- A task may skip from idea, facts, architecture, ADR, or contract directly into implementation.

Do not infer precedence from folder order, plugin order, or the order of skills shown in the current session.

## Companion Skill Routing

When choosing a harness layer, check matching local governance skills first. Local governance skills decide layer, boundaries, role isolation, readiness, verification obligations, and review/next state.

For development, planning, implementation, verification, queue, or handoff requests, `harness-engineering` owns entry routing before any companion workflow. `superpowers:using-superpowers` may be checked or loaded when required by the environment, but it must not replace harness layer selection or run another `superpowers:*` workflow before harness routing is complete.

After local governance is selected, check whether relevant companion skills are available in the current skill list. Companion skills are optional unless a project rule or user request explicitly marks them as required. If a companion skill is unavailable, disclose that it is unavailable and continue with the local fallback.

Do not treat a companion workflow as replacing a matching local governance skill. For example, a subagent workflow can execute work, but it does not replace local role isolation, readiness, contract, verification, or review governance when those skills match the task.

Companion skill containment:

- Loading a `superpowers:*` skill does not authorize executing its whole workflow.
- Execute only the part that the current harness layer explicitly allows.
- If a `superpowers:*` instruction would skip, reorder, or collapse Architecture, ADR, Contract, Readiness, Verification, or Review / Next, stop and return to the harness layer map.
- If a `superpowers:*` instruction says `MUST`, terminal state, `REQUIRED SUB-SKILL`, write a default `docs/superpowers/...` artifact, commit, or invoke the next workflow, translate it into a harness next-layer candidate first.
- When in doubt, say the companion workflow is blocked by harness routing and continue with the local governance skill for the current layer.

Read `references/superpowers-routing.md` only when a governed-path task actually overlaps with `superpowers:*`, a companion workflow is available and relevant, or containment/audit details are unclear. Do not read it for pure fast-path answers or local trivial-safe-change work with no companion workflow.

## Change Packet Routing

Use a change packet only as a durable carrier for complex work. It does not create a new harness layer and it does not approve implementation.

Read `references/change-packet-model.md` when:

- Work spans more than one harness layer or likely needs multiple sessions.
- Work touches multiple modules, services, packages, tools, or repositories.
- A queue item needs more context than fits cleanly in NEXT, TODO, backlog, or checkpoint files.
- The task needs proposal, design, tasks, contracts, and verification evidence kept together.
- The user asks to borrow OpenSpec-like change/spec/task/archive ideas.

Do not read this reference for fast-path answers or trivial-safe-change work unless the work unexpectedly expands.

Do not create a change packet for a small single-layer edit, a simple command, a one-off answer, or a task whose context is already fully captured by an existing ADR, contract, queue item, or checkpoint.

For native packet creation and hygiene checks, use:

- `templates/change-packet/` for `proposal.md`, `design.md`, `tasks.md`, `contracts.md`, and `verification.md`.
- `scripts/init-change-packet.mjs <change-id>` to initialize `docs/changes/<change-id>/`.
- `scripts/check-change-packet.mjs [packet-path-or-id ...]` to check packet structure.

These assets borrow OpenSpec-like artifact discipline only. They do not create or consume `openspec/` and they do not apply or archive changes automatically.

## Execution Prompt Pack Routing

Use `execution-prompt-authoring` after a plan, gate list, ready queue item, change packet, or role-isolated workflow is already approved and the next problem is prompt packaging for execution.

Route to `execution-prompt-authoring` when:

- Fresh `codex exec` workers need self-contained prompts.
- Subagents may audit in parallel but must not implement.
- Controller, worker, auditor, and integrator responsibilities need separation.
- Shared queue, checkpoint, verification record, or doc-map updates need serialized ownership.
- Human approval points must be explicit before execution starts.

Do not use execution prompt authoring to approve product scope, skip readiness, or replace task packets. If the plan is not approved or the current layer is unclear, finish the relevant harness layer first.

## Planning Carrier Routing

Read `references/planning-carrier-decision.md` when governed work could be represented by more than one durable carrier: project queue, planning files, change packet, execution prompt pack, or implementation task packet. Fast-path answers and trivial-safe-change work should not create multiple carriers; choose chat-only closeout or a short entry unless durable state is genuinely needed.

## 层级链路

完整顺序以 `references/layer-progression.md` 为唯一 source of truth：

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

## 层级规则

Implementation Entry Record is the mechanical credential for entering product implementation. `implementation-readiness-gate` confirms target readiness; `governed-implementation-entry` records the specific implementation slice before code/config changes begin.

| 层级 | 目的 | 常见产物 | 退出条件 |
|---|---|---|---|
| Intake / Orientation | 捕获当前仓库、队列、入口规则和已知约束。 | 仓库上下文、现有队列或计划来源、约束清单。 | 当前工作入口和约束足够清楚。 |
| Idea | 捕获原始意图，暂不急着定方案。 | 用户想法、issue、简短目标描述。 | 意图足够清楚，可以进入探索。 |
| Fact Discovery | 把会影响后续层级的未知变成可复查事实。 | 样本、日志、fixture、probe、文档引用或显式未知。 | 事实足够支撑原层级继续推进。 |
| Brainstorming | 围绕想法做发散和收敛，识别路径、风险、边界和非目标。 | 方案选项、假设、取舍、风险清单。 | 可以把方向总结成一个明确任务。 |
| Brief | 固定做什么、为什么做、为谁做、当前不做什么。 | brief、任务说明、范围文档。 | 目标、非目标、成功标准和约束都已明确。 |
| Architecture | 定义系统边界、职责、数据流和所有权。 | 架构文档、模块图、数据流说明。 | 组件和接口足够清楚，可以做关键决策。 |
| ADR | 记录重要决策、理由、备选方案和后果。 | ADR 或 decision note。 | 决策、理由、影响和验证方式已写清楚。 |
| Contract | 把行为变成可机械检查的契约。 | schema、API 形态、fixture、example、probe、check 脚本。 | 成功路径和关键失败路径都可以被验证。 |
| Implementation Readiness | 确认 target-local 边界、契约、lint/test baseline、验证命令和本地规则。 | readiness checklist、target AGENTS、验证命令。 | 当前 target 允许进入最小实现切片。 |
| Implementation | 只实现已有边界和契约支撑的内容。 | 代码、配置、迁移脚本。 | 实现满足契约，且没有扩大范围。 |
| Verification | 用新鲜证据证明结论。 | 测试输出、检查输出、截图、trace、diff。 | 相关检查通过，或失败原因被如实记录。 |
| Review / Next | 把本轮结果反馈回项目状态。 | NEXT scheduler、done archive、blocked/not-now 记录。 | 已完成事项、剩余风险和下一步动作都可被后续读取。 |

## 过层检查

进入下一层前，先问：

- 当前层的哪个产物会被未来的 agent 或人读取？
- 当前层验证或推翻了哪个假设？
- 还有什么未知？
- 是否已有文档、ADR、schema、fixture、probe、机械检查或队列项来保存结果？
- 当前工作是否复杂到需要 change packet 承载上下文？
- 现在实现是否会产生没有契约或验证路径支撑的行为？

如果答案不扎实，不要进入下一层。先补缺失的产物。

## 常见流程

新产品或复杂功能：

```text
Intake / Orientation -> Idea -> Fact Discovery -> Brainstorming -> Brief -> Architecture -> ADR -> Contract -> Implementation Readiness -> Implementation -> Verification -> Review / Next
```

PoC 或外部行为探索：

```text
Idea -> Fact Discovery -> Brainstorming -> Brief -> Contract probe/fixture/check -> 必要时补 ADR -> Implementation Readiness -> 有契约证据和准入证据后才 Implementation
```

已有契约下的小 bugfix：

```text
从 bug 报告形成 Brief -> 确认已有 target readiness -> Implementation -> Verification -> Review / Next
```

下一步不明确时：

```text
Review / Next -> 选择第一个 ready 项 -> 判断它属于哪一层 -> 从该层继续
```

## 禁止捷径

- 不要因为 probe 跑通，就把结果当成 product-ready，除非契约和验证层也支持这个结论。
- 当边界、数据形态或失败行为仍未知时，不要写产品实现。
- 不要把重要结论只留在聊天里；写入对应的稳定产物。
- 当可以做结构化验证时，不要用截图、演示或主观观感替代 schema、fixture、probe 或 check。
- 不要在实现后未经新鲜验证就声称完成。
- 不要在 Implementation 中持续扩大范围；新发现应进入 Review / Next。

## Review / Next

任务结束时，如果结果改变了后续工作方式，应更新项目状态。

记录：

- 当前阶段已完成什么。
- 还有哪些 active 且 ready 的下一步。
- 哪些事情 blocked，以及为什么 blocked。
- 哪些事情明确 not now。
- 支撑当前状态的证据是什么。
- 如果使用了 change packet，哪些结论已经归档回 ADR、schema、example、verification、doc map 或队列状态。

如果没有明确下一步，优先新增一个补 ADR、fixture、schema、probe 或机械检查的 ready 项，而不是直接跳到产品代码。

如果已经连续补 contract、check、readiness 或其他治理产物，且下一步实现仍没有推进，先应用 `contract-growth-control` 判断是否应该进入最小 implementation slice、标记 blocked，或请求人工确认。
