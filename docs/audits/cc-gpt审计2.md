# cc-gpt skills 二次审计：对比 OpenSpec + Superpowers + GStack

> 日期：2026-06-12  
> 范围：`E:\my-skills` 当前整套非 system skills、根目录治理文档、核心 reference、脚本/测试入口，以及 OpenSpec / Superpowers / GStack 的公开定位。  
> 目标：审计当前本地 skills harness 的实际状态，对比 `OpenSpec + Superpowers + GStack` 组合的差异，并总结下一步可改进点。

## 1. 一句话结论

当前 `E:\my-skills` 已经从“skills 集合”演进成一套 **local agent governance harness**：它的强项不是某个开发阶段的单点提示词，而是用入口锁、层级状态机、契约优先、实现准入、Implementation Entry Record、角色隔离、队列/checkpoint、done archive、自治 runner 和状态可视化来约束 AI coding agent 的长期行为。

与 `OpenSpec + Superpowers + GStack` 相比：

- **本项目更强**：治理主权、入口路由、companion workflow containment、实现前准入、持久状态、长任务自治、状态 JSON/Markdown 可视化、避免自测自收。
- **外部组合更强**：产品化安装、生态可见度、多工具分发、团队上手 UX、角色/命令命名的直觉性、release/ship/retro 一体化、浏览器 QA / 发布检查等端到端交付叙事。
- **最适合定位**：不是替代 OpenSpec、Superpowers 或 GStack，而是作为它们之上的 **本地治理内核 / adapter boundary / execution guardrail**。OpenSpec 管 spec artifact discipline，Superpowers 管工程动作纪律，GStack 管角色化交付叙事；本项目负责决定何时能进入下一层、哪些证据必须落盘、什么不能被 companion workflow 越权。

## 2. 本地验证结果

本轮运行：

```text
npm run check:all
```

结果：

| 检查 | 结果 |
|---|---|
| routing guardrail | pass |
| Node test suite | 25/25 pass |
| change packet check | pass：no change packets found |
| Implementation Entry Record check | pass：`cc-gpt整改记录.md` |

说明：相比上一轮 `cc-gpt审计.md` 中指出的问题，很多 P0/P1 项已经整改完成并进入机械检查，例如：

- canonical layer progression 已统一到 `harness-engineering/references/layer-progression.md`。
- `governed-implementation-entry` 已纳入 readiness / implementation 路由。
- autonomous runner 已改为命名 verification preset，避免直接 `eval` / `Invoke-Expression` 任意命令。
- `harness-status.mjs` 已测试拒绝 repo 外 status 输出路径。
- `harness-status-dashboard` 与 `harness-visualization` 的默认职责已拆分。
- PowerShell planning parity 已有测试。
- 根目录 `package.json` 已提供 `npm run check:all`。

## 3. 当前 skills 能力画像

根 README 登记当前启用非 system skills：25 个。它们覆盖的是 agent 工程治理链路，不是语言/框架片段库。

### 3.1 Canonical progression

当前 source of truth：`harness-engineering/references/layer-progression.md`。

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

核心状态机：

```text
Entry lock
 -> Classify current layer
 -> Select primary local governance skill
 -> Name allowed companion skills
 -> Execute current layer only
 -> Transition gate
 -> Review / Next
```

这个模型比 OpenSpec 的 change lifecycle、Superpowers 的 workflow chain、GStack 的 delivery loop 都更“治理型”：它不只问“下一步做什么”，还问“当前证据是否允许进入下一层”。

### 3.2 Skills 分组

