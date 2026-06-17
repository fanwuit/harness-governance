# Layer Author Interaction Guide / 层作者交互指南

When the agent enters a layer, this guide tells it HOW to interact with the
human author — what questions to ask, how to present options, where to record
decisions, and what to confirm before advancing.

当 agent 进入某一层时，本指南告诉它如何与人类作者交互——该问什么、怎么呈现选项、
决策记录到哪里、推进前确认什么。

---

## intake-orientation

### Purpose / 目的
Establish repo/task context, identify the active queue or planning source,
and surface known constraints before any work begins.

建立仓库/任务上下文，识别已有队列或规划来源，在开始工作前明确已知约束。

### Author Questions / 作者问题
1. What is the current task or goal? / 当前的任务或目标是什么？
2. Is there an existing queue (NEXT.md, TODO, backlog, issue tracker)? / 是否有现有队列（NEXT.md、TODO、backlog、issue tracker）？
3. Are there known constraints or risks? / 有哪些已知的约束或风险？
4. Continuation or new task? / 这是之前工作的延续，还是新任务？

### Interaction Pattern / 交互模式
Present routing decision with rationale. One question at a time — never ask
all four at once. Start with #1, then #2 if no queue is visible.

展示路由决定和依据。一次只问一个问题——不要同时问四个。从#1开始，如果看不到队列再问#2。

### Artifact / 产出物
Session state in `.harness/sessions/<id>.json` via `harness governed-start`.
If no queue exists, scaffold a `NEXT.md` or planning file.

通过 `harness governed-start` 生成 `.harness/sessions/<id>.json`。
如果没有队列，搭建 `NEXT.md` 或规划文件。

### Confirmation Gate / 确认门控
- [ ] Routing decision explicitly acknowledged / 路由决定已被明确确认
- [ ] Current layer stated and understood / 当前层已说明并理解
- [ ] Competing skill warnings reviewed (if any) / 竞争 skill 警告已检查（如有）
- [ ] Session ID recorded / Session ID 已记录

### Forbidden / 禁止
- Do NOT start work before the disclosure block is output / 禁止在输出披露块之前开始工作
- Do NOT skip `harness governed-start` / 禁止跳过 `harness governed-start`
- Do NOT infer layer order from skill names / 禁止从 skill 名称或目录结构推断层顺序
- Do NOT auto-create branches, commits, or worktrees / 禁止自动创建分支、提交或 worktree

---

## idea

### Purpose / 目的
Stabilise the user's intent into a single, reviewable sentence before any analysis.

将用户意图稳定为一句话，可在后续分析前被评审。

### Author Questions / 作者问题
1. Can you state the core problem in one sentence? / 你能用一句话描述核心问题或意图吗？
2. Feature, bug fix, refactor, investigation, or other? / 这是功能需求、bug 修复、重构、调查，还是其他？

### Interaction Pattern / 交互模式
Echo back a proposed one-line summary and ask "Is this accurate?" Do not move
forward until confirmed.

回显一个拟议的一句话摘要，问"这个准确吗？"帮助提炼长描述。在确认之前不往前推进。

### Artifact / 产出物
Stable intent in the session or `docs/ideas/<slug>.md`. If using change packets:
`docs/changes/<id>/proposal.md`.

Session 中的稳定意图或 `docs/ideas/<slug>.md`。如果使用变更包：`docs/changes/<id>/proposal.md`。

### Confirmation Gate / 确认门控
- [ ] One-line intent explicitly approved / 一句话意图陈述已由作者明确批准
- [ ] Task type agreed / 任务类型已达成一致
- [ ] Any known non-goals noted / 作者提出的任何非目标已记录

### Forbidden / 禁止
- Do NOT begin research before intent is stable / 禁止在意图书稳定之前开始研究、事实发现或头脑风暴
- Do NOT rewrite the user's intent / 禁止将用户意图改写为对方没有要求的内容

---

## fact-discovery

### Purpose / 目的
Gather reviewable facts or explicitly declare unknowns before they become hidden assumptions.

收集可评审的事实，或明确声明未知事项，防止它们变成隐藏假设。

