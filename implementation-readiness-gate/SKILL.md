---
name: implementation-readiness-gate
description: Use before entering implementation or writing product code, especially when a task moves from Contract to Implementation, starts coding in a Java/Vue/.NET/Worker/frontend/backend target, creates a new app/service/package, or an autonomous loop selects an implementation-ready item. Checks target-local architecture boundaries, ADR/decision state, contracts, lint/format baselines, unit tests, integration/contract tests, verification commands, and local AGENTS.md before allowing code changes.
---

# Implementation Readiness Gate

把这个 skill 作为 `Contract` 进入 `Implementation` 之前的强制准入门。

不要把 implementation readiness 当成“整个仓库一次性通过”的勾选项。必须按即将写代码的具体 target 单独判断。

这个 gate 是 target-entry gate，不是每个小改动都要重复执行的流程。某个 target 已经通过 readiness gate 后，该 target 内的小 bug fix 和小 feature 可以直接遵守已有规则、lint、测试和验证命令推进。

这个小改动例外不适用于新的外部集成、持久化状态、public contract 变更、新 runtime/dependency、跨 target 行为或新的关键失败模式。用户说“快点做”“直接实现”不等于 throwaway prototype，也不能绕过 readiness。

## 核心规则

在 target-local gate 通过前，不要写正式产品实现代码。

如果任一必需项缺失，先停止 implementation，创建或执行 readiness 任务，用稳定产物和机械检查补齐缺口。

当改动打开新 target、跨组件边界、增加新 runtime/dependency、修改 public contract、引入新的失败模式或扩大实现范围时，必须重新运行或扩展这个 gate。

## Target Scope

先识别 implementation target。常见例子：

- Java backend：`apps/platform-api`
- Vue/Web frontend：`apps/web-preview`、`apps/web-designer`
- Worker/runtime：`apps/external-worker`、`apps/designer-orchestrator`
- NX plugin：`apps/nx-plugin`
- Shared package：`packages/*`

每个 target 都需要自己的 readiness evidence。根目录的 `docs/linting.md` 或根级测试命令有价值，但不能替代 target-local lint、test、verification command 和 local coding rules。

## Reference Map

按 target 读取对应参考，不要一次性加载所有 reference：

- 通用 checklist：`references/checklist.md`
- Java backend：`references/java-backend-target.md`
- Vue/Web frontend：`references/web-frontend-target.md`
- Worker/runtime：`references/worker-runtime-target.md`
- Shared package：`references/shared-package-target.md`

## 必需 Gate

进入某个 target 的 implementation 前，确认该 target 已具备以下证据：

1. Architecture boundary
   - 组件职责清楚。
   - 数据流和 runtime/deployment boundary 清楚。
   - forbidden paths 明确。

2. ADR 或 decision state
   - 长期技术选择或边界选择已有 ADR。
   - 如果不需要 ADR，有稳定、可复核的说明解释原因。
   - 聊天中的临时同意不能替代长期边界、持久化、部署、所有权或 public contract 的 decision state。

3. Contract evidence
   - 即将实现的行为已有 API/schema/example/fixture/probe/check。
   - 成功路径和重要失败路径都有覆盖。

4. Lint 和 formatter baseline
   - target 已选择 lint/format 工具。
   - 命令已文档化且可运行。
   - generated files 和 external read-only references 已排除。

5. Unit test baseline
   - target 已有单元测试框架。
   - 命名和目录约定已记录。
   - 至少有一个最小测试或测试命令证明 baseline 可运行。

6. Integration 或 contract test baseline
   - 跨边界行为已有 integration、contract、fixture 或 harness check。
   - target 不能只依赖 unit tests 覆盖边界行为。

7. Verification command
   - target-specific verification command 存在。
   - 适合时已注册到项目标准 verification path。

8. Local agent rules
   - target 有本地 `AGENTS.md` 或等价稳定实现规则。
   - 规则覆盖命名、分层、禁止依赖、测试期望和 public/private 泄漏边界。

9. Commit/review policy
   - target 遵守项目提交和 review 规则。
   - autonomous worker 知道完成 ready 后是否自动 commit。

## 决策

如果所有必需项都通过：

- 进入最小 implementation slice。
- 保持 slice 在已批准 target 和 contract 边界内。
- 声明完成前运行 target-specific verification 和标准 verification。

如果 target 已通过 gate，且请求只是该 target 内的小 bug fix 或小 feature：

- 使用现有 target rules、lint、tests 和 verification commands。
- 不要重新创建 architecture、ADR、lint 或 test baseline。
- 行为受影响时补充或更新聚焦测试。
- 新外部集成、持久化、public contract、跨 target 行为或新关键失败模式不属于“小改动”。
- 只有 scope 扩大或跨 readiness boundary 时，才回到本 gate。

如果任一必需项缺失：

- 不要写 implementation code。
- 为缺失的 target-local baseline 新增或执行 readiness ready item。
- 优先补 `AGENTS.md`、lint config、test config、examples、schemas 和 check scripts。
- 更新 queue/status，让阻塞成为稳定记录，不只留在聊天里。

## Autonomous Loop 行为

当 autonomous runner 选中 implementation item：

- 先对被选 target 运行本 gate。
- 如果 gate 失败，按项目规则把 implementation item 替换成 readiness item，或用 boundary/block marker 停止。
- 不要用另一个 target 的 readiness evidence 替代当前 target。
- 除非队列项明确允许，不要为了“让测试通过”从一个 target 扩张到另一个 target。

## 常见结果

gate 通过后通常允许：

- 带 unit tests 的小型 in-memory service skeleton。
- 带 lint/build/test 的 static frontend consumer slice。
- 不含生产进程行为的 Worker contract harness。
- 受现有 schema/examples/checks 约束的 adapter implementation。

没有单独 gate 时不允许：

- 完整 HTTP controllers。
- Database persistence。
- Object storage integration。
- Authentication 或 authorization flows。
- Production Worker process supervision。
- External executable implementation。
- 完整 Vue Designer workflows。
- Release/package marketplace features。

## 汇报格式

使用本 skill 时汇报：

- 已评估 target。
- Gate 状态：pass 或 fail。
- 缺失的 readiness items。
- 该请求是否属于“已通过 gate 的 target 内小改动”。
- 下一步稳定产物或 ready item。
- 已运行或仍需运行的 verification commands。
