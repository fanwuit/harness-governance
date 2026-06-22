# Brief: P0 Capability-Tiered Subagent Routing

## Goal / 目标

定义平台中立的能力层级（strong/execution/mechanical），建立角色→必需层级策略，
通过 agent 目录自动发现（tiers.json）暴露模型候选，并在 REVIEW_NEXT 强制执行低层级不能自验证。

## Non-Goals / 非目标

- 不实现适配器实际调度执行（adapter dispatch）
- 不添加前端 CLI 命令（如 harness check capability-tiers）
- native handoff records are the execution boundary; no process executor API is part of core
- 不编码平台特定模型排名到 harness 核心

## Options Considered / 已考虑的选项

- Option A: Documentation + 继续推进治理流程（已选）
- Option B: 新增 CLI 命令 + 集成（推迟）

## Decision / Direction / 决策方向

Option A: 先写 adoption 文档，再继续推进后续治理层。

## Risks / Unknowns / 风险与未知

- 无 agent tiers.json 声明的项目默认退回到 platform-generic 行为
- 自定义角色不在 ROLE_CAPABILITY_POLICY 中默认 STRONG，可能过于严格

## Success Criteria / 成功标准

1. tiers.json 格式已文档化，agent 开发者可按格式声明模型候选
2. harness core 能从 agent 目录正确发现 declarations
3. 测试覆盖 declaration 发现、解析、优先级逻辑
4. 已有 gate hook 在 REVIEW_NEXT 层正确拦截自验证

## Next Layer / 下一层

Architecture — 确认整体架构设计，包括 agent declarations 与 capability_routing 的集成关系。
