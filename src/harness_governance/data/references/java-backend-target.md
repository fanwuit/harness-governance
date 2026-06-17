# Java Backend Target Gate / Java 后端目标关卡

For Java backend targets, such as `<backend-app>`, `<api-service>`, or the project's own backend target paths.

用于 Java 后端目标，例如 `<backend-app>`、`<api-service>` 或项目自己的后端 target 路径。

## Required Baseline / 必需基线

- Local `AGENTS.md`. / 本地 `AGENTS.md`。
- Build tool and Java version. / build tool 和 Java version。
- Formatting/lint command, e.g. Spotless and Checkstyle. / formatting/lint command，例如 Spotless 和 Checkstyle。
- Unit test command, typically Maven- or Gradle-driven JUnit. / unit test command，通常是 Maven 或 Gradle 驱动的 JUnit。
- Contract/integration checks targeting public API, adapter, worker, or storage boundaries. / 面向 public API、adapter、worker 或 storage boundary 的 contract/integration check。
- Explicit forbidden scope for HTTP, DB, auth, storage, queues, or background workers until explicitly allowed. / 在明确允许前，对 HTTP、DB、auth、storage、queues 或 background workers 写出 explicit forbidden scope。

## Local Rule Skeleton / 本地规则骨架

````markdown
# <target>/AGENTS.md

## Architecture Boundary

- Owns:
- Does not own:

## Lint And Format Baseline

- Tool:
- Command:

## Test Baseline

- Unit framework:
- Unit command:
- Contract/integration command:

## Verification

```powershell
<command>
```

## Forbidden Shortcuts

- 不要在 controller gate 前新增 controllers。
- 不要在 persistence gate 前新增 persistence。
- 不要在 public DTO 中泄漏 private worker/storage/runtime details。
````
