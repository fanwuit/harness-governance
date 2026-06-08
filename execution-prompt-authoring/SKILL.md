---
name: execution-prompt-authoring
description: Use when Codex needs to turn an approved plan, gate list, queue item, change packet, or role-isolated workflow into a reviewable execution prompt pack for subagents, codex exec workers, autonomous-ready-loop runners, and integrators, including explicit rules for what may run in parallel, what must run in fresh codex exec sessions, what must be serialized, and what needs AI or human audit before execution.
---

# Execution Prompt Authoring

## 概览

使用本 skill 把已确认的计划、gate、队列项或 change packet 转成可审计的执行提示词包。提示词包必须能让 fresh agent、subagent、`codex exec` worker 或 integrator 在不依赖聊天历史的情况下工作。

中文友好：保留必要英文角色名，并在首次出现时给出中文解释。生成提示词和审计清单时优先使用中文。

## 角色

- `Execution Prompt Author`（执行提示词作者）：编写 prompt pack，不执行、不验收。
- `Execution Prompt Auditor`（执行提示词审计者）：独立审计 prompt pack，不实现、不改测试、不替代最终验收。
- `Controller`（主控）：调度审计、worker 和整合，串行更新共享状态。
- `Integrator`（整合者）：汇总 worker 结果、验证共享文件一致性、更新收口记录，不扩大功能范围。

## 适用边界

使用本 skill 时，先确认输入已经足够明确：

- 已有 approved plan、gate list、NEXT/TODO ready 项、change packet 或人工确认的执行方向。
- 需要判断 subagent 是否可并行。
- 需要判断哪些任务必须用 fresh `codex exec` worker。
- 需要把提示词落成可审计、可复用、可交接的文件或文本。

如果目标仍在想法发散、产品范围未确认、架构边界不清，先回到对应的 planning、brief、architecture 或 contract 层，不要直接写执行提示词。

## 输出产物

生成 `Execution Prompt Pack`（执行提示词包），至少包含：

```text
Objective:
Inputs:
Role map:
Execution matrix:
Controller prompt:
Subagent audit prompts:
Codex exec worker prompts:
Integrator prompt:
Shared-file serialization rules:
Verification commands:
Stop markers:
AI audit checklist:
Human approval checklist:
```

当项目已有 change packet、implementation task packet 或 runner prompt 位置时，优先写入项目约定路径。不要只把关键提示词留在聊天里，除非用户明确只要临时草案。

## 执行矩阵

为每个 gate、task 或 packet 明确一个执行类别：

```text
parallel-subagent-audit: 只允许并行审计，不改文件。
codex-exec-serial: 必须按依赖顺序用 fresh codex exec worker 执行。
codex-exec-parallel-safe: 可在独立 worktree/branch 或互不冲突 owner files 下并行执行。
controller-serialized: 只能由 controller 或 integrator 串行更新共享文件。
blocked-human-approval: 进入产品实现、跨阶段、改优先级或扩大范围前需要人工确认。
blocked-missing-packet: 缺少自包含 packet、owner files、验证命令或 stop condition。
```

不要把“能并行审计”等同于“能并行实现”。只要会修改同一工作树、同一共享状态文件、同一 contract/test 文件，默认不可并行实现。

## Prompt 编写规则

每段 prompt 必须自包含，并写清：

- `Role`：当前 worker 是 Planner、Contract/Test Writer、Implementer、Reviewer/Verifier、Auditor 还是 Integrator。
- `Inputs`：必须读取的稳定文件路径。
- `Allowed changes`：允许修改的文件或目录。
- `Forbidden changes`：禁止修改的文件、目录、行为和 scope。
- `Parallelism`：是否允许 subagent 并行，是否允许 `codex exec` 并行。
- `Verification`：必须运行的命令或无法运行时的记录要求。
- `Done when`：完成条件。
- `Stop conditions`：必须停止并上报的条件。
- `Final marker`：worker 结束时必须输出的 marker。

不要在 Author 角色里预写验收结论。验收必须由独立 Reviewer/Verifier 或 Integrator 基于新鲜证据完成。

## Audit 规则

AI audit 可以审计：

- prompt pack 是否自包含。
- role 是否混乱。
- parallelism matrix 是否过度乐观。
- 哪些任务必须 fresh `codex exec`。
- owner files、forbidden files、verification、stop markers 是否齐全。
- 是否违反仓库规则、change packet、readiness gate 或 scope 边界。

Human approval 适合处理：

- 是否进入产品实现。
- 是否改变最高优先级。
- 是否跨阶段或扩大范围。
- 是否接受并行执行带来的冲突风险。
- 是否允许修改共享状态、阶段 gate 或长期决策。

如果 AI audit 发现 prompt pack 会导致实现者同时写测试并验收自己、绕过 fresh worker、或修改共享文件冲突，必须要求修改 prompt pack，不要继续执行。

## 常用模板

Controller prompt 最小模板：

```text
你是 Controller。根据 <input files> 生成或执行 Execution Prompt Pack。
先判断每个 task 的执行类别：parallel-subagent-audit / codex-exec-serial / codex-exec-parallel-safe / controller-serialized / blocked-human-approval / blocked-missing-packet。
subagent 只做审计，不改文件。实际实现必须按执行矩阵启动 fresh worker。
共享状态文件只能由 Controller 或 Integrator 串行更新。
最后输出执行矩阵、需要审计的 prompt、以及需要人工确认的点。
```

Subagent audit prompt 最小模板：

```text
你是 Execution Prompt Auditor。只审计 <prompt pack or task>，不修改文件、不实现、不验收。
检查 role、inputs、owner files、forbidden changes、parallelism、verification、done-when、stop conditions 和 final marker。
输出结论：APPROVE / NEEDS_REVISION / BLOCKED，并列出必须修改的问题。
```

Codex exec worker prompt 最小模板：

```text
你是 fresh codex exec worker。只执行 <task packet> 指定角色。
不要依赖聊天历史；先读取 prompt 中列出的仓库文件。
只修改 allowed changes；遇到 forbidden changes 或 scope 扩大必须停止。
完成后运行 verification，更新指定持久化状态，并输出唯一 final marker。
```

Integrator prompt 最小模板：

```text
你是 Integrator。只整合已完成 worker 的结果，不实现新功能。
检查共享文件、verification record、queue 状态和 prompt pack 执行矩阵是否一致。
运行结构和阶段检查。发现漂移只修状态和导航，或标记 blocked。
```

## 完成标准

只有在以下条件满足时，才能说 prompt pack ready：

- Author 和 Auditor 角色已分离，或无法分离的原因已记录。
- 每个任务都有明确执行类别和依赖顺序。
- 下一个执行者不需要聊天历史即可工作。
- 并行审计和并行实现被明确区分。
- 需要 human approval 的事项没有被 AI 自行批准。
- 共享文件更新规则明确且默认串行。
