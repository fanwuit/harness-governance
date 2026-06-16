# harness-governance / 治理 CLI

[![Python](https://img.shields.io/badge/python-≥3.10-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](./LICENSE)
[![Version](https://img.shields.io/badge/version-0.7.1-blue)](./CHANGELOG.md)

AI engineering governance CLI. Encodes a 12-layer state machine, 5-layer defense system, and programmable gate enforcement. Any agent with shell access can load a per-platform skill adapter and gain access to the same governance commands.

AI 工程治理 CLI。内置 12 层状态机、五层防御体系、程序化门控引擎。任何有 shell 权限的 agent 都能加载平台适配 skill 并使用统一的治理命令。

---

## Why this exists / 为什么需要

The legacy Codex skill set exposed 25 separate `SKILL.md` files plus 20 shell/Node scripts. `harness-governance` consolidates that into one `harness` command, then adds **hard enforcement** — 5 layers of defense that prevent agents from skipping governance steps.

旧版 Codex skill 体系需要 25 个 `SKILL.md` + 20 个 shell/Node 脚本。本项目合并为单个 `harness` 命令，并增加了**硬性强制执行**——五层防御防止 agent 跳过治理步骤。

### 5-Layer Defense / 五层防御

```
第 0 层 / Layer 0: 3-Skill 入口分流 (strict/standard/light × 8 platforms)
第 1 层 / Layer 1: RigorTier 自动检测 (86 个中英文关键词，默认 STRICT)
第 2 层 / Layer 2: LayerGateEngine (12 层程序化门控验证)
第 3 层 / Layer 3: Capability Lock Files (.harness/gates/ 磁盘级强制)
第 4 层 / Layer 4: Git Pre-commit Hook (代码入库最后防线)
```

## Quickstart / 快速开始

```bash
pip install harness-governance
mkdir my-project && cd my-project
harness init
```

Output / 输出：

```
Detected: Claude Code
Created: .harness/config.toml
Created: .claude/skills/harness-governance-strict/SKILL.md
Created: .claude/skills/harness-governance-standard/SKILL.md
Created: .claude/skills/harness-governance-light/SKILL.md
Note: AGENTS.md triggers: AGENTS.md
Done. Your agent will now use harness governance for engineering work.
```

See [`QUICKSTART.md`](./QUICKSTART.md) for 5-minute guided setup / 五分钟引导配置见 QUICKSTART.md。

## Commands / 命令总览 (v0.7.1)

```
harness init                        # 初始化项目 (3 个 skill + config + AGENTS.md)
harness governed-start "<desc>"     # 入口分类器 (--rigor light|standard|strict)
harness gate check <layer>          # 门控验证 (exit 0=通过)
harness gate status [layer]         # 查看锁文件状态
harness gate reset <layer>          # 重置锁 (需 --confirmed)
harness gate timing                 # 每层耗时分析 (v0.7.1)
harness layer advance <layer>       # 推进层 (强制先过 gate)
harness layer show                  # 当前层 + 转换历史
harness layer guide [layer]         # 作者交互指南
harness packet init <id>            # 创建 change packet
harness packet check [id]           # 验证 packet 结构
harness entry check                 # Entry Record 检查
harness plan init/attest/show       # 规划会话管理
harness check routing               # 路由护栏检查
harness check docs                  # 文档园丁检查 (v0.7.1)
harness check all                   # 全部检查
harness status                      # 仪表盘聚合输出
harness verify <preset>             # 运行验证预设
harness review close                # 关闭任务
harness runner start                # 自主就绪循环
harness session show/list           # 会话管理
```

## Architecture / 架构

```
src/harness_governance/
  cli.py                     ← click entry point, 14 command groups
  state_machine/
    layers.py                ← HarnessLayer enum (12 values)
    engine.py                ← StateMachineEngine, 9 transition rules (T1-T9)
    classification.py        ← 3-way classifier (Fast/Trivial/Governed)
    rigor.py                 ← RigorTier detection (LIGHT/STANDARD/STRICT)
    gates.py                 ← GATE_CATALOG, LayerGateEngine, LockFileManager
  commands/
    init.py                  ← 3-tier skill injection (24 files generated)
    gate.py                  ← gate check/status/reset/timing
    layer.py                 ← layer advance/show/guide (gate-enforced)
    check.py                 ← check routing/packets/entry/inventory/docs/all
  session/                   ← SessionState persistence (JSON)
  models/schemas.py          ← Pydantic v2 (20+ models)
  runner/                    ← autonomous loop + orchestrator + result parser
  data/
    skills/{strict,standard,light}/  ← 24 skill files (8 platforms × 3 tiers)
    role-prompts/             ← 10 subagent role templates
    references/               ← layer-author-guide, layer-progression, etc.
  messages.py                ← bilingual i18n (~170 message IDs)
```

## Supported platforms / 支持平台

| Platform | Skill path (standard tier) |
|----------|---------------------------|
| Claude Code | `.claude/skills/harness-governance-standard/SKILL.md` |
| Codex | `.agents/skills/harness-governance-standard/SKILL.md` |
| Cline | `.clinerules/harness-governance-standard.md` |
| Cursor | `.cursor/rules/harness-governance-standard.mdc` |
| OpenCode | `.opencode/agents/harness-governance-standard.md` |
| Windsurf | `.windsurf/skills/harness-governance-standard/SKILL.md` |
| QoderWork | `AGENTS.md` |
| Generic | `AGENTS.md` |

Each platform gets 3 tiers / 每个平台 3 个 tier: `strict`, `standard`, `light`.

## Development / 开发

```bash
pip install -e .
pytest tests/ -x --tb=short     # ~920 tests
harness check all                # governance self-check
```

Bilingual output / 双语输出: `set HARNESS_LANG=zh-CN` (Windows) or `export HARNESS_LANG=zh-CN` (Unix).

## License

MIT — see [LICENSE](./LICENSE).