| 能力域 | 本地 skills | 当前作用 |
|---|---|---|
| 入口与透明度 | `skill-use-transparency`, `harness-engineering` | 显式说明 skill 选择；优先入口锁；判断当前 layer；防 companion workflow 抢入口。 |
| 导览与事实 | `codebase-orientation`, `find-docs`, `observable-fact-discovery` | 陌生仓库导览；外部文档查询；把未知行为变成可复查事实。 |
| 想法到 brief | `brainstorm-to-brief` | 把模糊想法收敛成 goal、non-goal、risk、success criteria。 |
| 架构与决策 | `architecture-boundary-design`, `adr-writing`, `implementation-detail-timing` | 固定边界、职责、数据流、ADR 候选和细节冻结时机。 |
| 契约优先 | `contract-first-development`, `contract-growth-control` | 先固定 schema、fixture、probe、check、acceptance；防止无限补契约不实现。 |
| 实现准入 | `implementation-readiness-gate`, `governed-implementation-entry` | target-local readiness；Implementation Entry Record 作为进入产品实现的机械凭证。 |
| 实现质量 | `agent-role-isolation`, `code-quality-drift-guard`, `agent-mistake-guard`, `doc-comment-policy` | 角色隔离；防代码/文档漂移；沉淀 agent 错误；规范语言原生 doc comments。 |
| 验证收口 | `review-next-governance`, `document-gardener`, `debugging-checklist` | 完成证据、风险、next queue、done archive、文档漂移、调试 handoff。 |
| 状态与自治 | `autonomous-ready-loop`, `harness-status-dashboard`, `harness-visualization` | fresh worker 循环、checkpoint、queue 状态、Markdown/JSON/CLI 仪表。 |
| 计划与执行包装 | `planning-with-files`, `execution-prompt-authoring` | 无队列项目的文件化计划 fallback；将计划/packet 转成可审计 prompt pack。 |

## 4. 与 OpenSpec 对比

### 4.1 OpenSpec 画像

公开资料中，OpenSpec 定位为面向 AI coding assistants 的轻量 spec-driven development 框架。典型流程是创建 change，生成 proposal/specs/design/tasks，执行 apply，完成后 archive。它强调 spec 与代码同仓、spec delta、brownfield 友好、跨多种 AI coding tools。

### 4.2 差异表

| 维度 | OpenSpec | 当前本地 harness |
|---|---|---|
| 核心目标 | 让 AI 在写代码前与人对齐 spec，保留 in-repo spec context。 | 控制 agent 从想法到实现到验证的层级推进，避免跳层、越权和自测自收。 |
| 典型 lifecycle | propose / specs / design / tasks / apply / archive。 | intake / fact / brainstorm / brief / architecture / ADR / contract / readiness / implementation / verification / review-next。 |
| artifact 形态 | `openspec/changes/<id>/...` 或类似 change folder。 | 原生 `docs/changes/<id>/proposal.md/design.md/tasks.md/contracts.md/verification.md`，且明确不是 OpenSpec adapter。 |
| spec delta | 强。 | 已吸收为 `contracts.md` 的 `Current behavior` / `Proposed behavior / contract delta`，但不把 prose 当作可执行契约。 |
| 机械工具 | OpenSpec CLI、slash commands、init/update/apply/archive。 | repo-local scripts：routing guardrail、change packet check、entry record check、status renderer、runner assets。 |
| 多工具分发 | 强，面向多 AI coding assistants。 | 当前主要是本地 skills repo，产品化分发弱。 |
| 治理强度 | 相对轻量、迭代、spec-first。 | 更强 gate：ADR、contract、readiness、Implementation Entry Record、verification、review-next。 |
| 长任务状态 | 依赖 spec/change lifecycle。 | 更强：NEXT/checkpoint/invocation log/status JSON/done archive/autonomous loop。 |

### 4.3 结论

OpenSpec 更像 **spec artifact workflow**；本项目更像 **agent behavior governance workflow**。

当前项目已经正确选择“不做 OpenSpec 兼容目标”：README 和 `change-packet-model.md` 明确只吸收 OpenSpec-like artifact discipline，不创建/读取 `openspec/changes/*`，不暴露 `openspec init/apply/archive`。这避免了双 source of truth，也避免了外部 lifecycle 绕过本地 readiness / entry record。

可改进点不是“兼容 OpenSpec”，而是把 OpenSpec 的优点继续内化为：

1. 更严格的 packet schema / spec delta lint。
2. 更好的 packet 初始化与 archive UX。
3. 更清晰的 change index / active change discovery。
4. 更适合团队使用的 install/update/check 命令。

## 5. 与 Superpowers 对比

### 5.1 Superpowers 画像

Superpowers 定位为 agentic skills framework & software development methodology，核心动作包括 brainstorming、writing/executing plans、TDD、systematic debugging、verification before completion、code review、parallel/subagent development、worktree/branch finish 等。它是方法论 + skill pack，强在让通用 coding agent 具备更稳定的软件工程习惯。

### 5.2 差异表