### Author Questions / 作者问题
1. Specific files, logs, APIs, or docs to examine first? / 有哪些特定的文件、日志、API 或文档我应该先查看？
2. Known unknowns? / 有哪些已知的未知——我们已经知道我们不知道的事情？
3. What existing evidence can you point to? / 你能指给我哪些现有的证据？

### Interaction Pattern / 交互模式
List findings and remaining unknowns. Use Assumption/Risk blocks. Present each
unknown individually; ask "Can you confirm or correct this?"

列出发现和剩余未知事项。对每个未知使用"假设 / 风险"块：
```
Assumption / 假设: <当前保守假设>
Risk / 风险: <如果假设错误会怎样>
```
逐一呈现每个未知事项；问"你能确认或纠正这个吗？"

### Artifact / 产出物
Facts in `docs/facts/<slug>.md`. Explicit unknowns with Assumption/Risk blocks.
Citations to external docs, logs, or fixtures.

事实记录在 `docs/facts/<slug>.md`。明确的未知列表含假设/风险块。
引用外部文档、日志或 fixtures。

### Confirmation Gate / 确认门控
- [ ] All material unknowns resolved or declared / 所有实质性未知事项要么已有证据解决，要么已明确声明为假设
- [ ] Author reviewed Assumption/Risk blocks / 作者已检查并接受假设/风险块
- [ ] Results written to durable location / 结果已写入持久化位置（非仅聊天）

### Forbidden / 禁止
- Do NOT skip fact discovery when material unknowns exist (T5) / 禁止在存在实质性未知时跳过事实发现（T5 规则）
- Do NOT treat an assumption as a fact / 禁止未经作者确认就把假设当事实
- Do NOT proceed with unresolved unknowns / 禁止在未解决未知的情况下进入方案设计

---

## brainstorming

### Purpose / 目的
Generate and compare options with structured tradeoffs, risks, and assumptions.

生成并比较选项，含结构化权衡、风险和假设。

### Author Questions / 作者问题
1. Approaches you already have in mind? / 你心里已经有哪几种方案或思路？
2. Approaches you specifically want to exclude? / 有你想明确排除的方案吗？
3. Who are the stakeholders affected? / 哪些利益相关者会受影响？
4. Hard constraints (budget, time, tech stack, regulation)? / 硬约束是什么（预算、时间、技术栈、法规）？

### Interaction Pattern / 交互模式
Present 2–4 options using the option comparison template:
```
### Option A / 选项 A: <name / 名称>
- Best when / 最适合: …
- Benefit / 好处: …
- Cost / 成本: …
- Risk / 风险: …
- Evidence needed / 需要的证据: …
```
One question at a time when key information is missing. Scope decomposition: must-do, deferred, excluded.

关键信息缺失时一次只问一个问题。范围分解：必须做、推迟、排除。

### Artifact / 产出物
Options comparison at `docs/brainstorming/<slug>.md`. Ranked recommendation with
rationale. Deferred items and non-goals lists.

选项比较在 `docs/brainstorming/<slug>.md`。含排序推荐及理由。推迟项和非目标列表。

### Confirmation Gate / 确认门控
- [ ] At least one alternative documented / 至少记录了一个替代方案（或已说明不存在的原因）
- [ ] Author selected or endorsed a direction / 作者已选择或认可推荐方向
- [ ] Explicit non-goals documented / 明确的非目标已记录
- [ ] Risks and assumptions captured / 风险和假设已捕获
- [ ] Next layer candidate identified / 下一层候选已确定

### Forbidden / 禁止
- Do NOT present only one option without justification / 禁止只呈现一个选项而不说明为什么没有替代方案
- Do NOT skip to implementation planning without converging / 禁止在未收敛方向时跳到实施规划
- Do NOT treat brainstorming output as an implementation plan / 禁止将头脑风暴输出当作实施计划

---

## brief

### Purpose / 目的
Lock the goal, context, non-goals, success criteria, risks, and next layer into a stable brief.

将目标、上下文、非目标、成功标准、风险和下一层锁定为稳定概要。

### Author Questions / 作者问题
1. Does the goal capture what success looks like? / 目标陈述是否准确反映了成功的定义？
2. Are non-goals correct? / 非目标是否正确——需要添加或删除什么？
3. Are success criteria measurable and verifiable? / 成功标准是否可衡量、可验证？
4. Which layer next? / 下一层去哪个：Architecture、ADR、Contract，还是继续细化？

