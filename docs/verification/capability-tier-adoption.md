# Capability-Tier Subagent Routing: Agent Adoption Guide

## User-Perceived Integration Not Applicable

This is a developer reference document — it describes how to configure `tiers.json`,
not a user-facing feature. No screenshots, traces, or user interaction recording
apply.

- Reason: Developer documentation only, no user-visible behavior change
- Replacement verification: All contract tests pass
- Residual risk: None

---

## Overview

每个 agent 平台可以在其配置目录下放置 `tiers.json` 文件，声明该平台能为每个角色提供什么能力层级和模型。

Harness core 在运行时自动发现这些声明，从不硬编码模型排名。

## Quick Start

在 agent 配置目录创建 `tiers.json`：

```json
{
  "platform": "opencode",
  "adapters": [
    {
      "role": "implementer",
      "required_tier": "execution",
      "adapter": "subagent",
      "model_label": "deepseek-v4-flash"
    },
    {
      "role": "verifier",
      "required_tier": "strong",
      "adapter": "subagent",
      "model_label": "deepseek-v4-flash"
    }
  ]
}
```

## Well-Known Paths

| Agent Platform | Config Directory | tiers.json Location |
|---|---|---|
| Claude Code | `.claude/` | `.claude/tiers.json` |
| Codex / Multi | `.agents/` | `.agents/tiers.json` |
| Cline | `.clinerules/` | `.clinerules/tiers.json` |
| Cursor | `.cursor/` | `.cursor/tiers.json` |
| OpenCode | `.opencode/` | `.opencode/tiers.json` |
| Windsurf | `.windsurf/` | `.windsurf/tiers.json` |
| Generic | project root | `tiers.json` |

## Capability Tiers

| Tier | Description | Self-Verify |
|---|---|---|
| `strong` | 全能力：规划、写契约、实施、验证、关闭 | ✅ 可以 |
| `execution` | 执行型：根据清晰 spec 实现 | ❌ 不能，需 independent strong verifier |
| `mechanical` | 机械型：文档更新、格式化、lint | ❌ 不能，需 independent strong verifier |

## Role Policy (Default)

| Role | Required Tier | Verifier Needed |
|---|---|---|
| planner | strong | No |
| contract-writer | strong | No |
| adr-writer | strong | No |
| fact-finder-reviewer | strong | No |
| readiness-gate-writer | strong | No |
| reviewer | strong | No |
| verifier | strong | No |
| integrator | strong | No |
| orchestrator | strong | No |
| implementer | execution | Yes |
| document-gardener | mechanical | Yes |

可在 `.harness/config.toml` 中覆盖单个角色的必需层级：

```toml
role_capability_overrides = [
  { role = "implementer", required_tier = "strong" },
]
```
