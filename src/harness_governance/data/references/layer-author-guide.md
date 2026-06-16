# Layer Author Interaction Guide / 层作者交互指南

When the agent enters a layer, this guide tells it HOW to interact with the
human author — what questions to ask, how to present options, where to record
decisions, and what to confirm before advancing.

当 agent 进入某一层时，本指南告诉它如何与人类作者交互——该问什么、怎么呈现选项、
决策记录到哪里、推进前确认什么。

---

## intake-orientation

### 目的 / Purpose
建立仓库/任务上下文，识别已有队列或规划来源，在开始工作前明确已知约束。
Establish repo/task context, identify the active queue or planning source,
and surface known constraints before any work begins.

### 作者问题 / Author Questions
1. 当前的任务或目标是什么？ / What is the current task or goal?
2. 是否有现有队列（NEXT.md、TODO、backlog、issue tracker）？ / Is there an existing queue?
3. 有哪些已知的约束或风险？ / Are there known constraints or risks?
4. 这是之前工作的延续，还是新任务？ / Continuation or new task?

### 交互模式 / Interaction Pattern
展示路由决定和依据。一次只问一个问题——不要同时问四个。从#1开始，如果看不到队列再问#2。
Present routing decision with rationale. One question at a time — never ask
all four at once. Start with #1, then #2 if no queue is visible.

### 产出物 / Artifact
通过 `harness governed-start` 生成 `.harness/sessions/<id>.json`。
如果没有队列，搭建 `NEXT.md` 或规划文件。原样输出披露块。
Session state in `.harness/sessions/<id>.json` via `harness governed-start`.
If no queue exists, scaffold a `NEXT.md` or planning file.

### 确认门控 / Confirmation Gate
- [ ] 路由决定已被明确确认 / Routing decision explicitly acknowledged
- [ ] 当前层已说明并理解 / Current layer stated and understood
- [ ] 竞争 skill 警告已检查 / Competing skill warnings reviewed (if any)
- [ ] Session ID 已记录 / Session ID recorded

### 禁止 / Forbidden
- 禁止在输出披露块之前开始工作 / Do NOT start work before the disclosure block is output
- 禁止跳过 `harness governed-start` / Do NOT skip `harness governed-start`
- 禁止从 skill 名称或目录结构推断层顺序 / Do NOT infer layer order from skill names
- 禁止自动创建分支、提交或 worktree / Do NOT auto-create branches, commits, or worktrees

---

## idea

### 目的 / Purpose
将用户意图稳定为一句话，可在后续分析前被评审。
Stabilise the user's intent into a single, reviewable sentence before any analysis.

### 作者问题 / Author Questions
1. 你能用一句话描述核心问题或意图吗？ / Can you state the core problem in one sentence?
2. 这是功能需求、bug 修复、重构、调查，还是其他？ / Feature, bug fix, refactor, investigation, or other?

### 交互模式 / Interaction Pattern
回显一个拟议的一句话摘要，问"这个准确吗？"帮助提炼长描述。在确认之前不往前推进。
Echo back a proposed one-line summary and ask "Is this accurate?" Do not move
forward until confirmed.

### 产出物 / Artifact
Session 中的稳定意图或 `docs/ideas/<slug>.md`。如果使用变更包：`docs/changes/<id>/proposal.md`。
Stable intent in the session or `docs/ideas/<slug>.md`. If using change packets:
`docs/changes/<id>/proposal.md`.

### 确认门控 / Confirmation Gate
- [ ] 一句话意图陈述已由作者明确批准 / One-line intent explicitly approved
- [ ] 任务类型已达成一致 / Task type agreed
- [ ] 作者提出的任何非目标已记录 / Any known non-goals noted

### 禁止 / Forbidden
- 禁止在意图书稳定之前开始研究、事实发现或头脑风暴 / Do NOT begin research before intent is stable
- 禁止将用户意图改写为对方没有要求的内容 / Do NOT rewrite the user's intent

---

## fact-discovery

### 目的 / Purpose
收集可评审的事实，或明确声明未知事项，防止它们变成隐藏假设。
Gather reviewable facts or explicitly declare unknowns before they become hidden assumptions.

