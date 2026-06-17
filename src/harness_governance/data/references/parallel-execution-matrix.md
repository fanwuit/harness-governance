# Parallel Execution Matrix / 并行执行矩阵

Localizes the collaboration advantages of dispatching parallel agents / subagent-driven development into auditable execution rules for this project.

用于把 dispatching parallel agents / subagent-driven development 的协作优势落成本项目可审计执行规则。

## Local Owner / 本地所有者

- Owner skill: `execution-prompt-authoring`
- Supporting skill: `agent-role-isolation`
- Stable evidence: execution matrix, owner files, shared-file serialization rules, integrator verification / 稳定证据：execution matrix、owner files、shared-file serialization rules、integrator verification

## Safe Parallel Work / 安全并行工作

Generally safe to parallelize:

通常可以并行：

- Read-only audits. / 只读审计。
- Independent module exploration. / 独立模块探索。
- Independent test design, but final test commits require serial review. / 独立测试设计，但最终测试落盘需串行 review。
- Prompt pack drafts for different owner files. / 对不同 owner files 的 prompt pack 草案。
- Multiple reviewers making independent comments on the same diff. / 多个 reviewer 对同一 diff 做独立评论。

## Serialized Work / 串行化工作

Must be serialized by default:

默认必须串行：

- `README.md`, `AGENTS.md`, package scripts. / `README.md`、`AGENTS.md`、package scripts。
- `NEXT.md`, checkpoint, done archive, change packet status. / `NEXT.md`、checkpoint、done archive、change packet 状态。
- Shared schema, shared fixture, public API contract. / shared schema、shared fixture、public API contract。
- Implementation of the same source file. / 同一源文件实现。
- Additions, deletions, or modifications to the same test file. / 同一测试文件的增删改。
- Version / release / install documentation. / version / release / install 文档。

## Integrator Rules / 整合器规则

The integrator may only integrate already-completed output:

Integrator 只能整合已经完成的输出：

- Read worker final marker and verification. / 读取 worker final marker 和 verification。
- Check whether owner files exceed boundaries. / 检查 owner files 是否越界。
- Re-run structural checks when merging shared files. / 合并共享文件时重新运行结构检查。
- Mark as blocked or request the controller to re-split when conflicts are found. / 发现冲突时标记 blocked 或要求 controller 重新拆分。
- Do not add new features, relax contracts, or self-verify on behalf of workers. / 不新增功能，不放宽 contract，不替 worker 做自我验收。

## Prompt Fields / 提示词字段

Each parallel task must clearly state:

每个并行任务必须写清：

```markdown
Parallel task:
- Role:
- Owner files:
- Read-only files:
- Allowed changes:
- Forbidden changes:
- Shared files touched: yes | no
- Parallel safety reason:
- Verification:
- Final marker:
- Integrator checks:
```

## Worktree Guidance / Worktree 指引

Consider independent worktree / branch for parallel implementation only when:

并行实现只有在满足以下条件时才考虑独立 worktree / branch：

- Owner files do not overlap. / owner files 不重叠。
- Verification can run independently. / verification 可以独立运行。
- The integrator has a clear merge order. / integrator 有明确合并顺序。
- The user or project rules allow creating additional workspaces. / 用户或项目规则允许创建额外工作区。

Do not create worktrees by default; when the current workspace can safely complete work serially, prefer simplicity.

不默认创建 worktree；当前 workspace 能安全串行完成时，优先保持简单。
