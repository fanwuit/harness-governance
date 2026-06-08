# Codex Skills

这个目录保存本机可用的 Codex skills。除 `.system` 外，当前启用的 skills 主要是一套面向长期 agent 工程的 harness / governance 能力：把想法逐层推进到可验证实现，并通过契约、准入、验证、队列、文档和自治 runner 控制漂移。

## 总览

- 启用的非 system skills：22 个。
- 额外存在 `gh-fix-ci`，但入口文件是 `SKILL.disabled.md`，当前不作为启用 skill 自动触发。
- 这些 skills 偏流程、边界、契约和治理，不是某个编程语言或框架的代码片段库。

## 核心链路

`harness-engineering` 定义了主要工程层级：

```text
Idea
 -> Brainstorming
 -> Brief
 -> Architecture
 -> ADR
 -> Contract
 -> Implementation
 -> Verification
 -> Review / Next
```

每一层都应该产出可持久化证据，例如 brief、架构摘要、ADR、schema、fixture、probe、check、测试输出或队列记录。重要结论不应只留在聊天里。

## 已包含的功能

| 能力域 | Skills | 功能 | 是否启用 |
|---|---|---|---|
| Harness 总流程 | `harness-engineering` | 判断当前层级、下一层级和本地治理 skill 的顺序，防止从想法或事实发现直接跳到无契约实现。 | 是 |
| 需求收敛 | `brainstorm-to-brief` | 把模糊想法收敛成 brief，固定目标、非目标、方案取舍、风险、成功标准和下一层。 | 是 |
| 事实发现 | `observable-fact-discovery` | 把未知行为、日志、fixture、probe、外部能力调查成可复查事实，区分事实、假设和推断。 | 是 |
| 架构边界 | `architecture-boundary-design` | 从 brief 推出组件职责、数据流、运行时/部署边界、ADR 候选和 contract 候选。 | 是 |
| 决策记录 | `adr-writing` | 记录长期架构决策、技术选择、备选方案、后果、约束和验证方式。 | 是 |
| 契约优先 | `contract-first-development` | 在实现前固定 schema、example、fixture、probe、check、失败路径和验证命令。 | 是 |
| 契约膨胀控制 | `contract-growth-control` | 防止一直补 ADR/schema/check/readiness 而不进入最小实现切片。 | 是 |
| 实现细节时机 | `implementation-detail-timing` | 判断类名、模块名、字段、表、迁移、依赖规则等应在哪个层级固定。 | 是 |
| 实现准入 | `implementation-readiness-gate` | 进入 target 实现前检查架构、ADR、contract、lint、测试 baseline、验证命令和本地 agent 规则。 | 是 |
| 角色隔离 | `agent-role-isolation` | 分离 Planner、Contract/Test Writer、Implementer、Reviewer/Verifier，降低自测自收和范围膨胀风险。 | 是 |
| 验证收口 | `review-next-governance` | 完成后更新 NEXT/backlog/blocked/not-now，记录验证证据、剩余风险和下一步。 | 是 |
| 自治执行 | `autonomous-ready-loop` | 用外部 runner 反复启动短 `codex exec` worker，按 ready 队列推进并写 checkpoint。 | 是 |
| 状态仪表 | `harness-status-dashboard` | 汇总 ready、target、contract、runner marker、验证新鲜度、漂移和是否需要人工输入。 | 是 |
| 文档治理 | `document-gardener` | 审计和修正文档、ADR、队列、索引、检查注册与当前代码/验证状态之间的漂移。 | 是 |
| 错误沉淀 | `agent-mistake-guard` | 把重复 agent 错误沉淀为短小 guardrail，必要时升级成机械检查。 | 是 |
| 代码质量漂移 | `code-quality-drift-guard` | 检查孤儿脚本、孤儿 wrapper、命名漂移、重复 helper、文件膨胀和未引用候选。 | 是 |
| 文件化计划 | `planning-with-files` | 用 `task_plan.md`、`findings.md`、`progress.md` 做持久计划、进度记录和上下文恢复。 | 是 |
| 执行提示词编写 | `execution-prompt-authoring` | 把已确认的计划、gate、队列项或 change packet 转成可审计的 controller、worker、subagent audit 和 integrator prompt pack。 | 是 |
| Skill 透明度 | `skill-use-transparency` | 要求说明选择了哪个 skill、为什么触发、是否成功读取 `SKILL.md`、是否完整执行。 | 是 |
| 代码库导览 | `codebase-orientation` | 给陌生仓库快速梳理模块、入口、运行/测试命令和安全入门任务。 | 是 |
| 调试交接 | `debugging-checklist` | 输出轻量调试 checklist，用于人类或初级开发者 handoff。 | 是 |
| 外部技术文档 | `find-docs` | 用 Context7 查询非 OpenAI 技术文档和 API 示例；OpenAI/Codex 问题应走 system `openai-docs`。 | 是 |
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

适合没有现成 `NEXT.md`、checkpoint 或项目队列系统的复杂多步任务。

### `autonomous-ready-loop`

提供自治 runner 模板：

- `assets/run-autonomous-ready-loop.ps1`
- `assets/run-autonomous-ready-loop.sh`
- `references/runner-contract.md`

目标是让长任务由多个短 `codex exec` worker 通过仓库文件交接，而不是依赖单个长聊天上下文。

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

用于判断当前层级、下一步和与可选 companion skills 的关系。

### `execution-prompt-authoring`

用于把已确认的 plan、gate list、NEXT ready、change packet 或 role-isolated workflow 转成可审计执行提示词包，明确 controller、subagent audit、fresh `codex exec` worker、integrator、共享文件串行规则、验证命令、停止 marker 和人工审批点。

## 未启用但存在

### `gh-fix-ci`

目录存在，但使用 `SKILL.disabled.md`，所以当前不是启用 skill。

它的说明显示目标能力是：

- 使用 GitHub CLI 检查 PR checks。
- 聚焦 GitHub Actions 失败日志。
- 摘要失败上下文。
- 先提出修复计划，得到明确批准后再实现。

如果需要启用，应先确认它是否仍符合当前 skill 规范，再把入口恢复为 `SKILL.md` 并验证其脚本和权限边界。

## 使用建议

- 新想法或范围不清时，从 `brainstorm-to-brief` 开始。
- 行为未知时，先用 `observable-fact-discovery` 固定事实。
- 涉及多个组件或边界时，进入 `architecture-boundary-design`，必要时再写 `adr-writing`。
- 新 API、schema、CLI、fixture、外部行为或失败路径，应先用 `contract-first-development`。
- 进入产品实现前，按 target 使用 `implementation-readiness-gate`。
- 完成后用 `review-next-governance` 更新队列、风险和下一步。
- 长时间自治推进时，使用 `autonomous-ready-loop` 和 `harness-status-dashboard`。
- 文档、队列、索引或治理规则漂移时，使用 `document-gardener`。
- 已确认的多 worker、多角色或 change packet 需要落成可审计执行提示词时，使用 `execution-prompt-authoring`。

## 当前覆盖重点与缺口

当前 skills 覆盖较强的方向：

- agent 工程层级推进。
- 契约优先和实现准入。
- 文档、队列、状态和错误沉淀。
- 长任务自治执行和 checkpoint。
- 代码质量漂移的轻量检查思路。

当前明显较少的方向：

- 具体前端 UI 实作专项。
- 后端框架、数据库迁移、认证授权等领域专项。
- 已启用的 CI 修复专项。
- 特定语言生态的重构、测试或性能分析专项。

这些缺口不一定需要全部补齐；应按实际项目频率和重复问题来决定是否新增 skill。