### 作者问题 / Author Questions
1. 有哪些特定的文件、日志、API 或文档我应该先查看？ / Specific files, logs, APIs, or docs to examine first?
2. 有哪些已知的未知——我们已经知道我们不知道的事情？ / Known unknowns?
3. 你能指给我哪些现有的证据？ / What existing evidence can you point to?

### 交互模式 / Interaction Pattern
列出发现和剩余未知事项。对每个未知使用"假设 / 风险"块：
```
假设 / Assumption: <当前保守假设>
风险 / Risk: <如果假设错误会怎样>
```
逐一呈现每个未知事项；问"你能确认或纠正这个吗？"
List findings and remaining unknowns. Use Assumption/Risk blocks. Present each
unknown individually; ask "Can you confirm or correct this?"

### 产出物 / Artifact
事实记录在 `docs/facts/<slug>.md`。明确的未知列表含假设/风险块。
引用外部文档、日志或 fixtures。
Facts in `docs/facts/<slug>.md`. Explicit unknowns with Assumption/Risk blocks.
Citations to external docs, logs, or fixtures.

### 确认门控 / Confirmation Gate
- [ ] 所有实质性未知事项要么已有证据解决，要么已明确声明为假设 / All material unknowns resolved or declared
- [ ] 作者已检查并接受假设/风险块 / Author reviewed Assumption/Risk blocks
- [ ] 结果已写入持久化位置（非仅聊天） / Results written to durable location

### 禁止 / Forbidden
- 禁止在存在实质性未知时跳过事实发现（T5 规则） / Do NOT skip fact discovery when material unknowns exist (T5)
- 禁止未经作者确认就把假设当事实 / Do NOT treat an assumption as a fact
- 禁止在未解决未知的情况下进入方案设计 / Do NOT proceed with unresolved unknowns

---

## brainstorming

### 目的 / Purpose
生成并比较选项，含结构化权衡、风险和假设。
Generate and compare options with structured tradeoffs, risks, and assumptions.

### 作者问题 / Author Questions
1. 你心里已经有哪几种方案或思路？ / Approaches you already have in mind?
2. 有你想明确排除的方案吗？ / Approaches you specifically want to exclude?
3. 哪些利益相关者会受影响？ / Who are the stakeholders affected?
4. 硬约束是什么（预算、时间、技术栈、法规）？ / Hard constraints (budget, time, tech stack, regulation)?

### 交互模式 / Interaction Pattern
使用选项比较模板——呈现 2–4 个选项：
```
### 选项 A / Option A: <名称>
- 最适合 / Best when: …
- 好处 / Benefit: …
- 成本 / Cost: …
- 风险 / Risk: …
- 需要的证据 / Evidence needed: …
```
关键信息缺失时一次只问一个问题。范围分解：必须做、推迟、排除。
One question at a time. Scope decomposition: must-do, deferred, excluded.

### 产出物 / Artifact
选项比较在 `docs/brainstorming/<slug>.md`。含排序推荐及理由。推迟项和非目标列表。
Options comparison at `docs/brainstorming/<slug>.md`. Ranked recommendation with
rationale. Deferred items and non-goals lists.

### 确认门控 / Confirmation Gate
- [ ] 至少记录了一个替代方案（或已说明不存在的原因） / At least one alternative documented
- [ ] 作者已选择或认可推荐方向 / Author selected or endorsed a direction
- [ ] 明确的非目标已记录 / Explicit non-goals documented
- [ ] 风险和假设已捕获 / Risks and assumptions captured
- [ ] 下一层候选已确定 / Next layer candidate identified

### 禁止 / Forbidden
- 禁止只呈现一个选项而不说明为什么没有替代方案 / Do NOT present only one option without justification
- 禁止在未收敛方向时跳到实施规划 / Do NOT skip to implementation planning without converging
- 禁止将头脑风暴输出当作实施计划 / Do NOT treat brainstorming output as an implementation plan

---

## brief

### 目的 / Purpose
将目标、上下文、非目标、成功标准、风险和下一层锁定为稳定概要。
Lock the goal, context, non-goals, success criteria, risks, and next layer into a stable brief.