| 维度 | Superpowers | 当前本地 harness |
|---|---|---|
| 核心目标 | 给 AI coding agent 注入通用工程方法论。 | 给本地 agent 工作流加入口主权、层级治理和证据约束。 |
| 触发风格 | workflow/skill 强触发，部分技能可能声明 before any response / MUST。 | `harness-engineering` 拥有入口锁；Superpowers 只能 companion-only。 |
| 计划 | writing-plans / executing-plans。 | `planning-with-files`、project queue、change packet、execution prompt pack，且通过 carrier decision 选唯一 source of truth。 |
| TDD | red/green/refactor 明确。 | 已吸收到 `contract-first-development/references/tdd-contract-cycle.md`，但必须经过 Contract -> Implementation -> Verification。 |
| Debugging | systematic debugging。 | 已吸收到 `observable-fact-discovery/references/debugging-fact-workflow.md`，主动 debug 先事实发现。 |
| Verification | verification-before-completion。 | `review-next-governance` 要求 fresh completion evidence、skipped/fail 风险记录。 |
| 多 agent | dispatching parallel agents / subagent-driven development。 | `agent-role-isolation` + `execution-prompt-authoring` + Integrator 串行整合边界。 |
| Worktree/branch finish | 明确 workflow。 | 只作为可选 execution mode；不默认 worktree，不自动 commit/push。 |

### 5.3 结论

当前项目对 Superpowers 的处理是正确的：**借动作，不借主权**。

`superpowers-routing.md` 已明确：

- `superpowers:*` 不是 layer owner。
- companion terminal state、required sub-skill、default artifact path、commit/worktree/branch finish 都不能直接执行。
- 借用动作必须落到本地 owner、stable evidence 和 verification path。

这比直接安装 Superpowers 更适合当前 repo 的治理目标，因为本项目已经有比 Superpowers 更细的 layer map 和更强的 implementation gate。

可继续改进的是：减少重复口头规则，增加更多机械检查，确保 future skills 也遵守 companion-only 边界。

## 6. 与 GStack 对比

### 6.1 GStack 画像

公开资料中，GStack / gstack 被描述为 Garry Tan 的 AI development workflow / Claude Code and Codex workflow skill pack。其核心是用角色化的软件团队来驱动交付，典型七阶段为：

```text
Think -> Plan -> Build -> Review -> Test -> Ship -> Reflect
```

常见角色或命令包括 office-hours、CEO/product review、engineering review、design review、engineer、staff engineer review、QA、performance、release、SRE、retro、technical writer 等。它的优势是“像一个虚拟软件团队”：角色清晰、阶段命名直觉、面向交付闭环，尤其强调 review、QA、ship、monitor、retro。

### 6.2 差异表

| 维度 | GStack | 当前本地 harness |
|---|---|---|
| 核心叙事 | 虚拟软件团队；角色化交付。 | 本地治理内核；层级 gate 和证据链。 |
| 主流程 | Think / Plan / Build / Review / Test / Ship / Reflect。 | Intake / Idea / Fact / Brief / Architecture / ADR / Contract / Readiness / Implementation / Verification / Review-Next。 |
| 角色模型 | CEO、EM、Designer、Engineer、Staff Engineer、QA、Release、SRE、Writer 等。 | Planner、Contract/Test Writer、Implementer、Reviewer/Verifier、Integrator 等角色隔离。 |
| 用户体验 | 命令和阶段名更像真实团队流程，适合非流程专家。 | 概念更严谨，但学习曲线高，层级多。 |
| QA / Ship | 浏览器 QA、release checklist、monitor、retro 叙事较强。 | verification/review-next 强，但缺少专门 QA、release、monitor、retro skills。 |
| 治理防线 | 依靠角色职责、review/test/ship gate。 | 依靠入口锁、readiness、entry record、contract、机械检查、状态持久化。 |
| 长任务自治 | 角色/命令式推进。 | `autonomous-ready-loop` fresh workers + checkpoint + status JSON 更强。 |

### 6.3 结论

GStack 更像 **delivery operating model**；本项目更像 **governance kernel**。

本项目缺的不是 GStack 的全部角色，而是 GStack 在“交付后半段”的几个具体能力：

1. QA Lead：真实运行、浏览器/CLI/端到端场景验证。
2. Release Engineer：发布前检查、版本/文档/CI/回滚/健康检查。
3. SRE / Monitor：上线后错误、关键路径、日志、指标观察。
4. Retro / Technical Writer：完成后把经验和文档更新纳入固定闭环。

这些可以作为本地 owner skill 的增强，而不需要引入 GStack 主流程。例如：

