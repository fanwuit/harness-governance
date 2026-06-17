# Shared Package Target Gate / 共享包目标关卡

For shared packages consumed by multiple apps, services, runtimes, or tools. For example: `<contract-package>`, `<shared-types-package>`, `<api-client-package>`, `<test-fixtures-package>`, or the project's own shared package paths.

用于会被多个 app、service、runtime 或 tool 消费的共享包。例如：`<contract-package>`、`<shared-types-package>`、`<api-client-package>`、`<test-fixtures-package>`，或项目自己的 shared package 路径。

## Scope Template / 范围模板

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

## Gate Questions / 关卡问题

- Who consumes this package today? / 今天谁消费这个 package？
- Who is expected to consume it in the future? / 后续预计谁会消费它？
- Is this package pure contract/type/helper code, or does it execute runtime behavior? / 这个 package 是纯 contract/type/helper code，还是会执行 runtime behavior？
- What would a schema/type change break? / schema/type 变化会破坏什么？
- Do positive examples and negative examples exist? / 是否存在 positive examples 和 negative examples？
- Is there a check that fails when consumer-visible contracts leak private fields? / 是否有 check 能在 consumer-visible contract 泄漏 private fields 时失败？

## Common Failure Cases / 常见失败场景

- Shared package imports Spring, Vue, NXOpen, Windows-only APIs, or browser globals without an explicit runtime scope. / shared package import 了 Spring、Vue、NXOpen、Windows-only APIs 或 browser globals，但没有明确 runtime scope。
- A package named as a contract package starts performing network, filesystem, or process work. / 名为 contract package 的包开始执行 network、filesystem 或 process work。
- Schema changes are not synchronized with examples and consumer checks. / schema 变化时没有同步 examples 和 consumer checks。
- Fixture package contains production secrets or customer/private artifacts. / fixture package 包含 production secrets 或 customer/private artifacts。