### 作者问题 / Author Questions
1. 目标陈述是否准确反映了成功的定义？ / Does the goal capture what success looks like?
2. 非目标是否正确——需要添加或删除什么？ / Are non-goals correct?
3. 成功标准是否可衡量、可验证？ / Are success criteria measurable and verifiable?
4. 下一层去哪个：Architecture、ADR、Contract，还是继续细化？ / Which layer next?

### 交互模式 / Interaction Pattern
使用概要模板呈现完整概要。请作者逐一检查各节。当下一层涉及 architecture/ADR
决策时标记出来。
Present the full brief. Ask author to review each section individually. Flag
when the next layer involves architecture/ADR decisions.

### 产出物 / Artifact
概要在 `docs/briefs/<slug>.md`。必须包含：目标、非目标、已考虑的选项、决策/方向、
风险/未知、成功标准、下一层。
Brief at `docs/briefs/<slug>.md`. Must contain: Goal, Non-Goals, Options Considered,
Decision/Direction, Risks/Unknowns, Success Criteria, Next Layer.

### 确认门控 / Confirmation Gate
- [ ] 目标陈述已明确批准 / Goal statement explicitly approved
- [ ] 非目标已明确确认 / Non-goals explicitly confirmed
- [ ] 成功标准是可衡量的（不模糊） / Success criteria are measurable
- [ ] 下一层选择已由作者明确确认 / Next layer explicitly confirmed
- [ ] 概要已写入持久化文件 / Brief written to a durable file

### 禁止 / Forbidden
- 禁止在概要进一步推进到架构/实施 / Do NOT proceed with an unconfirmed brief
- 禁止跳过下一层选择 / Do NOT skip Next Layer selection
- 禁止让成功标准含糊不清（"可以正常工作"） / Do NOT leave success criteria vague

---

## architecture

### 目的 / Purpose
定义边界、职责、所有权、数据流，并识别 ADR 候选。
Define boundaries, responsibilities, ownership, data flow, and identify ADR candidates.

### 作者问题 / Author Questions
1. 有现有的架构决策或图表可以参考吗？ / Existing architectural decisions or diagrams?
2. 哪些边界是固定的（不能改），哪些是可协商的？ / Which boundaries are firm, which are negotiable?
3. 哪些团队/系统拥有被触碰的组件？ / Which teams/systems own the components?
4. 数据流是怎样的——输入、输出、持久化？ / What is the data flow?

### 交互模式 / Interaction Pattern
呈现文本化边界图（组件、所有权、数据流方向、持久化点）。对每个需要 ADR 的边界决策
标记："这涉及长期边界，应该成为一个 ADR。你同意吗？"
Present a text-based boundary diagram. For each boundary decision needing an ADR,
flag it: "This should become an ADR. Do you agree?"

### 产出物 / Artifact
架构文档在 `docs/architecture/<slug>.md`。必须包含：边界定义、组件职责、所有权分配、
数据流描述、ADR 候选列表。
Architecture document at `docs/architecture/<slug>.md`. Must contain: boundary
definitions, component responsibilities, ownership assignments, data flow
description, ADR candidates list.

### 确认门控 / Confirmation Gate
- [ ] 所有边界已明确记录并检查 / All boundaries documented and reviewed
- [ ] 每个组件/接触点的所有者已确定 / Owners for each component identified
- [ ] ADR 候选已列出并附理由 / ADR candidates listed with rationale
- [ ] 未过早确定实现细节 / No implementation details decided prematurely

### 禁止 / Forbidden
- 禁止在此层决定实现细节（库、算法、代码结构） / Do NOT decide implementation details
- 禁止在未标记 ADR 候选的情况下冻结边界决策 / Do NOT freeze a boundary decision
  without flagging it as an ADR candidate
- 禁止在涉及所有权/部署/持久化/公共 API 时跳过到 Contract（T3 规则） / Do NOT skip
  to Contract when boundaries involve ownership/deployment/persistence/public APIs (T3)

---

## adr

### 目的 / Purpose
记录具体的架构决策，含理由、替代方案、后果和验证方式。
Document a specific architectural decision with rationale, alternatives, consequences,
and validation approach.

