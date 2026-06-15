# cc-gpt 项目审计结果

> 目标：全面审计 `E:\my-skills`，并与 OpenSpec + Superpowers 组合进行对比。  
> 说明：本审计基于本地仓库只读检查、脚本/测试运行、子代理审计，以及联网查询 OpenSpec / Superpowers 截至 2026-06 的公开资料。工作区在审计时为 clean；本文件为审计结果落盘。

## 1. 一句话结论

`E:\my-skills` 不是普通 skills 集合，而是一套偏 **agent governance harness** 的本地能力层：它通过入口路由、层级推进、契约优先、实现准入、角色隔离、队列、checkpoint、done archive、自治 runner 和状态可视化来控制 AI coding agent 的漂移。

与 **OpenSpec + Superpowers** 相比：

- 你的项目在 **治理强度、长任务自治、状态持久化、review/next 收口、防 companion workflow 抢入口** 上更强。
- OpenSpec + Superpowers 在 **产品化、安装体验、生态可见度、多工具分发、官方 plugin/CLI 形态** 上更强。
- 最适合的定位不是替代 OpenSpec/Superpowers，而是作为它们之上的或旁路的 **local governance harness / adapter layer**。

## 2. 本地验证结果

| 检查 | 结果 |
|---|---|
| `node --test harness-visualization\tests\harness-status.test.mjs` | 8/8 pass |
| `python harness-engineering\scripts\check-routing-guardrails.py` | pass |
| `node governed-implementation-entry\scripts\check-entry-record.mjs README.md` | fail as expected：README 不是 Implementation Entry Record |
| `git status --short` | clean |

## 3. 项目能力画像

当前项目 README 描述其为本机可用 Codex skills 集合，启用非 system skills 25 个，主要面向长期 agent 工程的 harness / governance 能力，而不是语言或框架代码片段库。

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

主要能力域：

- `harness-engineering`：入口锁与层级路由。
- `brainstorm-to-brief`：想法收敛为 brief。
- `observable-fact-discovery`：事实发现，防止假设进入实现。
- `architecture-boundary-design`：架构边界。
- `adr-writing`：长期决策记录。
- `contract-first-development`：契约优先。
- `implementation-readiness-gate`：实现准入。
- `governed-implementation-entry`：实现入口记录。
- `agent-role-isolation`：规划、契约、实现、验证角色隔离。
- `review-next-governance`：完成后证据、风险、下一步收口。
- `autonomous-ready-loop`：短 worker 自治推进。
- `harness-visualization`：只读状态仪表，输出 text/markdown/JSON。
- `planning-with-files`：无队列项目的持久计划 fallback。
- `execution-prompt-authoring`：把已批准计划/队列/packet 转为可审计 prompt pack。
- `skill-use-transparency`：skill 使用透明度。

## 4. 强项

### 4.1 入口治理强

项目明确规定开发、规划、实现、调试、验证、review、队列、handoff 等请求必须先经过 `skill-use-transparency` 与 `harness-engineering`。

`superpowers:*` 只能作为 companion workflow；即使其自身声明 “before any response” 或强制触发，也不能抢本地 harness 入口。

### 4.2 层级比 OpenSpec 更细

本地 canonical progression 包含：

```text
Intake / Orientation
 -> Idea
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

这比 OpenSpec 常见的 proposal / apply / archive 更细，更适合控制 agent 长任务中的跳层、扩大范围和自测自收。

### 4.3 change packet 抽象正确

项目的 change packet 不是 gate，而是 carrier：用于承载复杂变更上下文。建议结构：

```text
docs/changes/
  <change-id>/
    proposal.md
    design.md
    tasks.md
    contracts.md
    verification.md
  archive/
    <YYYY-MM-DD>-<change-id>/
      proposal.md
      design.md
      tasks.md
      contracts.md
      verification.md
