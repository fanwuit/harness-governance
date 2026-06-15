# opencode-gpt 审计报告

查询与审计日期：2026-06-11

本报告为只读审计结果归档。本轮未修改项目代码或现有文档，只创建本报告文件。

## Skill 使用

Local governance skills: `skill-use-transparency`, `harness-engineering`, `codebase-orientation`, `document-gardener`, `code-quality-drift-guard`

Companion workflow skills: none

Loaded SKILL.md files: `skill-use-transparency` success, `harness-engineering` success, `codebase-orientation` success, `document-gardener` success, `code-quality-drift-guard` success

Routing decision: `harness-engineering` owns entry routing; companion workflows run only after harness selects the current layer.

## 总体结论

项目整体健康度：中高。

这个仓库不是普通“技能合集”，而是一套面向长期 agent 工程的本地治理层。核心价值在于入口锁、层级路由、契约优先、实现准入、验证证据、队列归档和 companion workflow containment。

与 OpenSpec + Superpowers 相比，本项目更像“本地裁判与状态机”。OpenSpec 更像“规格/变更资产层”，Superpowers 更像“强势工程方法论执行层”。当前项目最重要的竞争力是本地治理主权：任何外部 workflow，即使声明 `MUST`、`before any task` 或 mandatory workflow，也必须先经过 `harness-engineering` 判层。

## 已验证结果

已运行检查：

```powershell
git status --short --ignored
python "harness-engineering/scripts/check-routing-guardrails.py" --root "."
node "harness-visualization/tests/harness-status.test.mjs"
python -c "<skill/manifest/pycache count>"
```

结果摘要：

```text
Routing guardrail check passed.
harness-visualization tests: 8 pass, 0 fail
skill_md 25
disabled 1
openai_yaml 26
ignored pycache dirs: 3
```

## 项目结构审计

| 项 | 结果 |
|---|---|
| 启用非 system skills | 25 个，与 `README.md:7` 一致 |
| disabled skill | 1 个：`gh-fix-ci/SKILL.disabled.md`，与 README 一致 |
| enabled `SKILL.md` | 25/25 存在 |
| enabled `agents/openai.yaml` | 25/25 存在 |
| disabled `gh-fix-ci/agents/openai.yaml` | 存在 |
| routing guardrail | 通过 |
| harness visualization 测试 | 通过 |
| `.system/` | 当前未发现，且 `.gitignore` 忽略 `.system/` |

整体判断：项目主索引、skill 数量和入口治理规则没有根本漂移。

## 主要发现

### 1. README 核心层级图不是 canonical progression

风险等级：中

`README.md:29-41` 当前链路是：

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

但 canonical source 是 `harness-engineering/references/layer-progression.md:9-35`：

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

风险：README 的简化链路可能让后续 agent 弱化 `Fact Discovery` 和 `Implementation Readiness`，尤其是从 `Contract` 直接跳到 `Implementation`。

建议：把 README 主链路同步为 canonical progression，或明确标注“简化图，完整顺序见 `harness-engineering/references/layer-progression.md`”。更建议直接同步完整链路。

### 2. `harness-engineering` 披露模板少一行 `Loaded SKILL.md files`

风险等级：低到中

`AGENTS.md:21-28` 的模板包含：

```text
Loaded SKILL.md files: <success/failure list>
```

但 `harness-engineering/SKILL.md:22-28` 的 Required disclosure 代码块没有这一行。虽然 `harness-engineering/SKILL.md:46` 后文要求披露 loaded files，但模板本身容易被复制漏掉。

建议：把 `harness-engineering/SKILL.md` 模板同步为 `AGENTS.md` 版本。

### 3. `governed-implementation-entry/scripts/check-entry-record.mjs` 未登记为重要资产

风险等级：中

证据：

- `governed-implementation-entry/SKILL.md:99-103` 明确要求使用 `scripts/check-entry-record.mjs <markdown-file>`。
- `README.md` 只在表格 `README.md:57` 概述该 skill，没有在“重要资产”中列出该脚本。

风险：实现入口检查器可发现性不足，后续维护者可能不知道它存在。