### 作者问题 / Author Questions
1. 你同意推荐的决策及其理由吗？ / Do you agree with the recommended decision?
2. 有没有未列出的替代方案需要考虑？ / Alternatives not listed?
3. 长期后果是什么——维护、迁移、成本？ / Long-term consequences?
4. 这个决策在实施后应该如何验证？ / How to validate after implementation?

### 交互模式 / Interaction Pattern
用标准格式呈现 ADR：
```
# ADR: <标题 / title>
## 状态 / Status: 提议中 / proposed
## 决策 / Decision: <一句话 / one sentence>
## 理由 / Rationale: <为什么 / why>
## 已考虑的替代方案 / Alternatives considered:
- <A>: <为什么不选 / why not>
- <B>: <为什么不选 / why not>
## 后果 / Consequences: <正面和负面 / positive and negative>
## 验证 / Validation: <如何验证决策是否正确 / how to verify>
```
请作者明确接受（提议中 → 已接受）。
Ask the author to explicitly accept (proposed → accepted).

### 产出物 / Artifact
ADR 在 `docs/adr/<NNNN>-<slug>.md`。必须持久化且可评审——涉及长期边界、持久化、部署、
所有权或公共合约时，绝不能仅存在聊天中（T4 规则）。
ADR at `docs/adr/<NNNN>-<slug>.md`. Must be durable and reviewable — never chat-only
when long-lived boundaries are involved (T4).

### 确认门控 / Confirmation Gate
- [ ] 决策已明确陈述并理解 / Decision explicitly stated and understood
- [ ] 至少考虑了一个替代方案并记录了拒绝理由 / At least one alternative considered
- [ ] 后果（正面和负面）已记录 / Consequences documented
- [ ] 验证方式已定义 / Validation approach defined
- [ ] ADR 状态已由作者从"提议中"改为"已接受" / ADR status moved to "accepted" by author

### 禁止 / Forbidden
- 禁止在涉及长期边界时仅将 ADR 留在聊天中（T4 规则） / Do NOT capture ADR in chat only (T4)
- 禁止在 Architecture/ADR 之前进入 Contract（T3 规则） / Do NOT enter Contract before ADR (T3)
- 禁止跳过替代方案而不说明理由 / Do NOT skip alternatives without justification

---

## contract

### 目的 / Purpose
定义可执行或可评审的契约——schema、fixture、示例、探针、API 形态、检查或验收测试。
Define executable or reviewable contracts — schema, fixture, example, probe, API shape,
check, or acceptance test.

### 作者问题 / Author Questions
1. 实现必须满足什么确切行为？ / What exact behaviour must the implementation satisfy?
2. 必须处理哪些失败情况？ / What failure cases must be handled?
3. 是否有现成的契约/schema/测试可以扩展而非替换？ / Existing contracts to extend?
4. 什么范围明确不在范围内？ / What scope is explicitly out of bounds?

### 交互模式 / Interaction Pattern
将契约呈现为可验证的断言："系统必须 `<行为>`。验证方式：`<检查>`。"
对每条契约条款："这正确反映了预期行为吗？"
Present contracts as verifiable assertions: "The system MUST `<behaviour>`. Verified by
`<check>`." For each clause: "Does this capture the expected behaviour correctly?"

### 产出物 / Artifact
契约文档在 `docs/contracts/<slug>.md` 或内联 schema/fixture/test 文件。
必须可执行或可评审。必须涵盖预期行为和失败行为。
Contract document at `docs/contracts/<slug>.md` or inline files. Must be executable or
reviewable. Must cover both expected and failure behaviour.

### 确认门控 / Confirmation Gate
- [ ] 每条契约条款已检查并接受 / Every contract clause reviewed and accepted
- [ ] 失败情况已明确覆盖 / Failure cases explicitly covered
- [ ] 禁止范围边界已遵守 / Forbidden scope boundaries respected
- [ ] 契约未在无前置 ADR 的情况下冻结所有权/部署/边界决策（T3 规则） / Contract does not
  freeze boundary decisions without prior ADR (T3)