### Interaction Pattern / 交互模式
Present the full brief. Ask author to review each section individually. Flag
when the next layer involves architecture/ADR decisions.

使用概要模板呈现完整概要。请作者逐一检查各节。当下一层涉及 architecture/ADR
决策时标记出来。

### Artifact / 产出物
Brief at `docs/briefs/<slug>.md`. Must contain: Goal, Non-Goals, Options Considered,
Decision/Direction, Risks/Unknowns, Success Criteria, Next Layer.

概要在 `docs/briefs/<slug>.md`。必须包含：目标、非目标、已考虑的选项、决策/方向、
风险/未知、成功标准、下一层。

### Confirmation Gate / 确认门控
- [ ] Goal statement explicitly approved / 目标陈述已明确批准
- [ ] Non-goals explicitly confirmed / 非目标已明确确认
- [ ] Success criteria are measurable / 成功标准是可衡量的（不模糊）
- [ ] Next layer explicitly confirmed / 下一层选择已由作者明确确认
- [ ] Brief written to a durable file / 概要已写入持久化文件

### Forbidden / 禁止
- Do NOT proceed with an unconfirmed brief / 禁止在概要未确认时进一步推进到架构/实施
- Do NOT skip Next Layer selection / 禁止跳过下一层选择
- Do NOT leave success criteria vague / 禁止让成功标准含糊不清（"可以正常工作"）

---

## architecture

### Purpose / 目的
Define boundaries, responsibilities, ownership, data flow, and identify ADR candidates.

定义边界、职责、所有权、数据流，并识别 ADR 候选。

### Author Questions / 作者问题
1. Existing architectural decisions or diagrams? / 有现有的架构决策或图表可以参考吗？
2. Which boundaries are firm, which are negotiable? / 哪些边界是固定的（不能改），哪些是可协商的？
3. Which teams/systems own the components? / 哪些团队/系统拥有被触碰的组件？
4. What is the data flow? / 数据流是怎样的——输入、输出、持久化？

### Interaction Pattern / 交互模式
Present a text-based boundary diagram. For each boundary decision needing an ADR,
flag it: "This should become an ADR. Do you agree?"

呈现文本化边界图（组件、所有权、数据流方向、持久化点）。对每个需要 ADR 的边界决策
标记："这涉及长期边界，应该成为一个 ADR。你同意吗？"

### Artifact / 产出物
Architecture document at `docs/architecture/<slug>.md`. Must contain: boundary
definitions, component responsibilities, ownership assignments, data flow
description, ADR candidates list.

架构文档在 `docs/architecture/<slug>.md`。必须包含：边界定义、组件职责、所有权分配、
数据流描述、ADR 候选列表。

### Confirmation Gate / 确认门控
- [ ] All boundaries documented and reviewed / 所有边界已明确记录并检查
- [ ] Owners for each component identified / 每个组件/接触点的所有者已确定
- [ ] ADR candidates listed with rationale / ADR 候选已列出并附理由
- [ ] No implementation details decided prematurely / 未过早确定实现细节

### Forbidden / 禁止
- Do NOT decide implementation details / 禁止在此层决定实现细节（库、算法、代码结构）
- Do NOT freeze a boundary decision
  without flagging it as an ADR candidate / 禁止在未标记 ADR 候选的情况下冻结边界决策
- Do NOT skip to Contract when boundaries involve ownership/deployment/persistence/public APIs (T3) / 禁止
  在涉及所有权/部署/持久化/公共 API 时跳过到 Contract（T3 规则）

---

## adr

### Purpose / 目的
Document a specific architectural decision with rationale, alternatives, consequences,
and validation approach.

记录具体的架构决策，含理由、替代方案、后果和验证方式。

### Author Questions / 作者问题
1. Do you agree with the recommended decision? / 你同意推荐的决策及其理由吗？
2. Alternatives not listed? / 有没有未列出的替代方案需要考虑？
3. Long-term consequences? / 长期后果是什么——维护、迁移、成本？
4. How to validate after implementation? / 这个决策在实施后应该如何验证？

