# Web Frontend Target Gate / Web 前端目标关卡

For Web/frontend targets, such as `<frontend-app>`, `<web-client>`, or the project's own frontend target paths.

用于 Web/frontend 目标，例如 `<frontend-app>`、`<web-client>` 或项目自己的前端 target 路径。

## Required Baseline / 必需基线

- Local `AGENTS.md`. / 本地 `AGENTS.md`。
- Package manager and build command. / package manager 和 build command。
- Lint and formatter command. / lint 和 formatter command。
- Unit/component test command. / unit/component test command。
- Browser/build/integration check targeting user-visible behavior or rendering behavior. / 面向用户可见行为或渲染行为的 browser/build/integration check。
- Protocol boundary: the frontend only consumes public contracts. / protocol boundary：frontend 只消费 public contracts。

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

- Unit/component framework:
- Unit command:
- Browser/build/integration command:

## Verification

```powershell
<command>
```

## Forbidden Shortcuts

- 不要调用 backend-private、worker-private 或 storage-internal APIs。
- 不要把 protocol conversion 混入大型 UI components。
- 不要只用 screenshots 验证 structured behavior。
````