### 禁止 / Forbidden
- 禁止在 Architecture/ADR 之前进入 Contract（T3 规则） / Do NOT enter Contract before ADR (T3)
- 禁止在此层编写实现代码 / Do NOT write implementation code at this layer
- 禁止将契约范围扩展到 Brief 和 Architecture 已定义的范围之外 / Do NOT expand scope

---

## readiness

### 目的 / Purpose
验证所有实施前置条件已满足：边界、契约、验证命令、AGENTS.md 规则、基线检查、
Implementation Entry Record。
Verify all implementation prerequisites are met.

### 作者问题 / Author Questions
1. 你是否认为所有实施前提条件都已满足？ / Are all prerequisites met?
2. 这是丢弃式原型，还是会产生持久化/真实产物？ / Throwaway prototype or real artifacts?
3. 对实施环境或工具有任何顾虑吗？ / Concerns about implementation environment or tooling?

### 交互模式 / Interaction Pattern
呈现准备就绪清单，每个门控项标注 pass/fail/not-applicable。
使用 Implementation Entry Record 格式。请作者逐一检查。
Present a readiness checklist with pass/fail/not-applicable for each gate item.
Use the Implementation Entry Record format.

### 产出物 / Artifact
Implementation Entry Record。必须包含全部 9 个字段，明确 readiness pass/fail。
Implementation Entry Record with all 9 fields and explicit readiness pass/fail.

### 确认门控 / Confirmation Gate
- [ ] 准备就绪结果（pass/fail）已明确说明 / Readiness gate result explicitly stated
- [ ] 所有契约证据已引用 / All contract evidence cited
- [ ] 验证命令已定义 / Verification commands defined
- [ ] 停止条件已定义 / Stop conditions defined
- [ ] 如果是原型：作者已明确限定为丢弃式，且确认无持久化数据/外部副作用/公共合约/生产行为（T1/T2）
- [ ] 作者已明确授权进入实施 / Author explicitly authorises implementation

### 禁止 / Forbidden
- 禁止在没有明确 readiness pass 的情况下进入实施（T1 规则） / Do NOT enter implementation
  without readiness pass (T1)
- 禁止在存在持久化数据或外部效应时将"快速推进"当作原型例外（T2 规则） / Do NOT treat
  "move fast" as prototype exception (T2)
- 禁止跳过 Implementation Entry Record / Do NOT skip the Implementation Entry Record

---

## implementation

### 目的 / Purpose
执行代码/配置更改，保持在批准的边界内，满足现有契约，停止条件触发时停止。
Execute code/config changes that stay inside approved boundaries and satisfy existing
contracts.

### 作者问题 / Author Questions
1. 你是想检查中间进度，还是只看最终结果？ / Review intermediate progress or final only?
2. 在触碰批准的所有者列表之外的文件之前，我应该停下来问你吗？ / Stop before touching
   files outside the approved owner list?
3. 如果验证失败：尝试修复，还是停止并报告？ / If verification fails: fix or stop?

### 交互模式 / Interaction Pattern
说明实施计划（要改的文件、要满足的契约、要运行的验证命令）。在自然检查点报告。
如果出现未契約的行为：停止并呈现发现。执行期间不要问不必要的问题。
State the implementation plan. Report at natural checkpoints. If uncontracted behaviour
surfaces: stop and present findings. Do NOT ask unnecessary questions during execution.

### 产出物 / Artifact
在批准的所有者列表内的更改文件。新鲜的验证证据。更新后的 Implementation Entry Record。
Changed files within approved owner list. Fresh verification evidence. Updated
Implementation Entry Record.

### 确认门控 / Confirmation Gate
- [ ] 所有验证命令已通过（或失败已明确记录） / All verification commands passed or failures documented
- [ ] 未引入未契約的行为（T7 规则） / No uncontracted behaviour introduced (T7)
- [ ] 所有停止条件已评估 / All stop conditions evaluated
- [ ] 作者已检查验证证据 / Author reviewed verification evidence

### 禁止 / Forbidden
- 禁止未经明确许可修改批准所有者列表之外的文件 / Do NOT modify files outside approved owner list
- 禁止将范围扩展到契约和准备就绪所定义的范围之外 / Do NOT expand scope
- 禁止重写契约、ADR 或范围文档 / Do NOT rewrite contracts, ADRs, or scope documents
- 禁止在停止条件触发时继续 / Do NOT continue when a stop condition fires

