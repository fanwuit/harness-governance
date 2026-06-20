# Brainstorming: Capability-Tier Routing Next Steps

## Option A: Documentation + Layer Progression
- **Best when:** 核心实现已就绪，需要稳定化和推进
- **Benefit:** 既产生 adoption 文档指导用户使用，又按流程推进确保完整
- **Cost:** 中等 — 写文档 + 继续推进治理层
- **Risk:** 低 — 文档和流程推进不涉及代码风险
- **Evidence needed:** 用户已确认此方向

## Option B: CLI Commands + Integration
- **Best when:** 需要给用户提供可交互的发现/诊断能力
- **Benefit:** 增加 `harness check capability-tiers` 等命令
- **Cost:** 高 — 需要设计并实现新 CLI 命令
- **Risk:** 中 — CLI 交互设计可能需多次迭代
- **Evidence needed:** 用户未选此方向

## Non-Goals
- 适配器实际调度执行（adapter dispatch）不在当前 P0 范围
- 不添加平台特定的模型排名到 harness 核心
- 不改动现有 `AgentExecutor` 接口

## Selected Direction
Option A: Documentation + continue advancing governance layers.
