# codex-gpt 审计报告

生成日期：2026-06-11

## Skill 使用

本轮按项目规则使用并读取了以下 skill：

- `skill-use-transparency`：项目要求所有 skill 选择必须显式说明；`SKILL.md` 读取成功。
- `harness-engineering`：项目要求所有开发、审计、review、文档沉淀类请求先由它做入口路由；`SKILL.md` 读取成功。
- `document-gardener`：本轮把审计结果沉淀为仓库 Markdown 文档；`SKILL.md` 读取成功。

Routing decision：`harness-engineering` 拥有入口路由；本轮当前层为 `review-next` / 文档沉淀，不进入实现层，不执行 `superpowers:*` companion workflow。

## 一句话结论

这个仓库不是 OpenSpec 或 Superpowers 的替代品，而是一套更强本地治理优先级的 Codex skills harness。它已经有清晰的入口锁、层级路由、契约优先、实现准入、自治 runner、checkpoint 和状态可视化能力；主要风险集中在规范源重复、少数脚本执行边界偏松、README 资产清单不够完整。

## 已验证结果

本地验证：

- `python harness-engineering/scripts/check-routing-guardrails.py`：通过。
- `node --test harness-visualization/tests/harness-status.test.mjs`：8 个测试全部通过。
- 启用的非 system skills：25 个。
- 禁用但存在的 skill：`gh-fix-ci`，入口为 `SKILL.disabled.md`。
- 所有启用 skill 的 frontmatter `name` / `description` 基本检查通过。
- README 表格覆盖全部启用 skill。

工作区状态：

- 已存在未跟踪文件：`cc-gpt审计.md`、`opencode-gpt审计.md`。
- 本轮新增：`codex-gpt审计.md`。

## 项目强项

1. 入口治理强

   `AGENTS.md` 明确规定每次请求先走 `skill-use-transparency` 和 `harness-engineering`，并要求 `superpowers:*` 只能作为 companion workflow。这个规则能防止强势 companion skill 抢入口，尤其是 `superpowers:using-superpowers` 这类声明 “before ANY response” 的 workflow。