---

## verification

### 目的 / Purpose
从测试、检查、探针、截图、跟踪或明确的失败记录中产出新鲜证据。
Produce fresh evidence from tests, checks, probes, screenshots, traces, or explicit
failure records.

### 作者问题 / Author Questions
1. 除了已定义的命令外，还有额外的验证步骤吗？ / Additional verification steps?
2. 需要我录制截图或跟踪吗？ / Should I record screenshots or traces?
3. 如果验证失败：调查原因，还是报告并暂停？ / If verification fails: investigate or pause?

### 交互模式 / Interaction Pattern
用结构化格式呈现验证结果：命令、状态（passed/failed/skipped）、证据。
对失败：呈现失败证据，问是调查还是暂停。应用 T8 规则：识别拥有失败原因的最低层。
Present verification results in structured format. For failures: present evidence and
ask whether to investigate or pause. Apply T8: identify lowest layer that owns the failure.

### 产出物 / Artifact
新鲜验证证据在 `docs/verification/<slug>.md` 或变更包中。明确的失败记录。
验证新鲜度时间戳。
Fresh verification evidence. Explicit failure records. Verification freshness timestamp.

### 确认门控 / Confirmation Gate
- [ ] 所有验证命令已执行，结果是新鲜的 / All verification commands executed, results fresh
- [ ] 失败已记录证据并确定拥有者层 / Failures documented with evidence and owner layer
- [ ] 作者已检查验证摘要 / Author reviewed verification summary

### 禁止 / Forbidden
- 禁止跳过验证而声称"看起来没问题" / Do NOT skip verification and claim "looks good"
- 禁止在验证过期或失败时推进到 Review/Next / Do NOT advance with stale or failed verification
- 禁止隐藏或淡化验证失败 / Do NOT hide or downplay verification failures

---

## review-next

### 目的 / Purpose
归档已完成工作，更新调度器就绪队列，记录阻塞项、暂缓项、风险和证据到稳定状态。
Archive completed work, update scheduler ready queue, record blocked items, not-now items,
risks, and evidence to stable state.

### 作者问题 / Author Questions
1. 这项工作是否完成且可以归档？ / Is this work complete and ready to archive?
2. 下一个优先级是什么——接下来应该做什么？ / What is the next priority?
3. 有没有新的队列项、阻塞项或暂缓项要添加？ / New items to add to queue?
4. 有没有需要保留的风险或经验教训？ / Any risks or lessons learned to preserve?

### 交互模式 / Interaction Pattern
呈现摘要：做了什么、证据、风险、下一步。呈现队列更新：ready/blocked/not-now。
请作者明确批准归档和下一队列决策。使用
`harness review close <task-id> --evidence "..." --risks "..."`。
Present summary: what was done, evidence, risks, what's next. Present queue updates.
Ask author to explicitly approve archive and next-queue decisions.

### 产出物 / Artifact
完成归档条目。更新后的调度器就绪队列。阻塞项（含原因）。暂缓项（含理由）。
风险日志更新。Session 已关闭（如适用）。
Done archive entry. Updated scheduler ready queue. Blocked items with reasons. Not-now
items with rationale. Risk log updates. Session closed if applicable.

### 确认门控 / Confirmation Gate
- [ ] 完成归档条目准确且完整 / Done archive entry is accurate and complete
- [ ] 就绪队列、阻塞项和暂缓项已检查 / Queue, blocked, not-now items reviewed
- [ ] 风险和证据已写入稳定状态 / Risks and evidence written to stable state
- [ ] Session 已关闭或下一层已明确选择 / Session closed or next layer explicitly selected

### 禁止 / Forbidden
- 禁止在工作完成或暂停时跳过 Review/Next（T9 规则） / Do NOT skip Review/Next (T9)
- 禁止将"下一步"决策留在聊天中——写入队列 / Do NOT leave "what next" in chat
- 禁止归档验证过期或缺失的工作 / Do NOT archive work with stale or missing verification
