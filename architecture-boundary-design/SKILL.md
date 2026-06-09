---
name: architecture-boundary-design
description: Use when an existing brief or agreed direction needs system boundaries, responsibilities, data flow, ownership, runtime/deployment boundaries, component separation, or ADR candidate discovery before contracts or implementation.
---

## Harness Precondition

应用本 skill 前，先确认 `harness-engineering` 已经完成当前 layer 和本地治理义务判断。若尚未完成，停止本 skill，返回 `harness-engineering`；不要让本 skill 充当入口路由。

# Architecture Boundary Design

## 概览

把 brief 转换成系统边界、职责、数据流和决策点。Architecture 层不负责写最终代码，也不负责替代 ADR；它负责让系统怎么分、谁负责什么、数据怎么流、哪里需要决策变清楚。

该 skill 覆盖 harness engineering 的这段：

```text
Brief -> Architecture -> ADR
```

## 什么时候使用

以下情况使用本 skill：

- brief 已经说明目标和非目标，但系统边界还不清楚。
- 涉及多个模块、服务、进程、语言、团队或外部系统。
- 需要判断哪些能力放在哪一层。
- 需要定义数据流、调用流、部署边界或运行时边界。
- 需要区分产品功能、平台能力、外部能力、harness/probe。
- 需要找出哪些问题应该写 ADR，哪些可以直接进入 Contract。

如果只是单模块小改动且边界已由现有架构定义，可以不使用本 skill。

## 设计流程

1. 读取 Brief
   - 识别 Goal、Non-Goals、Success Criteria、Risks。
   - 如果 brief 不足，回到 Brainstorming / Brief，不要硬做架构。

2. 列出参与方
   - 用户或外部 actor。
   - 前端、后端、worker、插件、服务、外部系统。
   - 数据存储、队列、缓存、文件系统、第三方服务。

3. 定义职责边界
   - 每个组件负责什么。
   - 每个组件明确不负责什么。
   - 哪些能力是长期产品能力，哪些只是 harness/probe。

4. 定义数据流和控制流
   - 请求从哪里进入。
   - 数据在哪里被创建、转换、校验、存储、消费。
   - 哪些引用或路径不能跨边界泄漏。

5. 定义运行时和部署边界
   - 哪些逻辑同进程，哪些跨进程，哪些跨机器。
   - 哪些依赖必须本地存在，哪些通过 API 或 artifact 传递。
   - 哪些失败需要隔离、超时、取消或重试。

6. 标出决策点
   - 会长期影响实现或契约的点进入 ADR。
   - 只是数据形态或协议细节的点进入 Contract。
   - 只是任务执行顺序的点进入计划或 NEXT。

7. 输出 Architecture Brief
   - 生成可供 ADR 和 Contract 使用的架构摘要。

## Architecture Brief 模板

```markdown
# Architecture Brief: <名称>

## Context
来自 brief 的目标、非目标和约束。

## Actors / Components
列出参与方和组件。

## Responsibilities
说明每个组件负责什么、不负责什么。

## Data Flow
说明主要数据、引用、artifact 或事件如何流动。

## Runtime / Deployment Boundary
说明进程、机器、外部系统、缓存、文件和网络边界。

## Invariants
必须长期保持的边界或事实。

## Risks / Unknowns
仍不清楚或需要验证的风险。

## ADR Candidates
需要写 ADR 的决策点。

## Contract Candidates
需要 schema、example、fixture、probe 或 check 的契约点。

## Not In Scope
架构层明确不处理的事项。
```

## ADR 候选判断

进入 ADR 的问题通常满足：

- 有多个可行架构方向。
- 会影响长期边界或部署方式。
- 会限制后续实现选择。
- 需要记录为什么不选某个方案。
- 是团队或后续 agent 容易反复争论的问题。

直接进入 Contract 的问题通常是：

- 决策已经明确，只差数据形态。
- 需要固定 API、schema、fixture、probe 或检查脚本。
- 需要验证成功/失败路径。

## 质量检查

架构输出完成前检查：

- 每个组件是否有清楚职责。
- 是否写清楚组件不负责什么。
- 数据流是否从入口到出口完整。
- 是否标出跨进程、跨服务、跨外部系统边界。
- 是否标出错误、超时、缓存、权限或路径泄漏风险。
- 是否区分 ADR 候选和 Contract 候选。
- 是否避免提前写实现细节。

## 禁止捷径

- 不要把架构写成类名和文件名清单。
- 不要只画组件，不说明数据怎么流。
- 不要只写负责什么，不写不负责什么。
- 不要把 harness/probe 临时能力直接归入产品架构。
- 不要把架构文档当 ADR；关键取舍仍要进入 ADR。
- 不要把架构文档当 Contract；可执行验证仍要进入 schema、fixture、probe 或 check。

## 输出格式

如果用户只问架构建议，输出简短边界分析和推荐方向。

如果用户要求沉淀架构，输出完整 Architecture Brief。

如果用户要求继续下一层，先列出 ADR Candidates 和 Contract Candidates，再进入对应层。
