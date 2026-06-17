# Worker Runtime Target Gate / Worker 运行时目标关卡

For runtime, worker, external process, CLI, plugin, or host integration targets.

用于 runtime、worker、external process、CLI、plugin 或 host integration 目标。

## Required Baseline / 必需基线

- Local `AGENTS.md`. / 本地 `AGENTS.md`。
- Runtime/deployment boundary. / runtime/deployment boundary。
- Process, timeout, cancellation, retry, and crash ownership. / process、timeout、cancellation、retry 和 crash ownership。
- Lint/analyzer/formatter command when available. / 可用时提供 lint/analyzer/formatter command。
- Unit test command. / unit test command。
- Contract/integration harness targeting external inputs/outputs. / 面向 external inputs/outputs 的 contract/integration harness。
- Redaction/public-safety rules for logs, paths, storage references, and raw runtime output. / 针对 logs、paths、storage references 和 raw runtime output 的 redaction/public-safety rules。

## Local Rule Skeleton / 本地规则骨架

````markdown
# <target>/AGENTS.md

## Architecture Boundary

- Owns:
- Does not own:

## Runtime Boundary

- Process model:
- External dependencies:
- Timeout/cancellation:
- Crash/retry:

## Lint And Format Baseline

- Tool:
- Command:

## Test Baseline

- Unit framework:
- Unit command:
- Contract/integration harness:

## Verification

```powershell
<command>
```

## Forbidden Shortcuts

- 不要把 harness/probe behavior 提升为 production runtime。
- 不要公开 local paths、raw logs、raw external output 或 secrets。
- 不要在 runtime gate 允许前新增 process supervision 或 executable lifecycle code。
````
