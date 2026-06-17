# Brainstorming Template / 头脑风暴模板

Localizes brainstorming techniques into `brainstorm-to-brief`, but output still belongs to the harness Brainstorming / Brief layer.

用于把头脑风暴技巧本地化到 `brainstorm-to-brief`，但输出仍归 harness 的 Brainstorming / Brief 层所有。

## Local Owner / 本地所有者

- Owner skill: `brainstorm-to-brief`
- Harness layer: `brainstorming` or `brief` / harness 层：`brainstorming` 或 `brief`
- Stable evidence: brief draft, option comparison, risks/non-goals, next layer candidate / 稳定证据：brief 草案、方案对比、风险/非目标、下一层候选

## Allowed Technique / 允许的技巧

- Ask only one key question at a time; avoid throwing out multiple clarifications simultaneously.
- Confirm the user's real problem before comparing solutions.
- Present 2 to 4 options, explaining benefits, costs, risks, and applicable conditions.
- Perform scope decomposition: separate what must be done now, what can be deferred, and what is explicitly out of scope.
- When the problem involves interfaces, flows, or user experience, use a textual visual companion: describe key interface states, interaction paths, failure scenarios, and visual hypotheses that need verification.

- 一次只问一个关键问题，避免同时抛出多组澄清。
- 先确认用户真正要解决的问题，再比较方案。
- 给出 2 到 4 个方案，并说明收益、代价、风险和适用条件。
- 做 scope decomposition：把当前必须做、可后置、明确不做分开。
- 当问题涉及界面、流程或用户体验时，可使用文字化 visual companion：描述关键界面状态、交互路径、失败场景和需要验证的视觉假设。

## Forbidden Import / 禁止导入

- Do not write to third-party skill output directories (e.g. `docs/superpowers/*`).
- Do not treat brainstorming output directly as an implementation plan.
- Do not skip Brief, Architecture, ADR, Contract, or Readiness just because a solution looks clear.
- Do not automatically create commits, branches, worktrees, or external workflow artifacts.

- 不写第三方 skill 的输出目录（如 `docs/superpowers/*`）。
- 不把 brainstorming 输出直接当 implementation plan。
- 不因为方案看起来清楚就跳过 Brief、Architecture、ADR、Contract 或 Readiness。
- 不自动创建 commit、branch、worktree 或外部 workflow artifact。

## One-Question Pattern / 单问题模式

When key information is missing, prefer asking only one question:

当关键信息缺失时，优先只问一个问题：

```markdown
我需要先确认一个点：<问题>

为什么问：
- <这个答案会影响哪个方案或边界>
```

If you do not need to wait for the user, you can explicitly state an assumption and continue:

如果不需要等待用户，也可以明确假设继续：

```markdown
Assumption:
- <当前采用的保守假设>

Risk:
- <假设错误时会影响什么>
```

## Option Comparison Template / 方案对比模板

```markdown
## Options

### Option A: <名称>
- Best when:
- Benefit:
- Cost:
- Risk:
- Evidence needed:

### Option B: <名称>
- Best when:
- Benefit:
- Cost:
- Risk:
- Evidence needed:

## Recommendation
- Recommended direction:
- Why now:
- Deferred:
```

## Brief-Ready Output / Brief 就绪输出

```markdown
## Goal

## Non-Goals

## Options Considered

## Decision / Direction

## Risks / Unknowns

## Success Criteria

## Next Layer
<Architecture | ADR | Contract | Implementation | Continue Brainstorming>
```

## Verification / 验证

Check upon completion:

完成时检查：

- Is at least one alternative recorded, or is there an explanation for why no alternative exists? / 是否至少记录一个备选方案，或说明为什么没有备选。
- Are there explicit non-goals? / 是否有明确 non-goals。
- Is the next layer written as a harness layer, not an external workflow name? / 是否把下一层写成 harness layer，而不是外部 workflow 名称。
- Are there no promises of unverified implementation details? / 是否没有承诺未验证的实现细节。
