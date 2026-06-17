# Glossary / 术语表

A bilingual reference for the domain-specific terms used throughout
harness-governance. Terms are grouped by category; within each category
they are listed alphabetically.

harness-governance 中使用的领域术语的双语对照表。

---

## Core Model / 核心模型

**5-Layer Defense (五层防御)** — v0.7.0 引入的强制执行体系:
0: 3-Skill 入口分流, 1: RigorTier 自动检测, 2: LayerGateEngine 门控,
3: Lock Files 磁盘锁, 4: Git Pre-commit Hook。逐层收紧，不可绕过。

**Agent Platform (代理平台)** — The AI coding assistant that loads the
harness skill adapter. Supported: claude-code, codex, cline, cursor,
opencode, windsurf, qoderwork, generic (8 platforms). See also: *Skill Adapter*.

**Canonical Disclosure Block (标准披露块)** — The structured output
produced by `harness governed-start` that records the classification
(Fast / Trivial / Governed), affected files, routing flags, and rigor tier.

**Change Packet (变更包)** — A directory under `docs/changes/<id>/`
containing five template files (`proposal.md`, `design.md`, `tasks.md`,
`contracts.md`, `verification.md`) that carries a Governed task through
the state machine. See also: *Packet Status*.

**Classification (分类)** — The routing decision made at task intake:
Fast (pure question), Trivial (single-file safe change), or Governed
(multi-layer or high-risk work). Governed tasks enter the full pipeline.

**Entry Block Marker (入口标记)** — A configurable string (default
`Implementation Entry Record`) used to identify entry records in
Markdown files. See also: *Implementation Entry Record*.

**Gate Check (门控检查)** — `harness gate check <layer>` — 程序化验证某一层
是否满足推进条件（问题数 + artifacts 存在性）。exit 0 = 通过并写锁文件，
exit 1 = 失败。

**Gate Timing (门控耗时)** — `harness gate timing` (v0.7.1) — 从 session 的
TransitionRecord 和 lock file 读取每层耗时，输出总时长和平均值。

**Governed Path (受治理路径)** — The full state machine pipeline for
tasks that touch contracts, persistence, deployment, or multiple layers.
Produces a disclosure block and may require a change packet.

**HarnessConfig** — The Pydantic model loaded from `.harness/config.toml`
that holds all project-level settings: `agent_platform`, `queue_file`,
`changes_root`, `planning_root`, `harness_dir`, `check_frequency`, etc.

**Layer Gate (层门控)** — v0.7.0 引入的程序化验证机制。每一层定义了
`min_questions_answered` (按 RigorTier 区分)、`required_artifacts`、
`confirmation_items`。

**Lock File (锁文件)** — `.harness/gates/01-intake-orientation.lock` ~
`12-review-next.lock`。JSON 格式，记录通过时间、session_id、rigor_tier、
问答数、检查耗时。磁盘级强制——agent 在 Write/Edit 前必须运行
`harness gate check implementation`。

**Packet Status (包状态)** — One of: `draft`, `ready`, `active`,
`blocked`, `done`, `archived`. Governed by the
`ALLOWED_PACKET_STATUSES` constant. See also: *Change Packet*.

**Rigor Tier (严格等级)** — `LIGHT` (6 层，1 问题), `STANDARD` (12 层灵活,
半数问题), `STRICT` (12 层全走，全部问题)。默认 STRICT。
`harness governed-start --rigor` 可显式覆盖。

**RigorTier** — Python enum in `state_machine/rigor.py`. Auto-detected from
task description keywords (86 Chinese + English). Fallback: STRICT.

**Subagent Dispatch (子代理分发)** — v0.7.1 在 32 个 skill 文件中加入的
上下文隔离规则：预渲染不拼凑、禁止传对话历史、子代理是干净工作者。

**Transition Rule (转换规则)** — One of ten policy rules (T1-T10) enforced by
the state machine engine. Examples: readiness-before-implementation,
ADR durability, contract-before-implementation, scope-drift-return-to-contract.