- QA 能力归入 `review-next-governance` 或新增 `qa-verification`。
- Release 能力归入 `review-next-governance` 的 branch finish / release evidence。
- Monitor 能力归入 `observable-fact-discovery` + `harness-status-dashboard`。
- Retro 能力归入 `agent-mistake-guard` + `document-gardener`。

## 7. 三者组合 vs 当前 harness

| 能力 | OpenSpec + Superpowers + GStack | 当前本地 harness |
|---|---|---|
| 需求对齐 | OpenSpec proposal/spec，Superpowers brainstorming，GStack office-hours/CEO review。 | `brainstorm-to-brief` + `architecture-boundary-design` + ADR，更严谨但更重。 |
| 计划执行 | OpenSpec tasks/apply，Superpowers planning/executing，GStack Plan/Build。 | carrier decision + change packet + prompt pack + readiness + entry record。 |
| 角色分工 | Superpowers subagents，GStack 虚拟团队角色。 | `agent-role-isolation` + execution matrix + Integrator。 |
| TDD / contract | Superpowers TDD，OpenSpec spec delta。 | `contract-first-development`，并要求契约证据先于实现。 |
| QA / verification | Superpowers verification，GStack QA/Test/Ship。 | verification + review-next + status dashboard；缺专门 QA/Ship skill。 |
| 发布与监控 | GStack Ship/Monitor/Reflect 更完整。 | 当前是 not-now；没有 CI/release/monitor 专项。 |
| 状态持久化 | OpenSpec artifacts + GStack stage outputs。 | NEXT/checkpoint/invocation log/done archive/status JSON 更强。 |
| 产品化分发 | 三者更强，尤其 OpenSpec CLI、Superpowers plugin、GStack install story。 | 本地 repo 强，外部分发弱。 |
| 防越权 | 外部组合可能互相抢流程主权。 | 本项目有明确 companion-only containment。 |

总体判断：

> OpenSpec + Superpowers + GStack 的组合更像“完整 AI 软件开发方法论套装”；当前 `E:\my-skills` 更像“保证这些方法论不会越权、不会跳层、不会把聊天结论误当产品证据的本地治理内核”。

## 8. 当前主要优势

### 8.1 治理主权明确

`AGENTS.md` 和 `harness-engineering` 明确规定：开发、规划、实现、调试、验证、review、继续/下一步等请求先经过 `skill-use-transparency` 和 `harness-engineering`。这比直接叠加多个外部 skill pack 更安全，因为外部 workflow 的 `MUST`、terminal state、next skill transition 都会先被翻译成本地 layer 候选。

### 8.2 层级比外部组合更细

OpenSpec 的 change lifecycle、Superpowers 的 workflow 链、GStack 的七阶段都很实用，但它们不一定区分：

- Fact Discovery 是否已完成。
- Architecture 与 ADR 是否已固定。
- Contract 是否可执行或可复查。
- Readiness 是否通过。
- Implementation Entry Record 是否存在。

本项目把这些拆成显式层级，适合长期、复杂、多 session 的 agent 工程。

### 8.3 长任务自治和状态可视化是差异化能力

`autonomous-ready-loop` + `harness-visualization` 能通过 fresh worker、checkpoint、invocation log、status JSON/Markdown 管理长任务。这不是 OpenSpec/Superpowers/GStack 默认都具备的能力。

### 8.4 已经有机械检查

当前 `npm run check:all` 包括：

- routing guardrail；
- runner verification preset 测试；
- change packet 模板与检查；
- governance docs 测试；
- status renderer 测试；
- PowerShell parity 测试；
- entry record 测试。

这让治理规则不只停留在 prompt 文案。

## 9. 当前剩余风险

### P1：README / skill inventory 仍是人工维护

`AGENTS.md` 要求新增、删除、修改非 `.system` skill 时同步 README，但当前缺少独立 inventory checker 自动校验：

- README 是否覆盖所有 `**/SKILL.md`。
- 启用数量是否准确。
- 是否登记了已删除/禁用 skill。
- 重要 scripts / assets / references 是否漂移。

这已经在 `剩余整改项.md` 里列为“部分完成”。建议提升到近期 P1，因为 skill 数量已经达到 25，人工同步会越来越容易漂移。

### P1：`check:entry-record` 只检查硬编码文件

当前 `package.json` 中：