2. 层级模型比 OpenSpec 更细

   当前 canonical progression 在 `harness-engineering/references/layer-progression.md`：

   ```text
   Intake / Orientation
    -> Idea
    -> Fact Discovery
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

   这比 OpenSpec 的 proposal / specs / design / tasks / apply / archive 更适合约束 AI agent，因为它把事实发现、ADR、实现准入、验证收口拆开了。

3. Change packet 抽象是正确的

   `harness-engineering/references/change-packet-model.md` 把 change packet 定义为 carrier，不是 gate。这一点比直接引入 OpenSpec 目录结构更稳：OpenSpec artifacts 可以映射进本地 packet，但不能绕过 harness layer gate。

4. 长任务自治能力是差异化优势

   `autonomous-ready-loop`、`harness-status-dashboard`、`harness-visualization` 形成了一个可运行的长任务框架：短 `codex exec` worker、checkpoint、status markdown/json、done archive 和 queue scanner。这是 OpenSpec + Superpowers 默认组合里没有完全覆盖的部分。

## 主要问题与风险

### P0：canonical layer progression 有重复版本

事实：

- `harness-engineering/references/layer-progression.md` 是明确声明的 source of truth。
- `README.md` 和 `harness-engineering/SKILL.md` 仍保留旧链路：`Idea -> Brainstorming -> Brief -> Architecture -> ADR -> Contract -> Implementation -> Verification -> Review / Next`。
- 旧链路缺少 `Intake / Orientation`、`Fact Discovery`、`Implementation Readiness`。

风险：

- 后续 agent 可能按旧链路从 Contract 直接进入 Implementation。
- `Fact Discovery` 和 `Implementation Readiness` 会被弱化。

建议：

- `README.md` 主链路改为 canonical progression，或明确标注为“简化视图，完整顺序见 layer-progression.md”。
- `harness-engineering/SKILL.md` 的“层级链路”和“常见流程”同步补上 `Fact Discovery` 与 `Implementation Readiness`。
- `check-routing-guardrails.py` 增加检查：README / SKILL 中不得出现未标注的旧链路。

### P1：自治 runner 的验证命令执行边界偏宽

事实：

- PowerShell runner 使用 `Invoke-Expression $VerificationCommand`。
- Bash runner 使用 `eval "$VERIFICATION_COMMAND"`。

风险：

- 如果 `VerificationCommand` 来自不完全可信的 queue、config、环境变量或外部 runner 参数，会放大命令注入风险。

建议：

- 把验证命令改成受控命令数组或 allowlist。
- 至少在 runner 文档中明确：`VerificationCommand` 只能由可信操作者提供，不能从未审计队列文本透传。
- 对常见验证提供预设，例如 `routing-guardrails`、`harness-visualization-tests`、`all-local-checks`。

### P1：`harness-status.mjs` 写出路径缺 repo containment

事实：

- `--status-md` / `--status-json` 会 resolve 到绝对路径后直接写入。

风险：

- 如果 config 被污染，状态输出可写到 repo 外部路径。

建议：

- 复用已有 `isPathInside(childPath, parentPath)`，禁止 status 输出逃出 repo。
- 若确实需要外部输出，增加显式 `--allow-outside-output`。

### P1：README 对重要资产登记不完整

事实：

- `governed-implementation-entry/scripts/check-entry-record.mjs` 存在，但 README 没有单独列入重要资产。
- `planning-with-files/reference.md` 和 `examples.md` 存在，但 README 只列模板和脚本。
- `gh-fix-ci` disabled 目录仍保留 `agents/openai.yaml`。

风险：

- 维护者可能不知道实现入口记录已有机械检查。
- disabled skill 的 manifest 可见性规则不够明确。

建议：

- README 增加 `governed-implementation-entry` 资产小节。
- README 在 `planning-with-files` 小节补充 reference / examples。
- README 在 disabled 小节明确：disabled skill 可保留 manifest/assets，但不会作为启用 skill 自动触发；或规定 disabled skill 的 manifest 也应隐藏。

### P2：`planning-with-files` 有强入口措辞

事实：

- 该 skill 有 Harness Precondition。
- 正文仍写 “Before doing anything else” 和 “Before ANY complex task”。

风险：

- 与本项目“harness-engineering 先路由”的入口优先级存在语义冲突。

建议：

- 改成：“After harness routes to this skill”。
- 保留持久计划能力，但明确它只在没有 `NEXT.md` / checkpoint / 项目队列规则时作为 fallback。

### P2：仓库有 ignored 生成物

事实：

- 当前存在 `__pycache__` / `.pyc` 生成物，已被 git ignore。

风险：

- 不影响功能，但增加审计噪音。

建议：

- 单独清理生成物即可，不需要改 `.gitignore`。

## 与 OpenSpec 对比

联网确认：

- OpenSpec package 当前显示 `@fission-ai/openspec` version `1.4.1`。
- GitHub release 显示 v1.4.1 发布于 2026-06-03，修复 `openspec update` 问题。
- v1.4.0 新增 Kimi CLI、Mistral Vibe 支持，并默认生成 sync skills。

OpenSpec 强项：

- 标准化目录：`openspec/specs/` 是当前行为 source of truth，`openspec/changes/` 是活跃变更包。
- 标准 artifacts：`proposal.md`、`design.md`、`tasks.md`、delta specs。
- 标准命令：`/opsx:propose`、`/opsx:apply`、`/opsx:sync`、`/opsx:archive`；扩展模式包含 `/opsx:new`、`/opsx:continue`、`/opsx:ff`、`/opsx:verify`、`/opsx:bulk-archive`、`/opsx:onboard`。
- 支持 project config、custom schemas、global overrides。
- 生态和安装面更强，适合多工具团队。

本项目相对优势：

- 层级更细，尤其是 Fact Discovery、ADR、Implementation Readiness、Review / Next。
- companion workflow containment 明确，不让外部方法论接管入口。
- 有自治 runner、checkpoint、status 可视化。
- 更适合 Codex 本地治理和长任务队列。

建议关系：

- 不建议用 OpenSpec 替代本项目。
- 建议做 OpenSpec adapter：读取/写入 `openspec/changes/*`，把 proposal/spec/design/tasks 映射到本地 change packet，但 harness layer 仍然是最终 gate。

## 与 Superpowers 对比

联网确认：

- Superpowers Codex plugin manifest 当前显示 version `5.1.0`。
- release notes 显示 v5.1.0 发布于 2026-04-30。
- v5.1.0 删除旧 slash command stub，改为直接调用 skill；重写 worktree / finish branch；合并 code reviewer named agent；调整 subagent-driven cadence。

Superpowers 强项：

- 成熟的 agent 方法论：brainstorming、writing plans、TDD、systematic debugging、subagent-driven development、review、verification。
- 跨 Claude Code、Codex、Gemini CLI、OpenCode、Cursor 等工具。
- 技术动作更贴近日常开发，例如 TDD、debugging、worktree、branch finish。

本项目相对优势：

- 明确区分 local governance 和 companion workflow。
- 不让 `superpowers:using-superpowers` 的强触发词越过本地入口。
- 对长期治理、队列、checkpoint、状态可视化、实现准入更强。

建议关系：

- 继续把 Superpowers 当 companion-only。
- 只借用它的技巧：brainstorming、TDD discipline、systematic debugging、verification discipline、review prompt。
- 不接受它的 terminal state、required sub-skill、默认 artifact 路径、commit / branch finish 指令，除非 harness 当前层允许。

## OpenSpec + Superpowers 组合 vs 本项目

| 维度 | OpenSpec + Superpowers | 本项目 |
|---|---|---|
| 入口治理 | 容易被 Superpowers 强触发接管 | 本地 harness 明确拥有入口 |
| 规范 artifacts | OpenSpec 更标准 | 本项目更灵活，但需补 adapter |
| 层级细度 | 中等 | 更细，包含事实发现和准入 |
| TDD / debugging 方法 | Superpowers 更成熟 | 当前多为治理层，具体技术 workflow 较少 |
| 长任务自治 | 默认较弱 | autonomous-ready-loop + visualization 较强 |
| 跨工具生态 | 更强 | 主要面向 Codex skills |
| 风险 | workflow 叠加后入口冲突 | 自定义体系维护成本较高 |

最终判断：

- 如果目标是“开箱即用的 spec-driven + agent 方法论”，OpenSpec + Superpowers 更快。
- 如果目标是“本地可控、可审计、长任务自治、避免 companion workflow 抢入口”，本项目更合适。
- 最优路线不是替换，而是 adapter：OpenSpec 做 artifacts 标准化，Superpowers 做 companion 技术动作，本项目继续做 governance kernel。

## 推荐路线图

### P0：统一 source of truth

- 同步 README 和 `harness-engineering/SKILL.md` 的层级链路到 `layer-progression.md`。
- 给 routing guardrail 增加旧链路漂移检查。

### P1：收紧 runner / status 安全边界

- 替换 `eval` / `Invoke-Expression`。
- status 输出路径限制在 repo 内。
- 对 trusted verification command 做文档声明。

### P1：补 README 资产登记

- 增加 `governed-implementation-entry/scripts/check-entry-record.mjs`。
- 增加 `planning-with-files/reference.md`、`examples.md`。
- 明确 disabled skill 的 manifest 策略。

### P2：补根目录 check 入口

建议新增统一检查入口，例如：

```text
scripts/check-all.ps1
scripts/check-all.sh
```

串联：

- routing guardrail。
- harness visualization tests。
- frontmatter / README inventory check。
- 可选 pycache / ignored generated noise check。

### P3：做 adapter，不做替代

OpenSpec adapter：

- `openspec/changes/<id>/proposal.md` -> `docs/changes/<id>/proposal.md`
- `openspec/changes/<id>/design.md` -> `docs/changes/<id>/design.md`
- `openspec/changes/<id>/tasks.md` -> `docs/changes/<id>/tasks.md`
- `openspec/changes/<id>/specs/**` -> `contracts.md` 或 contract links

Superpowers adapter：

- `superpowers:brainstorming` -> 只辅助 Brainstorming / Brief。
- `superpowers:test-driven-development` -> 只辅助 Contract / Implementation。
- `superpowers:systematic-debugging` -> 只辅助 fact-discovery / implementation / verification。
- `superpowers:verification-before-completion` -> 只辅助 Verification。

## 外部来源

- OpenSpec GitHub releases: https://github.com/Fission-AI/OpenSpec/releases
- OpenSpec package metadata: https://github.com/Fission-AI/OpenSpec/blob/main/package.json
- OpenSpec docs: https://github.com/Fission-AI/OpenSpec/tree/main/docs
- Superpowers GitHub: https://github.com/obra/superpowers
- Superpowers release notes: https://github.com/obra/superpowers/blob/main/RELEASE-NOTES.md
- Superpowers Codex plugin manifest: https://github.com/obra/superpowers/blob/main/.codex-plugin/plugin.json

