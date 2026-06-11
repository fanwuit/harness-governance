# Codex Skills

这个目录保存本机可用的 Codex skills。除 `.system` 外，当前启用的 skills 主要是一套面向长期 agent 工程的 harness / governance 能力：把想法逐层推进到可验证实现，并通过契约、准入、验证、队列、文档和自治 runner 控制漂移。

## 总览

- 启用的非 system skills：25 个。
- 额外存在 `gh-fix-ci`，但入口文件是 `SKILL.disabled.md`，当前不作为启用 skill 自动触发。
- 这些 skills 偏流程、边界、契约和治理，不是某个编程语言或框架的代码片段库。
- change packet 只吸收 OpenSpec-like artifact discipline：标准 proposal/design/tasks/contracts/verification 资产形态、contract delta 表达和机械检查；OpenSpec 不是 dependency、入口或兼容目标。

## 核心链路

`harness-engineering` 是开发、规划、实现、调试、TDD、验证、review、队列、handoff、skill 更新、新项目、creative work 和继续/下一步请求的优先入口锁与层级路由。它先判断本地治理层级和义务，再决定是否使用 companion workflow。任何 `superpowers:*`、`superpowers:using-superpowers` 或其他 companion workflow 看起来适用时，都不能越过 `skill-use-transparency` 和 `harness-engineering`。

当前 harness 入口按硬状态机执行：

```text
Entry lock
 -> Classify current layer
 -> Select primary local governance skill
 -> Name allowed companion skills
 -> Execute current layer only
 -> Transition gate
 -> Review / Next
```

companion workflow 只能作为能力插件。其 `MUST`、terminal state、`REQUIRED SUB-SKILL`、next-skill transition、默认 artifact 路径或 commit 要求，都必须先翻译成 harness 下一层候选，不能直接执行。

`harness-engineering` 定义了主要工程层级：

```text
Intake / Orientation
 ->
Idea
 -> Fact Discovery, when material unknowns exist
 -> Brainstorming
 -> Brief
 -> Architecture
 -> ADR
 -> Contract
 -> Implementation Readiness
 -> Implementation
 -> Verification
 -> Review / Next
```

完整顺序以 `harness-engineering/references/layer-progression.md` 为唯一 source of truth。每一层都应该产出可持久化证据，例如 brief、架构摘要、ADR、schema、fixture、probe、check、readiness evidence、测试输出或队列记录。重要结论不应只留在聊天里。

## 已包含的功能

