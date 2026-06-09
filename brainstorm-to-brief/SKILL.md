---
name: brainstorm-to-brief
description: Use when a raw idea, vague goal, product concept, feature request, PoC thought, or process change needs option exploration, scope, non-goals, risks, and success criteria before it becomes a stable brief, including after optional companion brainstorming via superpowers:brainstorming.
---

## Harness Precondition

应用本 skill 前，先确认 `harness-engineering` 已经完成当前 layer 和本地治理义务判断。若尚未完成，停止本 skill，返回 `harness-engineering`；不要让本 skill 充当入口路由。

# Brainstorm To Brief

## 概览

把模糊想法通过受约束的头脑风暴收敛成稳定 brief。目标不是马上定实现，而是先澄清目标、边界、非目标、风险和最小下一步。

该 skill 覆盖 harness engineering 的前三层：

```text
Idea -> Brainstorming -> Brief
```

## 使用原则

- 先发散，再收敛。
- 先问目标和边界，再谈方案。
- 先识别非目标和风险，再进入架构、ADR、契约或实现。
- 不把 brainstorm 当成最终决策；brief 才是下一层输入。
- 如果用户只是在探索，不要直接改代码。

## 输入判断

把用户请求当作 Idea，当它具有以下特征之一：

- 只有方向，没有明确交付物。
- 有多个可能方案，需要比较取舍。
- 可能影响架构、契约、流程或项目阶段。
- 用户在问“能不能”“该不该”“怎么做比较好”。
- 请求里包含新概念，但概念边界还没定清楚。

如果请求已经有清楚 brief、契约和验收标准，可以跳过本 skill，进入后续层级。

## Brainstorming 流程

1. 复述 Idea
   - 用一句话确认用户真正想解决的问题。
   - 区分目标、手段和临时想法。

2. 拉出约束
   - 当前阶段是什么。
   - 哪些东西不能做。
   - 哪些外部依赖、成本、风险或时间限制会影响方案。

3. 发散方案
   - 给出 2 到 4 个可行方向。
   - 每个方向说明适用场景、收益、代价和风险。
   - 不要只给一个看似确定的方案。

4. 收敛判断
   - 推荐一个最小可验证方向。
   - 说明为什么现在做这个，而不是其它方向。
   - 明确哪些工作应该排到后面。

5. 输出 Brief 草案
   - 把讨论结果整理成稳定输入。
   - brief 应能直接交给 Architecture、ADR、Contract 或 Implementation 层使用。

## Companion 能力借用

当 harness 当前层级是 `brainstorming` 时，可以把 `superpowers:brainstorming` 当作 companion capability 使用，但本 skill 仍是本地 owner。

可借用：

- 探索项目上下文。
- 一次只问一个问题。
- 给出 2 到 3 个方案及取舍。
- 做 scope decomposition。
- 需要视觉比较时使用 visual companion。
- 设计时关注边界、组件、数据流、错误处理和测试。

必须拦截：

- 不接受 `superpowers:brainstorming` 的 terminal state。
- 不自动 invoke `superpowers:writing-plans`。
- 不自动写 `docs/superpowers/specs/...`。
- 不自动 commit。
- 不跳过 Brief、Architecture、ADR、Contract 或 Readiness。

输出必须回到 harness：`Brainstorming` 层产出方案、风险、非目标和 Brief 草案，再由 harness transition gate 判断下一层。

## Brief 模板

```markdown
# Brief: <名称>

## Goal
一句话说明要解决什么问题。

## Context
说明背景、当前阶段、已知事实和相关约束。

## Non-Goals
列出当前明确不做的事情。

## Options Considered
列出比较过的方案和主要取舍。

## Decision / Direction
说明当前推荐方向。若还不能决策，说明缺少什么证据。

## Success Criteria
说明什么结果算这一阶段完成。

## Risks / Unknowns
列出仍未验证的风险和未知点。

## Next Layer
说明下一步应进入 Architecture、ADR、Contract、Implementation，还是继续 Brainstorming。
```

## 退出条件

只有满足以下条件，才算完成 Brainstorming：

- Goal 可以用一句话描述。
- Non-Goals 已明确。
- 至少比较过一个备选方向或说明为什么没有备选。
- 有推荐方向，或明确说明缺少什么证据。
- 下一层级被明确标出。

## 禁止捷径

- 不要把第一个想到的方案直接写成实现计划。
- 不要在用户还没确认目标时替用户定需求。
- 不要只列优点，不列代价和风险。
- 不要把 brainstorming 输出说成 ADR 或最终架构。
- 不要因为用户想快点做，就省略 non-goals 和 success criteria。

## 输出格式

如果用户只是询问建议，输出简短分析和推荐方向。

如果用户要求“整理”“沉淀”“写下来”“作为后续依据”，输出完整 Brief 草案。

如果用户要求继续执行下一层，先说明当前 brief 是否足够；不足时补 brief，足够时再进入下一层。