```json
"check:entry-record": "node governed-implementation-entry/scripts/check-entry-record.mjs cc-gpt整改记录.md"
```

这能证明当前样例记录有效，但不能发现未来新增 Implementation Entry Record 时的漂移。建议改为：

- 支持扫描根目录 `*整改记录.md`；或
- 支持显式配置 entry record list；或
- 在 change packet / queue 中登记 active entry record，再由 checker 读取。

### P1：Dashboard / Visualization 仍有规范重复

虽然职责已拆分为：

- `harness-status-dashboard`：解释/诊断/human-needed 判断；
- `harness-visualization`：默认 renderer / JSON contract；

但两个 skill 中仍有部分 display hard rule 重复。建议把显示 contract 集中到 `harness-visualization/references/status-contract.md`，dashboard 只引用它，避免后续文案分叉。

### P2：缺少 GStack 式 QA / Ship / Monitor / Retro 专项

当前 verification 已强，但更偏“命令和证据”；GStack 的后半段提醒了几个缺口：

- 真实运行或浏览器 QA 的角色化检查。
- release readiness checklist。
- deploy 后 health / log / metric 观察。
- retro 和文档更新闭环。

建议不要一次性引入大而全 GStack adapter，而是按本地 owner 增量吸收。

### P2：CI / PR 协作仍是 not-now

本地检查入口已有，但没有 GitHub Actions / CI workflow。对个人本地 repo 没问题；如果要多人共享或作为 skill pack 发布，就会变成协作风险。

### P2：跨工具分发和安装 UX 弱

OpenSpec 有 CLI，Superpowers 有 Claude plugin/marketplace story，GStack 有 install story。当前项目只有 repo-local skills 和 README，缺：

- version manifest；
- install/update 脚本；
- host compatibility matrix；
- release checklist；
- onboarding / quickstart；
- examples gallery。

### P3：领域专项能力少

README 已列明当前缺口：前端 UI、后端框架、数据库迁移、认证授权、CI 修复、语言生态重构/测试/性能分析等。建议按高频问题逐个补，不要为了覆盖面膨胀。

## 10. 推荐改进路线图

## P0：保持现状，不再引入外部主流程

当前不建议做：

- OpenSpec adapter；
- Superpowers adapter；
- GStack adapter；
- 兼容 `openspec/` 目录；
- 接受外部 workflow terminal state；
- 自动 apply/archive/ship/commit/push。

理由：当前最大价值是本地治理主权。直接兼容外部主流程会重新引入多 source of truth 和流程抢入口风险。

## P1：补机械一致性检查

### 1. 新增 README / inventory checker

建议脚本：

```text
scripts/check-skill-inventory.mjs
```

检查：

- `**/SKILL.md` 数量与 README “启用非 system skills”一致。
- README 功能表包含每个 skill 名称。
- README “重要资产”中列出的 scripts/assets/references 存在。
- 删除/禁用的旧 skill 不应出现在启用表。
- 每个非 system skill 有 `Harness Precondition` 或被明确豁免。

接入：

```json
"check:inventory": "node scripts/check-skill-inventory.mjs",
"check:all": "npm run check:routing && npm test && npm run check:packets && npm run check:entry-record && npm run check:inventory"
```

### 2. 改进 entry record checker

将 `check:entry-record` 从硬编码 `cc-gpt整改记录.md` 改为：

- 扫描 `*整改记录.md`；或
- 支持 `--all-known`；或
- 支持 `--from README/queue/config`。

目标是让未来新增实现记录时不会漏检。

### 3. 抽出 status contract reference

新增：

```text
harness-visualization/references/status-contract.md
```

内容包括：

- compact panel 必需字段；
- task packet checklist 展示规则；
- legacy `[done]` 迁移 warning；
- status JSON 字段稳定性；
- dashboard 与 renderer 的职责边界。

然后让 `harness-status-dashboard/SKILL.md` 和 `harness-visualization/SKILL.md` 引用同一 reference。

## P2：吸收 GStack 后半段能力，但保留本地 owner

### 4. 增强 QA verification

选择一：新增 `qa-verification` skill。  
选择二：扩展 `review-next-governance`。

建议内容：

- 真实运行 app / CLI / TUI 的 smoke path。
- 浏览器或截图证据规则。
- 用户关键路径 checklist。
- regression coverage 要求。
- fail / skipped 时如何记录 residual risk。

