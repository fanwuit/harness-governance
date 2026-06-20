# Skill Priority / 技能优先级

harness governance 拥有入口路由最高优先权。任何第三方 skill 不得在 harness 完成入口分类之前执行。

Harness governance holds highest-priority entry routing. No third-party skill may execute before harness completes entry classification.

## Rule / 规则

Do not assume any third-party skill exists in the target environment. Before routing to a companion workflow, check the current skill list for matching local governance skills. Local governance skills own layer, boundary, role isolation, readiness, contract, verification, and review/next decisions. Third-party skills are companion execution workflows, not replacements for local governance skills.

不要假设目标环境中存在任何第三方 skill。路由到伴生工作流之前，先检查当前 skill 列表中是否有匹配的本地治理 skill。本地治理 skill 拥有层级、边界、角色隔离、就绪、契约、验证和 review/next 决策权。第三方 skill 是伴生执行工作流，不能替代本地治理 skill。

## Entry Gate / 入口门控

For development, planning, implementation, verification, queue, or handoff requests, route through `harness governed-start` before any third-party workflow. This includes empty projects, demos, small games, simple feature requests, and "continue" / "next" requests.

对于开发、规划、实施、验证、队列或交接请求，必须先通过 `harness governed-start` 路由，再处理任何第三方工作流。包括空项目、demo、小游戏、简单功能请求和"继续"/"下一步"请求。

If a third-party skill also appears to match because of a broad session-start rule, treat it as a companion check only. It may be loaded when required, but it does not own entry routing and must not trigger its own workflow chain until harness has selected the current layer.

如果第三方 skill 因宽泛的会话启动规则而匹配，仅将其视为伴生检查。可按需加载，但不拥有入口路由权，在 harness 选定当前层级之前不得触发其工作流链。

A third-party skill is not exempt from harness entry even when its metadata says "starting any conversation" or "before ANY response". Project-level harness entry and local governance routing run first.

即使第三方 skill 的元数据声明"starting any conversation"或"before ANY response"，也不得绕过 harness 入口。项目级 harness 入口和本地治理路由优先执行。

## Companion Capability Adapter / 伴生能力适配

When the current harness layer allows a companion workflow, import only the companion techniques that produce the current layer's required output. Ignore companion terminal states, required sub-skills, default artifact paths, commits, and next-workflow transitions unless the harness layer map explicitly approves them.

当当前 harness 层级允许伴生工作流时，仅导入产出该层级所需输出的伴生技巧。忽略伴生终止状态、必需子 skill、默认产物路径、提交和下一工作流转换，除非 harness 层级映射明确批准。

Local absorption principle: borrow engineering moves, not workflow ownership. Every borrowed move must name the local owner skill, allowed technique, forbidden import, stable evidence, and verification path.

本地吸收原则：借用工程动作，不借用工作流所有权。每个借用的动作必须声明本地所有者 skill、允许的技巧、禁止的导入、稳定证据和验证路径。

Adapter rules / 适配规则：

1. Convert companion `MUST`, hard gate, terminal state, `REQUIRED SUB-SKILL`, or "invoke next skill" language into a harness next-layer candidate. / 将伴生的 `MUST`、硬门控、终止状态、`REQUIRED SUB-SKILL` 或"调用下一 skill"语言转换为 harness 下一层级候选。
2. Keep ownership with the primary local governance skill for the current layer. / 保持当前层级的所有权在本地治理 skill。
3. Use companion techniques only as helpers. / 仅将伴生技巧作为辅助使用。
4. Do not create companion-specific artifacts, commits, worktrees, implementation plans, subagents, branch-finish flows, or PR steps solely because a companion workflow says to do so. / 不要仅因伴生工作流要求就创建伴生专属产物、提交、工作树、实施计划、子代理、分支完成流程或 PR 步骤。
5. Resume the harness transition gate after the companion-supported output is produced. / 伴生支持的输出产出后，恢复 harness 转换门控。

## Companion-Only Containment / 伴生隔离约束

Third-party skills are never layer owners under harness governance. Loading a third-party skill gives access to useful companion instructions, but it does not authorize following that skill's terminal state, hard gates, checklist, or next-skill transition when those would move the task outside the current harness layer.