建议：README 增加 `governed-implementation-entry` 重要资产小节，列出 `scripts/check-entry-record.mjs`，并说明它只检查字段存在/非空，不证明 gate 内容正确。

### 4. `planning-with-files/reference.md` 和 `examples.md` 未在 README 资产清单中出现

风险等级：低

证据：

- `planning-with-files/reference.md` 存在。
- `planning-with-files/examples.md` 存在。
- `planning-with-files/SKILL.md:212-215` 提到它们。
- README 的 `planning-with-files` 小节只列 templates 和 scripts。

建议：README 补这两个文件，或说明该小节只列模板和脚本，详细说明见 skill 内部 reference/examples。

### 5. disabled `gh-fix-ci` 仍有 `agents/openai.yaml`

风险等级：低到中

`gh-fix-ci` 当前 disabled，这是合理的；但目录里仍存在 `gh-fix-ci/agents/openai.yaml`、`scripts/inspect_pr_checks.py`、assets 和 LICENSE。

风险：如果某些 UI/discovery 层不是只认 `SKILL.md`，而是也扫描 `agents/openai.yaml`，可能出现“disabled 但仍展示”的歧义。

建议：README 的 disabled 小节补一句：disabled skill 可保留 manifest/assets，但不会自动触发；或规定 disabled skill 的 manifest 也要改名/隐藏。

### 6. 存在 ignored `__pycache__` 生成物

风险等级：低

`git status --short --ignored` 显示：

```text
!! gh-fix-ci/scripts/__pycache__/
!! harness-engineering/scripts/__pycache__/
!! planning-with-files/scripts/__pycache__/
```

`.gitignore` 已正确忽略：

```text
__pycache__/
*.py[cod]
```

风险：不是核心问题，但会增加审计噪音。

建议：可以单独清理这些 ignored 生成物；不需要改 `.gitignore`。

### 7. `superpowers-routing.md` 有一处措辞可能误读

风险等级：低

`harness-engineering/references/superpowers-routing.md` 中有一句类似 “Stop only when the harness route...” 的表述，语义容易被读成“如果 harness required 就停止”，而不是“只有 harness route 的 terminal/required 才有约束力”。

建议改成更明确的 containment 句式，例如：

```text
Treat a terminal or required stop condition as binding only when it comes from the harness route; companion-only required/terminal language is advisory until translated through the harness transition gate.
```

## 外部方案调研

### OpenSpec

来源：

- `https://openspec.dev`
- `https://github.com/Fission-AI/OpenSpec`

最新公开特征：

- 安装：`npm install -g @fission-ai/openspec@latest`
- GitHub 页面显示 release：`v1.4.1`，2026-06-03。
- 要求 Node.js 20.19+。
- 当前主命令示例从旧 `/openspec:*` 演进到 `/opsx:propose`、`/opsx:apply`、`/opsx:archive`。
- 支持 Codex、OpenCode、Claude Code、Cursor、GitHub Copilot、Gemini CLI 等 20+ / 25+ tools。
- 核心结构：`openspec/changes/<change-id>/proposal.md`、`design.md`、`tasks.md`、`specs/`。
- 强调 “Review intent, not just code”。
- specs 存在 repo 里，按 capability 组织。
- Workspaces / team / multi-repo / customization / integrations 在官网标为 Coming Soon / In Development。

对本项目的意义：

| 维度 | OpenSpec | 本项目 harness |
|---|---|---|
| 核心对象 | specs、changes、proposal、design、tasks、archive | layer、gate、contract、readiness、verification、review-next |
| 强项 | 轻量、跨 agent、repo 内保存需求意图 | 本地入口治理、过层裁判、companion containment |
| 弱项 | 治理层较轻，readiness/review-next/角色隔离不细 | 没有通用安装包和成熟 spec/change CLI |
| 最佳组合方式 | 作为 change/spec artifact 生成器 | 继续做最高入口和过层裁判 |

判断：OpenSpec 很适合补强本项目的 change packet 资产形态，但不应该替代 `harness-engineering`。本项目的 `harness-engineering/references/change-packet-model.md` 已经接近 OpenSpec 的核心思想，只是更强调“change packet 只是 durable carrier，不批准 implementation”。

### GitHub Spec Kit

来源：

