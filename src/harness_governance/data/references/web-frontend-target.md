# Web Frontend Target Gate

用于 Web/frontend 目标，例如 `<frontend-app>`、`<web-client>` 或项目自己的前端 target 路径。

## 必需基线

- 本地 `AGENTS.md`。
- package manager 和 build command。
- lint 和 formatter command。
- unit/component test command。
- 面向用户可见行为或渲染行为的 browser/build/integration check。
- protocol boundary：frontend 只消费 public contracts。

## 本地规则骨架

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
