# Shared Package Target Gate

用于会被多个 app、service、runtime 或 tool 消费的共享包。例如：`<contract-package>`、`<shared-types-package>`、`<api-client-package>`、`<test-fixtures-package>`，或项目自己的 shared package 路径。

## 范围模板

````markdown
# <package>/AGENTS.md

Applies to `<package>/**`.

## Scope

This package is shared by:

- <consumer 1>
- <consumer 2>

## Boundary

- 可以定义 schemas、DTOs、types、fixtures、helpers 或 checks。
- 除非 package 明确是 runtime-scoped，否则不要依赖 app runtime。
- 除非 I/O 是 package 的明确目的，否则不要执行 I/O。
- 不要暴露 secrets、local paths、storage internals、raw worker/exporter output 或 harness-only details。

## Version And Compatibility

- Breaking schema/API changes 需要 version bump 或 migration note。
- shared contract 变化时必须列出 consumers。
- contract 变化时必须更新 positive 和 negative examples。

## Lint / Format

- Tool:
- Command:
- Exclusions:

## Unit Tests

- Framework:
- Command:
- Minimum example:

## Contract / Integration Tests

- Fixtures/examples:
- Compatibility checks:
- Consumer-facing verification:

## Verification

Standard command:

```powershell
<command>
```

## Forbidden Shortcuts

- 不要把 app-only frameworks import 到 shared package。
- 不要把 app-specific behavior 藏进 generic helpers。
- 除非 package name 和 scope 明确说明，不要新增 environment-specific dependencies。
````

## Gate Questions

- 今天谁消费这个 package？
- 后续预计谁会消费它？
- 这个 package 是纯 contract/type/helper code，还是会执行 runtime behavior？
- schema/type 变化会破坏什么？
- 是否存在 positive examples 和 negative examples？
- 是否有 check 能在 consumer-visible contract 泄漏 private fields 时失败？

## Common Failure Cases

- shared package import 了 Spring、Vue、NXOpen、Windows-only APIs 或 browser globals，但没有明确 runtime scope。
- 名为 contract package 的包开始执行 network、filesystem 或 process work。
- schema 变化时没有同步 examples 和 consumer checks。
- fixture package 包含 production secrets 或 customer/private artifacts。