边界：QA 不批准新 scope；QA 失败回到最低 owning layer。

### 5. 增强 release readiness

扩展 `review-next-governance/references/completion-review-branch.md`，加入 GStack Ship 的本地版本：

- git status；
- tests/checks；
- docs updated；
- version/changelog if applicable；
- CI state if available；
- rollback / disable path if outward-facing；
- user approval before push/deploy。

### 6. 增强 monitor / retro

将 GStack Monitor / Reflect 拆给已有 owner：

- `observable-fact-discovery`：上线后日志、错误、指标、用户路径观察。
- `harness-status-dashboard`：runner/queue/verification stale 诊断。
- `agent-mistake-guard`：把重复 agent 错误变成 guardrail。
- `document-gardener`：把稳定经验写回 README/ADR/contract/queue。

## P2：做发布前本地 UX，而不是 marketplace

### 7. 新增 quickstart / compatibility matrix

新增：

```text
docs/quickstart.md
docs/compatibility.md
```

内容：

- 如何把这套 skills 放到 Claude Code / Codex / OpenCode 等 host。
- 哪些 skill 依赖 host-specific 能力。
- `find-docs` 对外部 `openai-docs` 的 fallback。
- Windows / PowerShell 与 POSIX shell 差异。
- 最小检查命令：`npm run check:all`。

### 8. 新增 examples gallery

把几类典型任务写成短例子：

- 模糊想法 -> brief。
- 外部 API 未知 -> fact discovery。
- 多模块变更 -> change packet。
- 实现前 -> readiness + entry record。
- 长任务 -> autonomous ready loop。
- 完成后 -> review-next + status dashboard。

这能降低学习曲线，弥补 GStack 在命令直觉性上的优势。

## P3：按实际频率新增领域专项

不要为了对齐外部组合而一次性新增大量 skills。建议只在重复出现 3 次以上时新增：

- CI failure triage；
- frontend UI QA；
- database migration safety；
- auth/authz review；
- performance profiling；
- security review adapter；
- release/deploy monitor。

每个新增 skill 必须满足：

- 有 Harness Precondition；
- README 登记；
- 有 local owner 和 forbidden transition；
- 有最小 mechanical check 或明确不可机械检查的原因；
- 不引入外部 workflow 主权。

## 11. 最小可执行整改清单

如果只做最划算的 6 项：

1. **新增 `check-skill-inventory.mjs` 并接入 `check:all`**。  
   解决 README / skill 表 / assets 漂移。

2. **改造 `check:entry-record`，不要只检查 `cc-gpt整改记录.md`**。  
   解决未来 entry record 漏检。

3. **抽出 `status-contract.md`**。  
   解决 dashboard / visualization 规范重复。

4. **在 `review-next-governance` 增加 QA / release evidence 小节**。  
   吸收 GStack Test / Ship 优势，不新增流程主权。

5. **新增 quickstart / compatibility matrix**。  
   补产品化 UX 的第一步，不急着做 marketplace。

6. **新增 examples gallery**。  
   让 25 个 skills 的使用方式可学习、可复制、可审计。

## 12. 审计判断

当前仓库已经完成了从“提示词集合”到“治理型 harness”的关键转变。上一轮 `cc-gpt审计.md` 里的高风险项大多已修复，并有测试覆盖。

下一阶段不应追求“更多外部流程兼容”，而应追求：

- **更少人工同步**：inventory、entry record、status contract 机械化。
- **更好交付后半段**：QA、release、monitor、retro 的本地化吸收。
- **更低学习曲线**：quickstart、compatibility、examples。
- **更稳的 companion containment**：任何 OpenSpec / Superpowers / GStack 技巧都只能作为本地 layer 的辅助能力，不能越过 Architecture、ADR、Contract、Readiness、Implementation Entry Record、Verification 或 Review / Next。

## 13. 外部来源

- [OpenSpec official/pro site](https://openspec.pro/)
- [OpenSpec dev site](https://openspec.dev/)
- [OpenSpec GitHub — Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec)
- [Superpowers official site](https://superpowers.apposters.com/)
- [Superpowers Claude Plugin listing](https://claude.com/plugins/superpowers)
- [Superpowers GitHub — obra/superpowers](https://github.com/obra/superpowers)
- [gstack official-style landing page](https://gstack.lol/)
- [The Dench Blog — gstack explained](https://www.dench.com/blog/gstack-explained)