---

## Layer Names / 层级 (12 Layers)

The state machine defines 12 layers in canonical order:

| # | Layer | Chinese | Purpose / 用途 |
|---|-------|---------|---------|
| 1 | intake-orientation | 接收定向 | Receive and orient the incoming request |
| 2 | idea | 构想 | Explore the high-level idea |
| 3 | fact-discovery | 事实发现 | Gather facts, constraints, and dependencies |
| 4 | brainstorming | 头脑风暴 | Generate and compare approaches |
| 5 | brief | 简报 | Produce a structured design brief |
| 6 | architecture | 架构 | Define architectural boundaries |
| 7 | adr | 架构决策记录 | Record an Architecture Decision Record |
| 8 | contract | 契约 | Write contracts and test specifications |
| 9 | readiness | 就绪检查 | Verify readiness before implementation |
| 10 | implementation | 实现 | Write the code |
| 11 | verification | 验证 | Run verification commands and attest results |
| 12 | review-next | 评审/下一步 | Close the task and determine next steps |

LIGHT tier skips layers 2 (idea), 3 (fact-discovery), 4 (brainstorming),
6 (architecture), 7 (adr), 8 (contract).

---

## Execution Modes / 执行模式

**Autonomous Ready Loop (自治就绪循环)** — The `harness runner start`
loop that reads the queue, dispatches work, parses results, and advances
or stops based on markers. Supports `bounded` (strict round cap) and
`boundary` (cap as fuse) modes.

**Bounded Mode (有界模式)** — Execution mode where the loop stops
after exactly `max_rounds` rounds, regardless of outcome.

**Boundary Mode (边界模式)** — Execution mode where `max_rounds` acts
as a fuse; the loop continues until it hits an `AUTONOMOUS_BOUNDARY_REACHED`
marker or exhausts the cap.

**Hard Gate (硬门)** — A fallback that escalates from subagent to
main-session execution when security, persistence, deployment, or
cross-repository behavior changes are involved. Platform-specific.

---

## File Artifacts / 文件制品

**`.harness/config.toml`** — Project-level configuration written by
`harness init`. Contains `agent_platform`, path settings, and check
frequency.

**`.harness/gates/`** — Lock file directory (v0.7.0). Contains
`01-intake-orientation.lock` through `12-review-next.lock`. See: *Lock File*.

**`.harness/invocations.ndjson`** — Append-only log of subagent
invocations. Each line is a JSON record with role, timestamp, result,
and round index.

**`.harness/run-checkpoint.md`** — Checkpoint file tracking the last
worker round, verification summary, and stop reason. Written by
`harness runner checkpoint-write`.

**`.harness/sessions/`** — Session state JSON files (v0.7.0). Each
file records `session_id`, `rigor_tier`, `layer_qa`, `transitions`.

**`.harness/status.json` / `status.md`** — Dashboard files generated by
`harness status --refresh`. The JSON version is machine-readable;
the Markdown version is human-readable.

**`NEXT.md` (队列文件)** — The project queue file. Contains items
prefixed with status labels (`[ready]`, `[active]`, `[blocked]`,
`[done]`, `[not-now]`) and optional fields like `Layer`, `Role`,
`Change`, `Verification command`, `Done when`, `Forbidden shortcut`.

**`docs/changes/<id>/`** — Change packet directory. Contains five
required template files in canonical order: `proposal.md`, `design.md`,
`tasks.md`, `contracts.md`, `verification.md`.

**`.planning/<id>/`** — Planning carrier directory created by
`harness plan init`. Used for session-level planning attestation.

**Implementation Entry Record (实现入口记录)** — A Markdown document
validated by `harness entry check` that records what was implemented,
how it was verified, and whether readiness gates were satisfied.

