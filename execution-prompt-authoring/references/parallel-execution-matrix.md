# Parallel Execution Matrix

用于把 dispatching parallel agents / subagent-driven development 的协作优势落成本项目可审计执行规则。

## Local Owner

- Owner skill: `execution-prompt-authoring`
- Supporting skill: `agent-role-isolation`
- Stable evidence: execution matrix、owner files、shared-file serialization rules、integrator verification

## Safe Parallel Work

通常可以并行：

- 只读审计。
- 独立模块探索。
- 独立测试设计，但最终测试落盘需串行 review。
- 对不同 owner files 的 prompt pack 草案。
- 多个 reviewer 对同一 diff 做独立评论。

## Serialized Work

默认必须串行：

- `README.md`、`AGENTS.md`、package scripts。
- `NEXT.md`、checkpoint、done archive、change packet 状态。
- shared schema、shared fixture、public API contract。
- 同一源文件实现。
- 同一测试文件的增删改。
- version / release / install 文档。

## Integrator Rules

Integrator 只能整合已经完成的输出：

- 读取 worker final marker 和 verification。
- 检查 owner files 是否越界。
- 合并共享文件时重新运行结构检查。
- 发现冲突时标记 blocked 或要求 controller 重新拆分。
- 不新增功能，不放宽 contract，不替 worker 做自我验收。

## Prompt Fields

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

## Worktree Guidance

并行实现只有在满足以下条件时才考虑独立 worktree / branch：

- owner files 不重叠。
- verification 可以独立运行。
- integrator 有明确合并顺序。
- 用户或项目规则允许创建额外工作区。

不默认创建 worktree；当前 workspace 能安全串行完成时，优先保持简单。