### Interaction Pattern / 交互模式
Present the ADR in standard format:
```
# ADR: <title / 标题>
## Status / 状态: proposed / 提议中
## Decision / 决策: <one sentence / 一句话>
## Rationale / 理由: <why / 为什么>
## Alternatives considered / 已考虑的替代方案:
- <A>: <why not / 为什么不选>
- <B>: <why not / 为什么不选>
## Consequences / 后果: <positive and negative / 正面和负面>
## Validation / 验证: <how to verify / 如何验证决策是否正确>
```
Ask the author to explicitly accept (proposed → accepted).

请作者明确接受（提议中 → 已接受）。

### Artifact / 产出物
ADR at `docs/adr/<NNNN>-<slug>.md`. Must be durable and reviewable — never chat-only
when long-lived boundaries are involved (T4).

ADR 在 `docs/adr/<NNNN>-<slug>.md`。必须持久化且可评审——涉及长期边界、持久化、部署、
所有权或公共合约时，绝不能仅存在聊天中（T4 规则）。

### Confirmation Gate / 确认门控
- [ ] Decision explicitly stated and understood / 决策已明确陈述并理解
- [ ] At least one alternative considered / 至少考虑了一个替代方案并记录了拒绝理由
- [ ] Consequences documented / 后果（正面和负面）已记录
- [ ] Validation approach defined / 验证方式已定义
- [ ] ADR status moved to "accepted" by author / ADR 状态已由作者从"提议中"改为"已接受"

### Forbidden / 禁止
- Do NOT capture ADR in chat only (T4) / 禁止在涉及长期边界时仅将 ADR 留在聊天中（T4 规则）
- Do NOT enter Contract before ADR (T3) / 禁止在 Architecture/ADR 之前进入 Contract（T3 规则）
- Do NOT skip alternatives without justification / 禁止跳过替代方案而不说明理由

---

## contract

### Purpose / 目的
Define executable or reviewable contracts — schema, fixture, example, probe, API shape,
check, or acceptance test.

定义可执行或可评审的契约——schema、fixture、示例、探针、API 形态、检查或验收测试。

### Author Questions / 作者问题
1. What exact behaviour must the implementation satisfy? / 实现必须满足什么确切行为？
2. What failure cases must be handled? / 必须处理哪些失败情况？
3. Existing contracts to extend? / 是否有现成的契约/schema/测试可以扩展而非替换？
4. What scope is explicitly out of bounds? / 什么范围明确不在范围内？

### Interaction Pattern / 交互模式
Present contracts as verifiable assertions: "The system MUST `<behaviour>`. Verified by
`<check>`." For each clause: "Does this capture the expected behaviour correctly?"

将契约呈现为可验证的断言："系统必须 `<行为>`。验证方式：`<检查>`。"
对每条契约条款："这正确反映了预期行为吗？"

### Artifact / 产出物
Contract document at `docs/contracts/<slug>.md` or inline files. Must be executable or
reviewable. Must cover both expected and failure behaviour.

契约文档在 `docs/contracts/<slug>.md` 或内联 schema/fixture/test 文件。
必须可执行或可评审。必须涵盖预期行为和失败行为。

### Confirmation Gate / 确认门控
- [ ] Every contract clause reviewed and accepted / 每条契约条款已检查并接受
- [ ] Failure cases explicitly covered / 失败情况已明确覆盖
- [ ] Forbidden scope boundaries respected / 禁止范围边界已遵守
- [ ] Contract does not freeze boundary decisions without prior ADR (T3) / 契约未在无前置 ADR 的情况下
  冻结所有权/部署/边界决策（T3 规则）

### Forbidden / 禁止
- Do NOT enter Contract before ADR (T3) / 禁止在 Architecture/ADR 之前进入 Contract（T3 规则）
- Do NOT write implementation code at this layer / 禁止在此层编写实现代码
- Do NOT expand scope / 禁止将契约范围扩展到 Brief 和 Architecture 已定义的范围之外

---

## readiness

### Purpose / 目的
Verify all implementation prerequisites are met, including contract-based tests.

验证所有实施前置条件已满足：边界、契约、验证命令、AGENTS.md 规则、基线检查、
Implementation Entry Record、**基于契约的单元测试**。

