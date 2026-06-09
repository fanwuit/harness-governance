---
name: adr-writing
description: Use when an already-identified architectural decision, technology choice, contract boundary, deployment model, data ownership rule, tradeoff, rejected alternative, or long-lived project rule must be recorded as an ADR or decision note.
---

## Harness Precondition

应用本 skill 前，先确认 `harness-engineering` 已经完成当前 layer 和本地治理义务判断。若尚未完成，停止本 skill，返回 `harness-engineering`；不要让本 skill 充当入口路由。

# ADR Writing

## 概览

把架构判断和关键取舍固化成 ADR。ADR 不是会议纪要，也不是实现计划；它记录一个会长期影响项目的决策、为什么这么做、放弃了什么、会带来什么后果，以及如何验证。

该 skill 覆盖 harness engineering 的这段：

```text
Architecture -> ADR -> Contract
```

## 什么时候需要 ADR

以下情况应写 ADR：

- 选择会影响多个模块、团队、服务或后续阶段。
- 边界需要被未来反复引用，例如 Web/API/Worker、服务端/客户端、内部/外部系统。
- 存在多个可行方案，需要记录为什么选其中一个。
- 某个禁止事项很重要，例如“不复制外部系统逻辑”“不在前端暴露内部路径”。
- 决策会影响契约、schema、fixture、部署、测试或安全边界。
- 用户或团队已经反复讨论同一问题，需要一个稳定结论。

以下情况通常不需要 ADR：

- 单文件小修复。
- 纯格式化、重命名或无行为变化的整理。
- 已有 ADR 明确覆盖的执行细节。
- 只需要在任务 brief 或 NEXT 队列记录的短期事项。

## ADR 必备结构

```markdown
# NNNN 标题

## Context
当前背景、问题、约束、已知事实。

## Decision
明确选择什么。用肯定句，不要只描述讨论过程。

## Alternatives Considered
列出主要备选方案，以及为什么没有选。

## Consequences
说明正面影响、代价、风险和后续约束。

## Validation
说明如何验证这个决策被正确执行。

## Not In Scope
说明这个 ADR 不解决什么，防止范围扩张。
```

项目有自己的 ADR 模板时，优先遵循项目模板，但仍要保留这些语义。

## 写作流程

1. 判断决策点
   - 用一句话写出“我们需要决定什么”。
   - 如果只是任务说明，先回到 Brief，不要写 ADR。

2. 收集上下文
   - 记录当前阶段、约束、已有事实、相关文档或证据。
   - 区分事实、假设和偏好。

3. 写 Decision
   - 决策必须能被执行。
   - 避免“考虑使用”“建议可能”“后续再看”这种不稳定措辞。

4. 写 Alternatives
   - 至少记录一个重要备选方案，或说明为什么没有真实备选。
   - 备选方案要写取舍，不要只写它“不好”。

5. 写 Consequences
   - 写清楚收益，也写清楚成本。
   - 包括对后续契约、实现、测试、部署和文档的影响。

6. 写 Validation
   - 优先使用 schema、fixture、probe、check、test 或 CI 验证。
   - 如果只能人工验证，说明人工验证的证据形式。

7. 指向下一层
   - ADR 完成后，通常进入 Contract 层。
   - 如果仍缺事实，回到 Brainstorming、Brief 或 Architecture。

## 质量检查

ADR 写完后检查：

- Decision 是否是一句明确选择。
- Context 是否包含足够事实，而不是只写愿望。
- Alternatives 是否记录真实取舍。
- Consequences 是否包含代价和约束。
- Validation 是否可执行、可复查。
- Not In Scope 是否阻止了常见范围扩张。
- 未来 agent 是否能只读 ADR 就理解边界。

## 禁止捷径

- 不要把 ADR 写成聊天摘要。
- 不要把 ADR 写成实现步骤清单。
- 不要只写选中的方案，不写备选方案。
- 不要只写好处，不写代价。
- 不要把“稍后验证”当成 Validation。
- 不要让 ADR 承担 schema、fixture 或测试的职责；ADR 只说明应该如何验证，具体证据应落到 Contract 或 Verification 层。

## 输出格式

如果用户只问“要不要写 ADR”，先判断并给出理由。

如果用户要求写 ADR，输出完整 ADR 草案。

如果用户要求落文件，遵循当前仓库的 ADR 编号、模板、目录和文档地图规则。
