---
name: contract-first-development
description: Use when an agreed behavior, API, schema, file format, CLI, fixture, probe, example, PoC conclusion, external interaction, or implementation boundary needs executable contracts or checks before or while writing production code.
---

## Harness Precondition

应用本 skill 前，先确认 `harness-engineering` 已经完成当前 layer 和本地治理义务判断。若尚未完成，停止本 skill，返回 `harness-engineering`；不要让本 skill 充当入口路由。

# Contract First Development

## 概览

先把行为固定成可机械检查的契约，再进入实现。契约不是只写接口名字，而是让成功路径和关键失败路径都能被复现、验证和回归。

该 skill 覆盖 harness engineering 的这段：

```text
Contract -> Implementation -> Verification
```

## 什么时候必须先补 Contract

以下情况不要直接实现，应先补契约：

- 新增或修改 API、schema、消息、事件、文件格式、CLI 参数或配置格式。
- 行为涉及多个模块、进程、服务、语言或外部系统。
- PoC 结论需要被后续复用。
- 失败路径、诊断码、权限边界、路径边界或缓存边界很重要。
- 用户说“先验证”“先固定”“后面容易误会”“方便其它项目复用”。
- 实现看似能跑通，但还没有可重复检查证明它应该如何工作。

已有稳定契约且改动很小，可以直接实现，但仍要补或更新验证。这个例外不适用于新的外部集成、持久化状态、public contract 变更、跨边界行为或新的关键失败模式；这些情况必须先补或更新契约。

## Contract 可以是什么

按任务选择最小足够组合：

- schema：JSON Schema、OpenAPI、protobuf、数据库约束、类型定义。
- example：最小请求/响应、配置样例、输入输出样例。
- fixture：稳定测试数据、样例文件、外部输入快照。
- probe：用于观察真实行为的最小程序或命令。
- check script：可重复运行的机械检查。
- acceptance test：端到端或集成测试。
- documentation invariant：必须被长期遵守的边界说明。

优先选择能被机器执行的产物。文档说明不能替代可执行检查，除非该行为确实无法机械验证。

## Contract Delta 推荐结构

当任务使用 change packet，或需要表达“当前行为 -> 目标行为”的增量时，在 `contracts.md` 或 contract plan 中固定以下结构：

```markdown
## Current behavior
当前可观察行为、已有 schema / fixture / probe / check，或明确缺口。

## Proposed behavior / contract delta
本次变更对行为契约的增量。

## Contract artifacts
新增或更新的 schema/example/fixture/probe/check/acceptance test 路径。

## Acceptance checks
可以机械运行的验收检查。

## Failure cases
关键失败路径和断言方式。
```

这个结构只负责说明 contract delta。它不能替代可执行 schema、fixture、probe、check 或 acceptance test；如果只能使用 documentation invariant，必须说明为什么无法机械验证。

## TDD Contract Cycle

当任务适合 red / green / refactor，读取 `references/tdd-contract-cycle.md`。本地映射规则：

- Red：先写会失败的 contract artifact 或测试，并记录失败证据。
- Green：只实现让 contract/test 通过的最小切片，进入产品实现前仍必须有 Implementation Entry Record。
- Refactor：验证通过后只做局部整理，不扩大 contract delta。

TDD discipline 不能替代 readiness、Implementation Entry Record 或 Review / Next；测试通过也不能单独批准实现完成。

## 工作流程

1. 定义行为
   - 用一句话说明要固定什么行为。
   - 明确输入、输出、成功条件和失败条件。

2. 选 contract 形态
   - 数据结构优先 schema + example。
   - 外部行为优先 fixture + probe + check。
   - 边界规则优先 ADR + check。
   - UI 行为优先可截图/可交互检查 + 状态断言。

3. 先写最小样例
   - 样例要小，但必须真实覆盖关键语义。
   - 不要为了方便测试而改变真实协议。

4. 补失败路径
   - 至少覆盖一个关键失败路径。
   - 失败输出要有可断言的 code、message、状态或结构。

5. 写机械检查
   - 检查必须能在干净工作区重复运行。
   - 失败信息要直接指出哪个契约被破坏。
   - 检查不要依赖聊天上下文或未记录的本机状态。

6. 实现最小代码
   - 只写足够让契约通过的实现。
   - 不要顺手扩展到产品完整功能。

7. 运行验证
   - 运行与契约和实现匹配的检查。
   - 失败先修复；不能运行时记录原因和风险。

## 进入 Implementation 的条件

只有满足以下条件，才进入实现：

- 成功路径已有样例或 fixture。
- 至少一个关键失败路径可被检查。
- 契约名称、字段、语义和边界已经清楚。
- 检查脚本或测试能证明契约没有被破坏。
- 实现范围被限制在让契约通过所需的最小集合。

## 禁止捷径

- 不要用“手动跑通一次”代替 contract-fixed。
- 不要只测输出数量、截图相似或日志包含某词，就声称行为固定。
- 不要把实现代码当成契约；契约应能约束实现。
- 不要只覆盖成功路径，不覆盖关键失败路径。
- 不要为了让检查简单而改变真实协议。
- 不要让检查依赖绝对临时路径、隐藏本机状态或聊天记录。

## 输出格式

如果用户要求设计契约，输出 contract plan：

```markdown
## Behavior
要固定的行为。

## Contract Artifacts
需要新增或更新的 schema/example/fixture/probe/check。

## Success Path
成功路径如何验证。

## Failure Path
至少一个失败路径如何验证。

## Implementation Boundary
实现只允许做到哪里。

## Verification Command
应运行哪些检查。
```

如果用户要求直接实现，先判断契约是否已足够；不足时先补契约，再实现。