| 能力域 | Skills | 功能 | 是否启用 |
|---|---|---|---|
| Harness 总流程 | `harness-engineering` | 优先入口锁和硬状态机；判断当前层级、下一层级和本地治理 skill 的顺序，防止 companion workflow 抢入口或从想法/事实发现直接跳到无契约实现。 | 是 |
| 需求收敛 | `brainstorm-to-brief` | 把模糊想法收敛成 brief，固定目标、非目标、方案取舍、风险、成功标准和下一层；可借用 `superpowers:brainstorming` 的提问、方案比较、scope decomposition 和 visual companion 技巧，但不接受其 terminal state。 | 是 |
| 事实发现 | `observable-fact-discovery` | 把未知行为、日志、fixture、probe、外部能力调查成可复查事实，区分事实、假设和推断。 | 是 |
| 架构边界 | `architecture-boundary-design` | 从 brief 推出组件职责、数据流、运行时/部署边界、ADR 候选和 contract 候选。 | 是 |
| 决策记录 | `adr-writing` | 记录长期架构决策、技术选择、备选方案、后果、约束和验证方式。 | 是 |
| 契约优先 | `contract-first-development` | 在实现前固定 schema、example、fixture、probe、check、失败路径和验证命令。 | 是 |
| 契约膨胀控制 | `contract-growth-control` | 防止一直补 ADR/schema/check/readiness 而不进入最小实现切片。 | 是 |
| 实现细节时机 | `implementation-detail-timing` | 判断类名、模块名、字段、表、迁移、依赖规则等应在哪个层级固定。 | 是 |
| 实现入口 | `governed-implementation-entry` | 在写实现代码前记录 Implementation Entry Record；它是进入 product implementation 的 mechanical credential，固定当前层级、target、scope、contract evidence、readiness、packetization、verification、Review / Next 和 stop conditions。 | 是 |
| 实现准入 | `implementation-readiness-gate` | 进入 target 实现前检查架构、ADR、contract、lint、测试 baseline、验证命令和本地 agent 规则。 | 是 |
| 角色隔离 | `agent-role-isolation` | 分离 Planner、Contract/Test Writer、Implementer、Reviewer/Verifier，降低自测自收和范围膨胀风险。 | 是 |
| 验证收口 | `review-next-governance` | 完成后更新 NEXT scheduler、done archive、backlog、blocked/not-now，记录验证证据、剩余风险和下一步。 | 是 |
| 自治执行 | `autonomous-ready-loop` | 用外部 runner 反复启动短 `codex exec` worker，按 ready 队列推进并写 checkpoint。 | 是 |
| 状态仪表 | `harness-status-dashboard` | 汇总 scheduler ready、done archive、target、contract、runner marker、验证新鲜度、漂移和是否需要人工输入；dashboard 负责解释/诊断，不默认复制 report 脚本。 | 是 |
| 可视化状态 | `harness-visualization` | 默认实现：从 NEXT scheduler、done archive、change packet、checkpoint 和 invocation log 生成只读 text/markdown dashboard、CLI 紧凑面板与 JSON 状态，展示 layer、ready、archive、task packet checklist、runner 和 verification。 | 是 |
| 文档治理 | `document-gardener` | 审计和修正文档、ADR、队列、索引、检查注册与当前代码/验证状态之间的漂移。 | 是 |
| 错误沉淀 | `agent-mistake-guard` | 把重复 agent 错误沉淀为短小 guardrail，必要时升级成机械检查。 | 是 |
| 代码质量漂移 | `code-quality-drift-guard` | 检查孤儿脚本、孤儿 wrapper、命名漂移、重复 helper、文件膨胀和未引用候选。 | 是 |
| 文档注释规范 | `doc-comment-policy` | 标准化类、接口、方法、函数、参数和返回值的语言原生 doc comment，避免“功能/入参/出参”模板破坏生成文档。 | 是 |
| 文件化计划 | `planning-with-files` | 用 `task_plan.md`、`findings.md`、`progress.md` 做持久计划、进度记录和上下文恢复。 | 是 |
| 执行提示词编写 | `execution-prompt-authoring` | 把已确认的计划、gate、队列项或 change packet 转成可审计的 controller、worker、subagent audit 和 integrator prompt pack。 | 是 |
| Skill 透明度 | `skill-use-transparency` | 要求说明选择了哪个 skill、为什么触发、是否成功读取 `SKILL.md`、是否完整执行。 | 是 |
| 代码库导览 | `codebase-orientation` | 给陌生仓库快速梳理模块、入口、运行/测试命令和安全入门任务。 | 是 |
| 调试交接 | `debugging-checklist` | 输出轻量调试 checklist，用于人类或初级开发者 handoff。 | 是 |
| 外部技术文档 | `find-docs` | 用 Context7 查询非 OpenAI 技术文档和 API 示例；OpenAI/Codex 问题依赖外部/system `openai-docs`，缺失时说明不可用并使用 official OpenAI docs fallback。 | 是 |
| CI 修复 | `gh-fix-ci` | 使用 GitHub CLI 检查 PR checks 和 GitHub Actions 失败日志；当前入口为 `SKILL.disabled.md`。 | 否 |

## 重要资产

### `planning-with-files`

提供持久计划模板和脚本：

- `templates/task_plan.md`
- `templates/findings.md`
- `templates/progress.md`
- `scripts/init-session.*`
- `scripts/set-active-plan.*`
- `scripts/resolve-plan-dir.*`
- `scripts/check-complete.*`
- `scripts/session-catchup.py`
- `scripts/attest-plan.*`
- `tests/powershell-parity.test.mjs`
- `reference.md`
- `examples.md`

适合没有现成 `NEXT.md`、checkpoint 或项目队列系统的复杂多步任务。

### `autonomous-ready-loop`

提供自治 runner 模板：

- `assets/run-autonomous-ready-loop.ps1`
- `assets/run-autonomous-ready-loop.sh`
- `references/runner-contract.md`
- `tests/runner-verification-command.test.mjs`

目标是让长任务由多个短 `codex exec` worker 通过仓库文件交接，而不是依赖单个长聊天上下文。runner 模板会在每轮完成或 checkpoint 写入后尝试调用通用 `harness-visualization` 刷新 `.harness/status.md` 和 `.harness/status.json`，并在 CLI/对话中展示紧凑状态面板；找不到脚本时只警告，避免把可视化依赖变成 worker 主流程阻断点。`NEXT.md` 应保持为 scheduler，只保留 `[ready]` 和必要时短暂 `[active]`；已完成历史进入 `docs/changes/archive/` 或项目 done 记录。

runner 的 `VerificationCommand` 只能使用受控 preset 名称，例如 `routing-guardrails`、`harness-visualization-tests`、`all-local-checks`；不要把未审计 shell 字符串从 queue、config 或环境变量透传给 runner 执行。

### `governed-implementation-entry`

提供实现入口记录检查：

- `scripts/check-entry-record.mjs`
- `tests/check-entry-record.test.mjs`