```

这个模型比直接照搬 OpenSpec 更贴合本项目：OpenSpec-like artifact 可进入本地 harness，但不能替代 ADR、contract、readiness 和 verification。

### 4.4 长任务自治与可观测性是差异化优势

`autonomous-ready-loop` 通过外部 runner 反复启动短 `codex exec` worker，从 repo 文件恢复上下文、执行第一个 ready 项、写 checkpoint、跑验证、输出 marker。

`harness-visualization` 能读取：

- `NEXT.md`
- `docs/changes/*/tasks.md`
- `docs/changes/archive/*/tasks.md`
- `.harness/run-checkpoint.md`
- `.harness/codex-exec-invocations.ndjson`

并输出 terminal text、Markdown、JSON。这个能力是 OpenSpec + Superpowers 组合中不一定默认具备的。

## 5. 主要问题与风险

## P0 / 高优先级

### 5.1 canonical layer progression 存在双重版本

README 和 `harness-engineering/SKILL.md` 中展示的是简化链：

```text
Idea -> Brainstorming -> Brief -> Architecture -> ADR -> Contract -> Implementation -> Verification -> Review / Next
```

但 `harness-engineering/references/layer-progression.md` 的 canonical source of truth 包含额外层：

- `intake-orientation`
- conditional `fact-discovery`
- `readiness`

影响：只读 README 或主 skill 的 agent 可能跳过 intake、fact discovery 或 readiness。

建议：

- README 和 `harness-engineering/SKILL.md` 直接复制完整 canonical progression。
- 或明确主文档中的短链只是 summary，真正 source of truth 是 `references/layer-progression.md`。

### 5.2 `governed-implementation-entry` 与 layer map 关系不清

README 把 `governed-implementation-entry` 定义为写实现前记录 Implementation Entry Record 的关键 skill。

但 `layer-progression.md` 中：

- `readiness` primary 是 `implementation-readiness-gate`
- `implementation` primary 也是 `implementation-readiness-gate`
- 没有把 `governed-implementation-entry` 纳入 canonical map

影响：路由可能进入 readiness/implementation 而不触发 implementation entry record。

建议：

- 在 `readiness` supporting skills 加 `governed-implementation-entry`；或
- 将 `implementation` primary 改为 `governed-implementation-entry`，supporting 为 `implementation-readiness-gate`；并
- 明确 Implementation Entry Record 是进入 product implementation 前的机械凭证。

## P1 / 中优先级

### 5.3 runner verification command 有命令注入风险

发现位置：

- `autonomous-ready-loop/assets/run-autonomous-ready-loop.sh` 使用 `eval "$VERIFICATION_COMMAND"`
- `autonomous-ready-loop/assets/run-autonomous-ready-loop.ps1` 使用 `Invoke-Expression $VerificationCommand`

影响：如果 verification command 来自 env、queue、配置、复制粘贴内容或 CI 变量，可能变成命令注入入口。

建议：

- 默认只接受 checked-in script path，如 `scripts/verify.sh` / `scripts/verify.ps1`。
- 或接受 argv array，而非字符串。
- 或维护 allowlist，例如 `npm test`、`pnpm test`、`pytest`、`go test ./...`。
- 若保留任意命令能力，文档中明确标注“只接受可信人工输入”，runner 默认禁用。

### 5.4 `harness-status.mjs` 输出路径可逃出 repo

`harness-status.mjs` 合并 config/CLI path 后，写 `statusMd` / `statusJson` 时使用 `path.resolve(status.repo, ...)`。如果 config 指向 `../outside.md` 或绝对路径，则可能写到 repo 外。

影响：自动 runner 中这是不必要的文件写入风险。

建议：

- 复用已有 `isPathInside(childPath, parentPath)` helper。
- 对所有 repo-relative 读写路径校验 inside repo。
- 特别保护 `--write-md` 和 `--write-json`。

### 5.5 `harness-status-dashboard` 与 `harness-visualization` 职责重叠

`harness-status-dashboard` 说要“新增一个 report 脚本”；但 `harness-visualization` 已经提供通用 `harness-status.mjs`、Markdown/JSON 输出和 status contract。

影响：agent 可能给每个业务项目重复写 report 脚本，破坏“通用 layer 负责解析和展示，业务项目只提供状态源”的设计。

建议：

- `harness-status-dashboard` 降级为解释/诊断/需求 skill。
- 默认实现统一调用 `harness-visualization/scripts/harness-status.mjs`。
- 仅在目标项目状态源非标准时写 adapter 或 `.harness/harness-status.config.json`。

### 5.6 `planning-with-files` 强制语气与 harness precondition 冲突

`planning-with-files` 有 Harness Precondition：必须先确认 `harness-engineering` 完成当前 layer 和治理义务判断。

但正文中又出现：

- “Before doing anything else”
- “Before ANY complex task”
- “Never start a complex task without `task_plan.md`”

影响：在已有 `NEXT.md`、checkpoint、项目 queue 的仓库中，agent 可能仍创建 root `task_plan.md`，导致 planning source 分裂。

建议改写为：

> After harness-engineering routes to planning-with-files and confirms no project queue/checkpoint/planning system exists...

并把 “Before ANY complex task” 改为 “Before any complex task that lacks an existing queue/checkpoint/planning system”。

### 5.7 PowerShell 与 shell 脚本 parity 不足

发现：

- `resolve-plan-dir.sh` 有 plan-id 安全校验；`resolve-plan-dir.ps1` 没有等价校验。
- `check-complete.sh` 能解析 active plan dir；`check-complete.ps1` 只默认 root `task_plan.md`。
- `init-session.sh` 有 slug mode / `.planning/<date>-slug/`；`init-session.ps1` 仍只创建 root 三文件。

影响：Windows 用户会更容易遇到 active plan 不生效、脚本行为与文档不一致。

建议：

- 把 `.sh` 的 slug/active plan 逻辑移植到 `.ps1`。
- 增加跨平台 parity tests。

## P2 / 低优先级与发布卫生

### 5.8 缺少根目录 test/check 入口

当前没有 `package.json` 或统一 `npm test` / `pnpm test` / `justfile`。Node 测试可以跑，但入口不明显。

建议新增：

```json
{
  "scripts": {
    "test": "node --test harness-visualization/tests/*.test.mjs",
    "check:routing": "python harness-engineering/scripts/check-routing-guardrails.py"
  }
}
```

### 5.9 测试覆盖集中在 `harness-visualization`

缺少系统测试的部分：

- `planning-with-files/scripts/*.sh`
- `planning-with-files/scripts/*.ps1`
- `autonomous-ready-loop/assets/*.sh`
- `autonomous-ready-loop/assets/*.ps1`
- `gh-fix-ci/scripts/inspect_pr_checks.py`
- `governed-implementation-entry/scripts/check-entry-record.mjs`
- `harness-engineering/scripts/check-routing-guardrails.py`

### 5.10 `find-docs` 依赖 `openai-docs`，但本 repo 不包含该 skill

`find-docs` 明确说 OpenAI/Codex 文档应使用 `openai-docs`。如果这是外部/system skill，应在 README 中标注为外部依赖，并给出缺失时 fallback。

## 6. OpenSpec 最新功能摘要

基于 OpenSpec 官网、GitHub、CLIHub 与 2026 文章：

- OpenSpec 定位为面向 AI coding assistants 的 spec-driven development 框架。
- GitHub repo 描述为 “Spec-driven development (SDD) for AI coding assistants”。
- 安装方式：`npm install -g @fission-ai/openspec@latest`。
- 要求 Node.js 20.19+。
- 项目初始化：`openspec init`。
- 典型 slash commands：
  - `/opsx:propose`
  - `/opsx:apply`
  - `/opsx:archive`
  - `/opsx:new`
  - `/opsx:ff`
  - `/opsx:verify`
  - `/opsx:bulk-archive`
  - `/opsx:onboard`
- artifact 通常包括：
  - `proposal.md`
  - `specs/`
  - `design.md`
  - `tasks.md`
- OpenSpec 宣称支持 20+/25+ AI tools/assistants，包括 Claude Code、Cursor、Codex、GitHub Copilot、OpenCode、Windsurf、Gemini CLI 等。
- release 信息：
  - v1.4.1：2026-06-03，修复 update 等问题。
  - v1.4.0：2026-06-01，增加 Kimi CLI、Mistral Vibe 集成。
  - v1.3.1：2026-04-21，路径与 telemetry 修复。
  - v1.2.0：2026-02-23，引入 profiles、Pi/AWS Kiro 支持、AI tool auto-detection 等。
  - v1.0：2026-01-26，强调 Explore Mode、逐步 artifact 生成、intent verification、config.yaml 等。

## 7. Superpowers 最新功能摘要

基于 `obra/superpowers` GitHub、官方站点与 Anthropic plugin listing：

- Superpowers 定位为 “agentic skills framework & software development methodology”。
- 支持 Claude Code 官方 plugin marketplace，安装示例：

```text
/plugin install superpowers@claude-plugins-official
```

- 也支持 Codex CLI/App、Factory Droid、Gemini CLI、OpenCode、Cursor、GitHub Copilot CLI 等。
- 核心技能/工作流包括：
  - brainstorming
  - writing-plans
  - executing-plans
  - dispatching-parallel-agents
  - subagent-driven-development
  - test-driven-development
  - systematic-debugging
  - verification-before-completion
  - requesting-code-review
  - receiving-code-review
  - using-git-worktrees
  - finishing-a-development-branch
  - writing-skills
  - using-superpowers
- 方法论强调：
  - 编码前先澄清目标
  - 写计划
  - TDD：red/green/refactor
  - 系统化 debugging
  - code review
  - 完成前验证
- GitHub 页面显示 latest release v5.1.0，时间为 2026-05-04。

## 8. 与 OpenSpec 对比

| 维度 | OpenSpec | `E:\my-skills` |
|---|---|---|
| 产品形态 | 成熟 CLI：`openspec init/update` + slash commands | repo-local skills，无统一 CLI/package |
| 核心目标 | specs as living docs，proposal/apply/archive | agent governance，层级、准入、契约、验证、队列 |
| artifact | `openspec/changes/...`，proposal/specs/design/tasks | `docs/changes/...`，proposal/design/tasks/contracts/verification |
| gate 模型 | 轻量、迭代、spec delta review | 更强 gate：Architecture/ADR/Contract/Readiness/Verification/Review |
| 多工具支持 | 官方宣称 20+/25+ agent/tools | 当前偏 Codex/Claude 本地 skills 语境 |
| 验证与状态 | 有 verify/archive/update 等命令 | runner checkpoint/status JSON/done archive 更强 |
| 弱点 | 不一定治理 agent 自治和角色隔离 | 不具备 OpenSpec 的完整 CLI/validator/spec-delta 生态 |

判断：

- 如果目标是让团队快速安装规范驱动开发，OpenSpec 更强。
- 如果目标是控制 agent 长任务漂移、跳层、乱用 companion workflow、实现前无契约，你的 harness 更强。

## 9. 与 Superpowers 对比

| 维度 | Superpowers | `E:\my-skills` |
|---|---|---|
| 产品形态 | 官方 Claude plugin + 多 harness 安装说明 | repo-local skills，缺 marketplace/plugin packaging |
| 工作流风格 | 通用开发方法论：TDD、debugging、planning、review | 治理状态机：层级、准入、契约、持久证据、queue |
| 强制程度 | 通过 skills/initial instructions 引导 | 明确 companion containment，不允许抢入口 |
| 多 agent | dispatching parallel agents、subagent development | role isolation、execution prompt pack、autonomous ready loop |
| 完成判定 | verification-before-completion | verification + review-next + done archive + status JSON |
| 弱点 | 可能让 companion terminal state 接管流程 | 生态/安装/UX 不如 Superpowers；学习曲线更高 |

判断：

- Superpowers 更像通用 agent 工程方法论套件。
- 你的项目更像对 Superpowers/OpenSpec 这类方法论的本地治理内核。
- 当前把 Superpowers 明确降级为 companion workflow 是正确设计。

## 10. OpenSpec + Superpowers 组合 vs 本项目

| 能力 | OpenSpec + Superpowers | `E:\my-skills` |
|---|---|---|
| 需求到 spec | OpenSpec 很强，Superpowers brainstorming 辅助 | brainstorm-to-brief + architecture + ADR + contract，更细但更重 |
| 计划到实现 | OpenSpec apply + Superpowers executing/TDD | governed implementation + readiness gate + role isolation |
| 代码验证 | Superpowers verification-before-completion | verification + review-next + status dashboard |
| 长任务自治 | 组合本身不一定提供标准 runner/checkpoint | autonomous-ready-loop 是明显优势 |
| 状态可视化 | 依赖工具/UI/PR | JSON/Markdown status 是优势 |
| 团队安装/传播 | OpenSpec CLI + Superpowers plugin 强 | 缺统一安装、版本、命令入口 |
| 规范一致性 | OpenSpec artifact schema 更集中 | 本地文档有局部不一致 |
| 安全边界 | 取决于配置 | 理念强，但 runner 脚本需修命令执行风险 |

最准确定位：

> OpenSpec/Superpowers-compatible local governance harness：OpenSpec 管 spec artifact，Superpowers 提供 agent 方法论，本项目负责入口路由、层级治理、准入、持久状态、自治 runner 和 drift control。

## 11. 推荐路线图

## P0：先修安全风险

1. 移除或限制：
   - `run-autonomous-ready-loop.sh` 的 `eval`
   - `run-autonomous-ready-loop.ps1` 的 `Invoke-Expression`
2. 给 `harness-status.mjs` 增加路径 inside-repo 校验。

## P1：统一规范源

1. README 和 `harness-engineering/SKILL.md` 使用 `layer-progression.md` 的完整层级。
2. 把 `governed-implementation-entry` 纳入 canonical layer map。
3. 明确 `harness-status-dashboard` vs `harness-visualization`：
   - dashboard = 解释/诊断 skill
   - visualization = 默认实现与 JSON contract

## P2：补齐测试与发布入口

1. 加根目录 `package.json` 或 `justfile`。
2. 增加 shell/PowerShell parity tests。
3. 给 `check-entry-record.mjs` 加正例/反例测试。
4. 如果准备对外发布，增加：
   - version manifest
   - install instructions
   - compatibility matrix：Claude Code / Codex / OpenCode / Cursor

## P3：做 adapter，而不是硬替代

### OpenSpec adapter

建议支持读取/写入：

```text
openspec/changes/<id>/
  proposal.md
  specs/
  design.md
  tasks.md
```

并映射到本地 harness：

| OpenSpec | 本地 harness |
|---|---|
| proposal | Brief |
| specs delta | Contract |
| design | Architecture / ADR candidate |
| tasks | Implementation packet |
| apply | Implementation |
| archive | Review / Next |

### Superpowers adapter

保持当前 containment 设计：

| Superpowers | 本地 owner |
|---|---|
| brainstorming | `brainstorm-to-brief` |
| writing-plans | `planning-with-files` / queue |
| test-driven-development | `contract-first-development` |
| systematic-debugging | fact discovery + debugging checklist |
| verification-before-completion | `review-next-governance` |
| subagent-driven-development | `agent-role-isolation` + `execution-prompt-authoring` |

## 12. 优先修复清单

1. 修 runner command execution sink：`eval` / `Invoke-Expression`。
2. 修 status output path escape。
3. 统一 layer progression 文档。
4. 把 `governed-implementation-entry` 写入 canonical layer map。
5. 明确 dashboard vs visualization 的职责边界。
6. PowerShell 与 shell 脚本 parity。
7. 增加根目录 test/check 入口和 CI。
8. 写 OpenSpec/Superpowers adapter 文档，而不是把它们视为竞争入口。

## 13. 外部来源

- [OpenSpec official site](https://openspec.dev/)
- [OpenSpec GitHub — Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec)
- [OpenSpec pro site](https://openspec.pro/)
- [CLIHub OpenSpec release/changelog page](https://clihub.org/cli/?slug=openspec)
- [Spec-Driven Development with OpenSpec and OpenCode](https://intent-driven.dev/blog/2026/05/10/spec-driven-development-openspec-opencode/)
- [OpenSpec 1.0 Release](https://intent-driven.dev/blog/2026/01/26/openspec-1-0-release/)
- [Superpowers GitHub — obra/superpowers](https://github.com/obra/superpowers)
- [Superpowers official site](https://superpowers.apposters.com/)
- [Superpowers — Claude Plugin listing](https://claude.com/plugins/superpowers)