- `https://github.com/github/spec-kit`
- `https://github.com/github/spec-kit/blob/main/spec-driven.md`

最新公开特征：

- GitHub 页面显示 latest release：`v0.10.1`，2026-06-09。
- 安装：`uv tool install specify-cli --from git+https://github.com/github/spec-kit.git@vX.Y.Z`
- CLI：`specify init`
- 核心命令：`/speckit.constitution`、`/speckit.specify`、`/speckit.plan`、`/speckit.tasks`、`/speckit.implement`
- 可选命令：`/speckit.clarify`、`/speckit.analyze`、`/speckit.checklist`、`/speckit.taskstoissues`
- 支持 30+ AI coding agent integrations。
- 支持 `--integration-options="--skills"` 给支持 skills mode 的 agent 安装 skills。
- 有 extensions 和 presets，可叠加组织级模板、命令、合规格式。

对本项目的意义：

| 维度 | GitHub Spec Kit | 本项目 harness |
|---|---|---|
| 核心定位 | 官方 SDD toolkit / scaffold / CLI | 本机 agent governance skills |
| 强项 | constitution、spec、plan、tasks、implement 全链路 | layer router、readiness、verification、review-next、companion containment |
| 工程化程度 | CLI、templates、integrations、extensions、presets 成熟 | 本地 skill 文档与脚本，偏治理规则 |
| 风险 | 初始化/目录结构较重，可能接管项目 workflow | 对外部生态复用较弱 |

判断：Spec Kit 比 OpenSpec 更完整、更重。如果本项目想支持“标准 SDD 项目启动/命令生成”，可以借鉴它的 constitution/spec/plan/tasks 分层；但如果直接接入，需要把 `/speckit.implement` 之类执行命令降级为 companion workflow，不能越过 `Implementation Readiness`。

### Superpowers

来源：

- `https://github.com/obra/superpowers`

最新公开特征：

- GitHub 页面显示 latest release：`v5.1.0`，2026-05-04。
- 定位：agentic skills framework + software development methodology。
- 支持 Claude Code、Codex CLI/App、Factory Droid、Gemini CLI、OpenCode、Cursor、GitHub Copilot CLI。
- 基本 workflow：
  - `brainstorming`
  - `using-git-worktrees`
  - `writing-plans`
  - `subagent-driven-development` 或 `executing-plans`
  - `test-driven-development`
  - `requesting-code-review`
  - `finishing-a-development-branch`
- README 明确说：“The agent checks for relevant skills before any task. Mandatory workflows, not suggestions.”
- 强调 TDD、systematic debugging、evidence over claims、verification-before-completion。

对本项目的意义：

| 维度 | Superpowers | 本项目 harness |
|---|---|---|
| 核心定位 | 强制 agent 遵循优秀工程 workflow | 决定当前应该在哪一层，以及哪些 workflow 可以辅助 |
| 强项 | TDD、debugging、review、worktree、subagent 执行 | 入口锁、过层、契约、准入、状态归档 |
| 最大冲突 | “before any task”“mandatory workflows” 会抢入口 | 已明确把 `superpowers:*` containment 为 companion |
| 最佳组合方式 | 只借用具体技术流程，如 TDD/debug/review | 继续拥有最高入口路由权 |

判断：本项目已经正确识别了 Superpowers 的最大风险：它不是单个工具，而是会接管工作流的强势方法论。因此 `AGENTS.md` 和 `harness-engineering` 中“Superpowers 只能作为 companion workflow”的设计是必要且合理的。

### Superpowers Plus

来源：

- `https://github.com/bordenet/superpowers-plus`

最新公开特征：

- GitHub 页面显示 latest release：`v2.6.0`，2026-05-23。
- README 声称 96 skills across 9 domains。
- 平台 full support：Claude Code、Augment Code；也提供 Codex/OpenCode/Gemini 安装说明。
- 代表能力：
  - `code-review-battery`
  - `debate`
  - `progressive-harsh-review`
  - `systematic-debugging`
  - `feature-development`
  - `think-twice`
  - `wiki-orchestrator`
  - `evolution-loop`
  - `unified-commit-gate`