该脚本只检查 Implementation Entry Record 的必需字段是否存在且非空，并确认 readiness / packetization 字段包含允许值；它不证明 gate 内容正确。

### `implementation-readiness-gate`

提供 target 准入参考：

- `references/checklist.md`
- `references/java-backend-target.md`
- `references/web-frontend-target.md`
- `references/worker-runtime-target.md`
- `references/shared-package-target.md`

用于进入具体 target 实现前确认架构、契约、lint、测试、验证命令和本地规则是否齐备。

### `harness-engineering`

提供全局路由参考：

- `references/layer-progression.md`
- `references/superpowers-routing.md`
- `references/change-packet-model.md`
- `templates/change-packet/proposal.md`
- `templates/change-packet/design.md`
- `templates/change-packet/tasks.md`
- `templates/change-packet/contracts.md`
- `templates/change-packet/verification.md`
- `scripts/check-routing-guardrails.py`
- `scripts/init-change-packet.mjs`
- `scripts/check-change-packet.mjs`
- `tests/governance-docs.test.mjs`
- `tests/change-packet.test.mjs`

用于判断当前层级、下一步和与可选 companion skills 的关系。开发、规划、实现、调试、TDD、验证、review、队列、handoff、skill 更新、新项目、creative work 和继续/下一步请求必须优先选择并读取 `harness-engineering`。与 `superpowers:*` 等 companion workflow 重叠时，先由本地 skill 决定层级、边界、角色隔离、准入、契约、验证和 review/next 义务；companion workflow 只在治理规则明确后辅助执行。

change packet 模板用于初始化原生 `docs/changes/<id>/`，包含 `proposal.md`、`design.md`、`tasks.md`、`contracts.md` 和 `verification.md`。`contracts.md` 固定 `Current behavior`、`Proposed behavior / contract delta`、`Acceptance checks` 和 `Failure cases`，但文档说明不能替代可执行 schema、fixture、probe、check 或 acceptance test。

`scripts/check-routing-guardrails.py` 用于机械检查：

- 本地启用 skill 是否缺少 `Harness Precondition` 自守层。
- `AGENTS.md`、`harness-engineering/SKILL.md`、`references/superpowers-routing.md` 是否保留 `superpowers:using-superpowers`、terminal state、`REQUIRED SUB-SKILL` 和 companion adapter 规则。
- 本地 skill 是否出现未被 containment 解释的高风险 routing 触发词。
- README 和 `harness-engineering/SKILL.md` 是否遗漏 canonical layer term，或保留未标注为简化视图的旧层级链路。

规则不依赖具体安装目录，应使用当前会话暴露的 skill 名称和路径。

`scripts/init-change-packet.mjs` 用本项目模板初始化 `docs/changes/<id>/`；`scripts/check-change-packet.mjs` 校验 packet 必需文件、`tasks.md` checkbox、`contracts.md` contract artifact 或 blocked 原因、`verification.md` 验证证据、允许的 status 值，以及 archive packet 是否把稳定结论回链到 ADR、README、contract、verification、queue 或项目索引。它不执行 apply/archive，也不批准 implementation。

### `execution-prompt-authoring`

用于把已确认的 plan、gate list、NEXT ready、change packet 或 role-isolated workflow 转成可审计执行提示词包，明确 controller、subagent audit、fresh `codex exec` worker、integrator、共享文件串行规则、验证命令、停止 marker 和人工审批点。

### `harness-visualization`

提供通用 harness 状态可视化脚本：

- `scripts/harness-status.mjs`
- `tests/harness-status.test.mjs`
- `tests/fixtures/sample-repo/`

脚本默认只读扫描目标项目的 `NEXT.md`、`docs/changes/*/tasks.md`、`docs/changes/archive/*/tasks.md`、`.harness/run-checkpoint.md` 和 `.harness/codex-exec-invocations.ndjson`，输出终端文本；使用 `--format json` 可供 agent、TUI 或 Web UI 消费；使用 `--write-md` / `--write-json` 可写入目标项目 `.harness/status.md` 和 `.harness/status.json`，写出路径必须保留在目标 repo 内，随后仍要在 CLI/对话展示当前紧凑状态面板。面板把 `Current ready` 作为调度大项；当 ready 指向 task packet、change packet 或等价任务包时，显示任务包路径、完成数/总数，以及 `## Task checklist` 中每个 `- [ ]` / `- [x]` 状态。使用 `--init` 可生成 `.harness/harness-status.config.json`，用于覆盖 queue、change root、archive root、checkpoint、invocation log 和 status 输出路径。它只负责可见性，不推进队列、不替代 gate 或 verification。旧 `NEXT.md` 中残留的 `[done]` 会以 `legacyDoneItems` 保留并产生迁移 warning，避免历史完成项丢失。

提示词入口支持 `$harness-visualization init`：初始化目标项目 status config，刷新 `.harness/status.md` / `.harness/status.json`，并报告缺失状态源。

