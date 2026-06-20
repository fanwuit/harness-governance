# Implementation Entry Record

## 1. Goal / 目标

定义平台中立的能力层级（strong/execution/mechanical），建立角色→必需层级策略，
通过 agent 目录自动发现（tiers.json）暴露模型候选，并在 REVIEW_NEXT 强制执行低层级不能自验证。

## 2. Scope / 范围

- CapabilityTier 枚举 + ROLE_CAPABILITY_POLICY 默认策略
- capability_routing.py 策略解析引擎
- agent_declarations.py agent 目录扫描器
- HarnessConfig 角色覆盖配置
- Orchestrator prompt 能力层级输出
- SkillInvocation 溯源字段扩展
- REVIEW_NEXT gate hook 强制执行

## 3. Owner Files

- `src/harness_governance/models/schemas.py`
- `src/harness_governance/state_machine/capability_routing.py`
- `src/harness_governance/state_machine/agent_declarations.py`
- `src/harness_governance/state_machine/skill_chain.py`
- `src/harness_governance/runner/orchestrator.py`
- `src/harness_governance/config/settings.py`

## 4. Verification Command

```bash
python -m pytest tests/test_state_machine/test_capability_routing.py tests/test_state_machine/test_agent_declarations.py tests/test_state_machine/test_skill_chain.py tests/test_subagent_runner/test_orchestrator.py -q
```

## 5. Readiness Check

| Check | Status |
|---|---|
| Contracts documented | ✅ docs/contracts/capability-tier-routing.md |
| ADRs documented | ✅ docs/adr/agent-directory-declarations.md, capability-tier-gate-enforcement.md |
| Architecture documented | ✅ docs/architecture/capability-tier-routing.md |
| Brief documented | ✅ docs/briefs/capability-tier-routing.md |
| Facts documented | ✅ docs/facts/capability-tier-routing.md |
| Unit tests from contract | ✅ 52+ tests passing |

## 6. Risks

- 无 agent tiers.json 声明的项目默认退回到 platform-generic
- 自定义角色不在 ROLE_CAPABILITY_POLICY 中默认 STRONG

## 7. Assumptions

- REVIEW_NEXT 层门控执行是足够的验证点
- Agent 目录 tiers.json 机制适配主流 agent 平台

## 8. Stop Conditions

- 任一契约行为测试失败
- REVIEW_NEXT 门控拒绝自验证但未记录原因

## 9. Authorization

Authorized by user at 2026-06-20. Proceed to implementation.