第三方 skill 在 harness 治理下永远不是层级所有者。加载第三方 skill 可获取有用的伴生指令，但不授权遵循其终止状态、硬门控、检查清单或下一 skill 转换——当这些会将任务移出当前 harness 层级时。

Containment rules / 隔离规则：

1. Name the current harness layer before applying the companion skill. / 应用伴生 skill 前先声明当前 harness 层级。
2. Name the local governance skill that owns that layer. / 声明拥有该层级的本地治理 skill。
3. Apply only the companion instructions that support that layer's required output. / 仅应用支持该层级所需输出的伴生指令。
4. Stop before any companion instruction that would skip or replace Architecture, ADR, Contract, Readiness, Verification, or Review / Next. / 在任何会跳过或替代架构、ADR、契约、就绪、验证或 Review/Next 的伴生指令前停止。
5. If the companion workflow conflicts with the harness layer map, say so and continue with the local governance skill. / 如果伴生工作流与 harness 层级映射冲突，声明冲突并继续使用本地治理 skill。

## Local Absorption Map / 本地吸收映射

| Borrowed technique / 借用技巧 | Local owner / 本地所有者 | Stable evidence / 稳定证据 |
|---|---|---|
| One-question brainstorming and option comparison | `brainstorm-to-brief` | Brief-ready output using `references/brainstorming-template.md` |
| Red / green / refactor discipline | `contract-first-development` | Contract artifact, failing/passing command, Implementation Entry Record |
| Systematic debugging steps | `observable-fact-discovery` | Repro, observed facts, isolation, hypothesis result, fix verification |
| Completion evidence before claims | `review-next-governance` | Completion Evidence record |
| Review feedback handling | `review-next-governance` / `agent-role-isolation` | Review Feedback record and verification |
| Plan execution checkpoints | `harness governed-start` / `planning-with-files` | Chosen carrier from `planning-carrier-decision.md` |
| Parallel agent coordination | `execution-prompt-authoring` / `agent-role-isolation` | Execution matrix and Integrator checks |
| Worktree / branch finish discipline | `review-next-governance` | Branch Finish record and explicit user/project approval |

## Routing Matrix / 路由矩阵

| Situation / 场景 | Companion / 伴生 | Local fallback / 本地回退 | Requirement / 要求 |
|---|---|---|---|
| Creative product, feature, or design work | third-party brainstorming | `brainstorm-to-brief` | preferred |
| Multi-step implementation planning | third-party plan writing | `planning-with-files` or project queue | preferred |
| Executing a written plan | third-party plan execution | harness queue + checkpoints | preferred |
| Independent parallel tasks | third-party parallel dispatch | Execute serially and record handoff state | optional |
| Bug, test failure, or unexpected behavior | third-party systematic debugging | Reproduce, observe, isolate, fix, verify | preferred |
| Feature or bugfix implementation | third-party TDD | `contract-first-development` + target-local tests | preferred |
| Before claiming completion | third-party verification | Run explicit verification commands and report evidence | preferred |
| Receiving review feedback | third-party code review | Default: verify, challenge unclear feedback, then patch | preferred |
| Requesting review before merge | third-party review request | Run local review checklist and verification | optional |
| Finishing a branch | third-party branch finish | `review-next-governance` + git status, commit, push | optional |
| Creating or updating skills | third-party skill writing | `skill-creator` when available | preferred |
| Starting isolated feature work | third-party worktree | Use current workspace unless project rules require isolation | optional |

## Disclosure Template / 披露模板

When a preferred companion is unavailable / 当首选伴生不可用时：

```text
Preferred companion skill <skill-name> is unavailable in this environment. Continuing with <local-fallback>.
首选伴生 skill <skill-name> 在当前环境不可用。继续使用 <local-fallback>。
```

When a companion workflow overlaps local governance / 当伴生工作流与本地治理重叠时：

```text
Local governance skills: <selected local skills>
Companion workflow skills: <selected companion skills>
Routing decision: local governance owns <layer/boundary/readiness/etc.>; companion workflow executes <workflow>.
路由决策：本地治理拥有 <层级/边界/就绪等>；伴生工作流执行 <工作流>。
```