### 根目录检查入口

提供统一 npm scripts：

- `npm test`
- `npm run check:routing`
- `npm run check:packets`
- `npm run check:entry-record`
- `npm run check:all`

`check:all` 串联 routing guardrail、Node test suites、change packet 检查和本轮 Implementation Entry Record 检查。仓库仍不引入 npm 依赖，脚本只使用 Node.js、Python 和 PowerShell。

## 未启用但存在

### `gh-fix-ci`

目录存在，但使用 `SKILL.disabled.md`，所以当前不是启用 skill。

禁用 skill 可以保留 `agents/openai.yaml`、assets、scripts 和 LICENSE 作为待启用资产；任何 discovery 或 marketplace 同步逻辑必须先确认入口文件是 `SKILL.md`，不能只因为 manifest 存在就把 disabled skill 当成已启用。

它的说明显示目标能力是：

- 使用 GitHub CLI 检查 PR checks。
- 聚焦 GitHub Actions 失败日志。
- 摘要失败上下文。
- 先提出修复计划，得到明确批准后再实现。

如果需要启用，应先确认它是否仍符合当前 skill 规范，再把入口恢复为 `SKILL.md` 并验证其脚本和权限边界。

## 使用建议

- 每次处理开发、规划、实现、调试、验证、review、队列、handoff、skill 更新、新项目和继续/下一步请求时，先用 `harness-engineering` 做入口路由。
- 新想法或范围不清时，由 `harness-engineering` 先路由到当前层，再进入 `brainstorm-to-brief` 等本地 skill。
- 任何 `superpowers:*` 或其他 companion workflow 看起来适用时，先选择并读取 `harness-engineering`；`superpowers:using-superpowers` 即使声明 starting any conversation / before ANY response，也不能早于 harness 入口。
- companion workflow 的 terminal state、`REQUIRED SUB-SKILL`、默认写文件/commit/next-skill 要求，只能作为 harness transition gate 的候选输入。
- 行为未知时，先用 `observable-fact-discovery` 固定事实。
- 涉及多个组件或边界时，进入 `architecture-boundary-design`，必要时再写 `adr-writing`。
- 新 API、schema、CLI、fixture、外部行为或失败路径，应先用 `contract-first-development`。
- 进入产品实现前，按 target 使用 `implementation-readiness-gate`。
- 完成后用 `review-next-governance` 更新 NEXT scheduler、done archive、风险和下一步；不要把已完成历史长期留在 `NEXT.md`。
- 长时间自治推进时，使用 `autonomous-ready-loop`、`harness-status-dashboard` 和 `harness-visualization`，分别负责执行循环、状态判断和可读/JSON 仪表输出；业务项目只暴露标准状态源，包括 scheduler queue、done archive、checkpoint、invocation log 和 change packet，通用 runner/status 脚本负责刷新可视化状态。
- 状态相关工作默认由 `harness-visualization/scripts/harness-status.mjs` 提供 visualization 默认实现；`harness-status-dashboard` 只负责 dashboard 解释/诊断、human-needed 判断和展示要求。只有状态源不标准时才补 adapter 或 `.harness/harness-status.config.json`。
- 文档、队列、索引或治理规则漂移时，使用 `document-gardener`。
- 写、审计或迁移 API/doc 生成链路上的代码注释时，使用 `doc-comment-policy`。
- 已确认的多 worker、多角色或 change packet 需要落成可审计执行提示词时，使用 `execution-prompt-authoring`。

## 当前覆盖重点与缺口

当前 skills 覆盖较强的方向：

- agent 工程层级推进。
- 契约优先和实现准入。
- 文档、队列、状态和错误沉淀。
- 长任务自治执行和 checkpoint。
- harness layer、scheduler ready 队列、done archive、task packet checklist、runner marker 和 verification 的只读可视化输出与 CLI/对话紧凑状态面板。
- OpenSpec-like artifact discipline 的本地化吸收：change packet 模板、contract delta 结构、packet 初始化与机械检查。
- 代码质量漂移的轻量检查思路。
- 代码文档注释的语言原生格式选择和防忘落地思路。
- companion workflow 抢入口的机械检查和本地 skill 自守层。

当前明显较少的方向：

- 具体前端 UI 实作专项。
- 完整 TUI / Web 控制台；当前只提供通用 text/markdown/JSON 状态层。
- 后端框架、数据库迁移、认证授权等领域专项。
- 已启用的 CI 修复专项。
- 特定语言生态的重构、测试或性能分析专项。
- 不提供 OpenSpec 安装、命令兼容、`openspec/` 目录读写、apply/archive 自动执行。

这些缺口不一定需要全部补齐；应按实际项目频率和重复问题来决定是否新增 skill。