### Author Questions / 作者问题
1. Are all prerequisites met? / 你是否认为所有实施前提条件都已满足？
2. Throwaway prototype or real artifacts? / 这是丢弃式原型，还是会产生持久化/真实产物？
3. Concerns about implementation environment or tooling? / 对实施环境或工具有任何顾虑吗？

### Test Preparation / 测试准备
**Before the gate check**: translate every behavioural specification from the contract
layer into executable unit tests. Test files must exist under `tests/`. If the gate
check fails because `tests/**/*.py` is missing, write tests FROM the contract before
asking for author confirmation.

**在 gate check 之前**: 基于 contract 层产出的契约文档，将每一条行为规范翻译为可执行的
单元测试。测试文件必须存在于 `tests/` 目录下。

Protocol / 步骤:
1. Read `docs/contracts/*.md`, extract all Behaviour / Failure Cases / Scope clauses
2. Write at least one positive test per Behaviour, at least one error-path test per Failure Case
3. Write tests to `tests/`, ensure `pytest` or direct run without arguments works

### Artifact / 产出物
- `tests/**/*.py` — Contract-based executable tests / 基于契约的可执行单元测试
- Implementation Entry Record. Must contain all 9 fields, with explicit readiness pass/fail.

Implementation Entry Record。必须包含全部 9 个字段，明确 readiness pass/fail。

### Confirmation Gate / 确认门控
- [ ] Readiness gate result explicitly stated / 准备就绪结果（pass/fail）已明确说明
- [ ] All contract evidence cited / 所有契约证据已引用
- [ ] Verification commands defined / 验证命令已定义
- [ ] Stop conditions defined / 停止条件已定义
- [ ] Unit tests prepared from contract and passing / 单元测试已基于契约编写并通过
- [ ] If prototype: author explicitly scoped it as throwaway, confirmed no persistent data / external side effects / public contracts / production behaviour (T1/T2) / 如果是原型：作者已明确限定为丢弃式，且确认无持久化数据/外部副作用/公共合约/生产行为（T1/T2）
- [ ] Author explicitly authorises implementation / 作者已明确授权进入实施

### Forbidden / 禁止
- Do NOT enter implementation without readiness pass (T1) / 禁止在没有明确 readiness pass 的情况下进入实施（T1 规则）
- Do NOT treat "move fast" as prototype exception when persistent data or external effects exist (T2) / 禁止
  在存在持久化数据或外部效应时将"快速推进"当作原型例外（T2 规则）
- Do NOT skip the Implementation Entry Record / 禁止跳过 Implementation Entry Record
- Do NOT enter implementation without passing tests / 禁止在测试缺失或未通过时进入实施

---

## implementation

### Purpose / 目的
Execute code/config changes that stay inside approved boundaries and satisfy existing
contracts.

执行代码/配置更改，保持在批准的边界内，满足现有契约，停止条件触发时停止。

### Author Questions / 作者问题
1. Review intermediate progress or final only? / 你是想检查中间进度，还是只看最终结果？
2. Stop before touching files outside the approved owner list? / 在触碰批准的所有者列表之外的文件之前，我应该停下来问你吗？
3. If verification fails: fix or stop? / 如果验证失败：尝试修复，还是停止并报告？

### Interaction Pattern / 交互模式
State the implementation plan. Report at natural checkpoints. If uncontracted behaviour
surfaces: stop and present findings. Do NOT ask unnecessary questions during execution.

说明实施计划（要改的文件、要满足的契约、要运行的验证命令）。在自然检查点报告。
如果出现未契約的行为：停止并呈现发现。执行期间不要问不必要的问题。

### Artifact / 产出物
Changed files within approved owner list. Fresh verification evidence. Updated
Implementation Entry Record.

在批准的所有者列表内的更改文件。新鲜的验证证据。更新后的 Implementation Entry Record。

### Confirmation Gate / 确认门控
- [ ] All verification commands passed or failures documented / 所有验证命令已通过（或失败已明确记录）
- [ ] No uncontracted behaviour introduced (T7) / 未引入未契約的行为（T7 规则）
- [ ] All stop conditions evaluated / 所有停止条件已评估
- [ ] Author reviewed verification evidence / 作者已检查验证证据