**Skill Adapter (技能适配器)** — Per-platform Markdown files written
by `harness init` that tell the agent how to use harness commands.
Since v0.7.0, three tiers are written per platform: `strict`, `standard`,
`light`. Location depends on platform (e.g., `.claude/skills/harness-governance-strict/SKILL.md`,
`.cursor/rules/harness-governance-strict.mdc`, `AGENTS.md`).

---

## Roles / 角色 (9 Dispatchable)

Roles used by the Subagent Runner to dispatch work:

| Role | Layers | Purpose / 用途 |
|------|--------|---------|
| Planner | 2-5 | Explores ideas, gathers facts, brainstorms, writes briefs |
| Contract Writer | 8 | Writes contracts and test specifications |
| Implementer | 10 | Writes the code |
| Reviewer | 11-12 | Runs verification and determines next steps |
| ADR Writer | 7 | Records Architecture Decision Records |
| Fact Finder Reviewer | 3 | Gathers facts, constraints, dependencies |
| Readiness Gate Writer | 9 | Verifies implementation readiness |
| Document Gardener | cross-cutting | Maintains documentation consistency |
| Integrator | cross-cutting | Merges and coordinates multi-worker outputs |

Each role has a template under `data/role-prompts/` that defines
approved inputs, forbidden inputs, and `{{PLACEHOLDER}}` tokens for
variable substitution.

---

## CLI Commands / CLI 命令

| Command | Purpose / 用途 |
|---------|---------|
| `harness init` | Write config + 3-tier skill adapters + scaffolding |
| `harness governed-start` | Classify task, produce disclosure block (v0.7.0: `--rigor`) |
| `harness gate check` | Programmatic gate verification (v0.7.0) |
| `harness gate status` | Lock file status (v0.7.0) |
| `harness gate reset` | Remove lock file (v0.7.0, requires `--confirmed`) |
| `harness gate timing` | Per-layer timing analysis (v0.7.1) |
| `harness layer advance` | Advance session layer (v0.7.0: gate-enforced) |
| `harness layer show` | Current layer + transition history |
| `harness layer guide` | Print author interaction guide for a layer |
| `harness packet init/check` | Manage change packets |
| `harness entry check/record` | Validate/render entry records |
| `harness plan init/attest/show/clear/complete` | Planning carrier |
| `harness check routing` | Routing guardrail check |
| `harness check docs` | Document gardener check (v0.7.1, `--self` for self-check) |
| `harness check all` | All governance checks |
| `harness status` | Aggregate dashboard |
| `harness verify` | Run verification presets |
| `harness review close` | Persist review/next state |
| `harness session show/list` | Inspect governance sessions |
| `harness runner start` | Autonomous-ready loop |
| `harness runner render` | Pre-render role prompt with variables |
| `harness runner parse-result` | Parse subagent JSON result |
| `harness config init` | Write config only (no skill adapter) |

---

## Runner Terms / Runner 术语

**Invocation Log (调用日志)** — The `invocations.ndjson` file that
records each subagent dispatch: role, timestamp, files changed, verdict,
and round index.

**Orchestrator (编排器)** — The agent-loaded prompt produced by
`harness runner start --executor orchestrator`. Combines orchestrator
rules, pre-rendered role prompts, queue context, and execution
parameters into a single document.

**Queue Item (队列项)** — A single entry in `NEXT.md`, consisting of a
status label and optional metadata fields.

**Role Prompt (角色提示)** — A pre-rendered Markdown prompt for a
specific role, with all `{{PLACEHOLDER}}` tokens substituted with
actual file contents from the project.

**Subagent (子代理)** — A dispatched worker that receives a role prompt
and returns a structured JSON result. Platform-specific: Agent tool
(Claude Code), `codex exec` (Codex), Task tool (QoderWork), etc.

**Template Renderer (模板渲染器)** — The component that substitutes
`{{VARIABLE_NAME}}` placeholders in role templates with exact file
contents extracted by the Variable Extractor.

**Variable Extractor (变量提取器)** — The component that reads project
files (queue item, change packet, git diff) and produces a
`RoleVariables` dataclass for template rendering.