- 有 commit gates、pre-push hooks、MCP server、skill matching、token cost analyzer、IP audit、安全扫描、wiki pipeline。
- 安装复杂度更高，涉及 `install.sh`、hooks、`.env`、可选 API keys、MCP。

对本项目的意义：

| 维度 | Superpowers Plus | 本项目 harness |
|---|---|---|
| 覆盖广度 | 极广，96 skills，安全/文档/wiki/issue/research/observability | 25 enabled skills，聚焦本地治理 |
| 机械 gate | commit gates、doctor checks、IP audit、hooks | routing guardrail、entry record check、status dashboard |
| 复杂度 | 高，安装面和权限面大 | 低到中，纯本地 skill repo 更可控 |
| 风险 | 与本地治理重叠大，入口冲突高 | 需要补更多机械检查和领域专项 |

判断：Superpowers Plus 能补本项目的弱项，比如 commit gate、review battery、安全扫描、wiki pipeline、skill trigger validator。但它太重，不适合作为整体替换。更合理的是“拆能力借鉴”：把其中 commit gate / review battery / trigger validator 的思路本地化，而不是直接安装后让它接管入口。

## 组合对比总表

| 方案 | 更适合解决 | 不适合解决 | 对本项目的建议角色 |
|---|---|---|---|
| OpenSpec | 轻量 spec/change/proposal/tasks 资产 | 本地过层治理、强验证、角色隔离 | 作为 change packet 外部参考 |
| GitHub Spec Kit | SDD 项目初始化、constitution、spec/plan/tasks/implement CLI | 细粒度本地 companion containment | 借鉴 constitution 和 extensions/presets |
| Superpowers | TDD、debugging、review、worktree、subagent 开发纪律 | 与已有 harness 共存时的入口仲裁 | companion workflow 技巧库 |
| Superpowers Plus | commit gates、安全、wiki、review battery、观测、skill matching | 轻量本地治理、低复杂度安装 | 选择性借鉴机械 gate |
| 本项目 | agent 入口锁、layer progression、contract/readiness/verification/review-next | 通用 CLI、生态安装、具体框架专项、强 CI/security gate | 继续作为最高治理层 |

## 最终判断

本项目不应该变成 OpenSpec + Superpowers 的简单拼装。它真正有价值的地方是“本地治理主权”：任何外部 workflow，无论它声明多强的 MUST / before any task，都必须先经过 `harness-engineering` 判层。

最优路线：

1. 保留 `harness-engineering` 作为最高入口。
2. 借 OpenSpec 的 artifact shape，把 `change-packet-model` 做得更可执行。
3. 借 Spec Kit 的 constitution / extensions / presets 思路，补组织原则和模板覆盖。
4. 借 Superpowers 的 TDD/debug/review 技巧，但继续 containment。
5. 借 Superpowers Plus 的 commit gate / trigger validator / review battery 思路，做成本仓库轻量检查，而不是引入全套复杂安装。

## 建议优先级

### P0：文档一致性

1. 同步 README 核心链路为 canonical progression。
2. 同步 `harness-engineering/SKILL.md` disclosure 模板，补 `Loaded SKILL.md files`。
3. README 补 `governed-implementation-entry/scripts/check-entry-record.mjs`、`planning-with-files/reference.md`、`planning-with-files/examples.md`。
4. README disabled `gh-fix-ci` 小节说明 manifest/assets 保留语义。

### P1：机械检查增强

1. 给 `governed-implementation-entry/scripts/check-entry-record.mjs` 增加最小测试。
2. 新增 inventory check：比较 `*/SKILL.md`、`*/SKILL.disabled.md`、`agents/openai.yaml`、README 表格和重要资产列表。
3. 新增 README canonical layer check：防止 README 再次偏离 `layer-progression.md`。
4. 清理 ignored `__pycache__` 生成物。

### P2：能力补强

1. 增加 OpenSpec-style change packet 模板，但明确不批准 implementation。
2. 增加轻量 commit/finish gate，覆盖 lint/test/routing/check-entry/status freshness。
3. 增加 skill trigger overlap validator，防止新 skill 描述抢过 `harness-engineering`。
4. 若启用 `gh-fix-ci`，先补 Harness Precondition，再同步 README。