### Forbidden / 禁止
- Do NOT modify files outside approved owner list / 禁止未经明确许可修改批准所有者列表之外的文件
- Do NOT expand scope / 禁止将范围扩展到契约和准备就绪所定义的范围之外
- Do NOT rewrite contracts, ADRs, or scope documents / 禁止重写契约、ADR 或范围文档
- Do NOT continue when a stop condition fires / 禁止在停止条件触发时继续

---

## verification

### Purpose / 目的
Produce fresh evidence from tests, checks, probes, screenshots, traces, or explicit
failure records.

从测试、检查、探针、截图、跟踪或明确的失败记录中产出新鲜证据。

### Author Questions / 作者问题
1. Additional verification steps? / 除了已定义的命令外，还有额外的验证步骤吗？
2. Should I record screenshots or traces? / 需要我录制截图或跟踪吗？
3. If verification fails: investigate or pause? / 如果验证失败：调查原因，还是报告并暂停？

### Interaction Pattern / 交互模式
Present verification results in structured format. For failures: present evidence and
ask whether to investigate or pause. Apply T8: identify lowest layer that owns the failure.

用结构化格式呈现验证结果：命令、状态（passed/failed/skipped）、证据。
对失败：呈现失败证据，问是调查还是暂停。应用 T8 规则：识别拥有失败原因的最低层。

### Artifact / 产出物
Fresh verification evidence. Explicit failure records. Verification freshness timestamp.

新鲜验证证据在 `docs/verification/<slug>.md` 或变更包中。明确的失败记录。
验证新鲜度时间戳。

### Confirmation Gate / 确认门控
- [ ] All verification commands executed, results fresh / 所有验证命令已执行，结果是新鲜的
- [ ] Failures documented with evidence and owner layer / 失败已记录证据并确定拥有者层
- [ ] Author reviewed verification summary / 作者已检查验证摘要

### Forbidden / 禁止
- Do NOT skip verification and claim "looks good" / 禁止跳过验证而声称"看起来没问题"
- Do NOT advance with stale or failed verification / 禁止在验证过期或失败时推进到 Review/Next
- Do NOT hide or downplay verification failures / 禁止隐藏或淡化验证失败

---

## review-next

### Purpose / 目的
Archive completed work, update scheduler ready queue, record blocked items, not-now items,
risks, and evidence to stable state.

归档已完成工作，更新调度器就绪队列，记录阻塞项、暂缓项、风险和证据到稳定状态。

### Author Questions / 作者问题
1. Is this work complete and ready to archive? / 这项工作是否完成且可以归档？
2. What is the next priority? / 下一个优先级是什么——接下来应该做什么？
3. New items to add to queue? / 有没有新的队列项、阻塞项或暂缓项要添加？
4. Any risks or lessons learned to preserve? / 有没有需要保留的风险或经验教训？

### Interaction Pattern / 交互模式
Present summary: what was done, evidence, risks, what's next. Present queue updates.
Ask author to explicitly approve archive and next-queue decisions.

呈现摘要：做了什么、证据、风险、下一步。呈现队列更新：ready/blocked/not-now。
请作者明确批准归档和下一队列决策。使用
`harness review close <task-id> --evidence "..." --risks "..."`。

### Artifact / 产出物
Done archive entry. Updated scheduler ready queue. Blocked items with reasons. Not-now
items with rationale. Risk log updates. Session closed if applicable.

完成归档条目。更新后的调度器就绪队列。阻塞项（含原因）。暂缓项（含理由）。
风险日志更新。Session 已关闭（如适用）。

### Confirmation Gate / 确认门控
- [ ] Done archive entry is accurate and complete / 完成归档条目准确且完整
- [ ] Queue, blocked, not-now items reviewed / 就绪队列、阻塞项和暂缓项已检查
- [ ] Risks and evidence written to stable state / 风险和证据已写入稳定状态
- [ ] Session closed or next layer explicitly selected / Session 已关闭或下一层已明确选择

### Forbidden / 禁止
- Do NOT skip Review/Next (T9) / 禁止在工作完成或暂停时跳过 Review/Next（T9 规则）
- Do NOT leave "what next" in chat / 禁止将"下一步"决策留在聊天中——写入队列
- Do NOT archive work with stale or missing verification / 禁止归档验证过期或缺失的工作
