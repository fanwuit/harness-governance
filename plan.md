# harness-governance: Python CLI + Skill 架构规划

## Context

将 E:\my-skills 的 Codex skills 治理框架改造为纯 Python CLI 工具，
任何能执行 shell 命令的 AI agent（Claude、GPT、Gemini、Codex、Cursor、Cline……）
加载一个 skill 文件后即可使用这套 AI 工程治理方法论。

**核心不变**: 12 层状态机 + 9 条流转规则 + Markdown 文件约定。
**核心变化**: Codex skill 加载 → CLI 命令 + 各平台 skill 适配文件；多语言 → 纯 Python。

## 为什么不是 MCP

MCP 有价值（类型安全、工具发现），但强制用户写 JSON 配置才能用，
违背"零配置上手"的目标。CLI 命令是任何 Agent 的通用接口。
如果未来有需求，加一个 MCP server 入口只需一行注册，核心代码不动。

## 目标架构

```
pip install harness-governance
cd my-project
harness init                     # 一步：创建 .harness/ + 写入 skill 文件

Agent 加载 skill 文件后:
  harness governed-start "做 X"
  harness packet init <name>
  harness check --all
  harness status
  ...
```

```
任意 Agent (有 shell 能力)
       │
       ▼
  skill 文件 (告诉 Agent 何时/如何调 CLI)
       │
       ▼
  harness CLI (Python)
       │
  ┌────┼────┬──────────┬──────────┐
  │    │    │          │          │
  ▼    ▼    ▼          ▼          ▼
start packet plan  verify  check  status
       │    │          │          │
       ▼    ▼          ▼          ▼
  StateMachine  FileOps  Runner  Config
```

## 目录结构

```
harness-governance/
├── pyproject.toml
├── README.md
├── LICENSE
├── src/harness_governance/
│   ├── __init__.py
│   ├── cli.py                  # CLI 主入口 (click 或 argparse)
│   │
│   ├── state_machine/
│   │   ├── layers.py           # HarnessLayer enum + LAYER_MAP (12 层)
│   │   ├── transitions.py      # 9 条流转规则
│   │   ├── engine.py           # StateMachineEngine
│   │   └── classification.py   # Fast/Trivial/Governed 三分法
│   │
│   ├── models/
│   │   └── schemas.py          # 所有 Pydantic 模型
│   │
│   ├── commands/               # 每个子命令的实现
│   │   ├── start.py            # harness governed-start
│   │   ├── packet.py           # harness packet {init,check}
│   │   ├── entry.py            # harness entry {check,record}
│   │   ├── plan.py             # harness plan {init,attest,complete}
│   │   ├── check.py            # harness check {routing,packets,entry,inventory,all}
│   │   ├── status.py           # harness status
│   │   ├── verify.py           # harness verify <preset>
│   │   ├── review.py           # harness review close
│   │   └── config.py           # harness config init
│   │
│   ├── runner/                 # 自主 runner (Python 原生)
│   │   ├── base.py             # AgentExecutor 抽象
│   │   ├── loop.py             # AutonomousReadyLoop
│   │   ├── checkpoint.py       # checkpoint 读写
│   │   └── adapters/
│   │       ├── generic.py      # 通用 subprocess
│   │       └── codex_cli.py    # Codex CLI
│   │
│   ├── config/
│   │   ├── settings.py         # HarnessConfig (Pydantic)
│   │   └── defaults.py         # 默认路径常量
│   │
│   ├── file_ops/               # Markdown 文件读写
│   │   ├── queue.py            # NEXT.md
│   │   ├── packet.py           # docs/changes/{id}/
│   │   ├── plan.py             # .planning/{id}/
│   │   ├── checkpoint.py       # .harness/run-checkpoint.md
│   │   └── entry.py            # entry records
│   │
│   ├── plugins/
│   │   ├── base.py
│   │   └── session_catchup.py  # 可选
│   │
│   └── data/                   # 打包的非代码资源
│       ├── templates/          # 8 个模板
│       ├── references/         # 18 个参考文档
│       └── fixtures/           # 测试 fixtures
│
├── skills/                     # 各平台的 agent 适配层
│   ├── claude-code/
│   │   └── SKILL.md            # Claude Code: 何时调 harness
│   ├── codex/
│   │   └── SKILL.md            # Codex skill
│   ├── cline/
│   │   └── prompt.md           # Cline rules
│   └── generic/
│       └── AGENTS.md           # 通用 agent instructions
│
└── tests/
    ├── conftest.py             # 共享 fixture: 临时 repo
    ├── test_state_machine/
    ├── test_commands/
    ├── test_runner/
    └── test_file_ops/
```

## CLI 命令树

```
harness init                        # 零配置初始化：创建 .harness/ + 写入当前平台的 skill
harness init --claude               # 指定平台（覆盖自动检测）

harness governed-start "<描述>"     # 入口路由：三分法分类
    [--files a.py,b.py]             # 拟改动的文件（可选）
    [--contracts]                   # 是否涉及公开契约
    [--external]                    # 是否有外部副作用

harness packet init <change-id>     # 创建变更包
    [--force]

harness packet check [paths...]     # 校验变更包

harness entry check [files...]      # 校验入口记录

harness entry record                # 写入入口记录
    [--type implementation|trivial]
    [--target ...] [--scope ...] ...

harness plan init [name]            # 创建规划会话
    [--template default|analytics]

harness plan attest [plan-id]       # SHA-256 锁定规划
harness plan show [plan-id]         # 显示锁定 hash
harness plan clear [plan-id]        # 清除锁定
harness plan complete [plan-id]     # 检查阶段完成状态

harness check routing               # 路由护栏检查
harness check packets               # 变更包检查
harness check entry                 # 入口记录检查
harness check inventory             # README 清单同步检查
harness check --all                 # 全部检查

harness status                      # 状态视图（Markdown）
harness status --json               # 状态视图（JSON）
harness status --refresh            # 刷新并写入 .harness/

harness verify <preset>             # 执行验证 preset

harness review close <task-id>      # 关闭任务
    [--evidence ...] [--risks ...]

harness config init                 # 初始化 .harness/config.toml
    [--force]

harness runner start                # 启动自主 runner
    [--mode bounded|boundary]
    [--max-rounds N]
    [--verification <preset>]
```

## 零配置体验

```bash
$ pip install harness-governance
$ cd my-project

$ harness init
Detected: Claude Code
Created: .harness/config.toml
Created: .claude/skills/harness-governance/SKILL.md
Done. Your agent will now use harness governance for engineering work.
```

`harness init` 做了两件事：
1. 创建 `.harness/config.toml`（项目级配置，默认值即可工作）
2. 写入一份 skill 文件到当前平台的约定路径

skill 文件内容（以 Claude Code 为例）：

```markdown
# Harness Governance

你是本项目的 AI 工程治理助手。
非简单问答或小修改时，使用 harness CLI 按以下流程工作：

## 入口
开始任何开发任务前，先了解任务范围：
  harness governed-start "<任务描述>"

## 变更包（跨层/跨会话工作）
创建: harness packet init <change-id>
校验: harness packet check

## 实现入口（写代码前）
校验: harness entry check
记录: harness entry record --type implementation ...

## 规划
创建: harness plan init <名称>
锁定: harness plan attest
检查: harness plan complete

## 检查
提交前: harness check --all
状态: harness status

## 验证
harness verify routing-guardrails
harness verify all-local-checks

## 关闭
harness review close <task-id> --evidence "..."

运行 `harness --help` 查看完整命令。
```

## 关键技术决策

1. **CLI 框架**: `click` — Python 最广泛的 CLI 库，`--help` 自动生成
2. **数据模型**: Pydantic v2 — 所有命令 I/O 用 BaseModel，`--json` 时自动序列化
3. **配置**: `.harness/config.toml` — 项目级，无默认值即可工作
4. **模板/参考文档**: `importlib.resources` 打包 — pip install 后自包含
5. **Agent 执行器**: `AgentExecutor` 抽象 — 默认 subprocess，Codex/Claude 各适配
6. **Python 版本**: >= 3.10
7. **测试**: pytest + conftest.py 共享临时 repo fixture
8. **包名**: `harness-governance` (pip) / `harness_governance` (Python)

## 保留 vs 丢弃

**保留**（打包到 data/ 或编码到 Python）:
- 全部 18 个参考文档（→ data/references/）
- 全部 8 个模板（→ data/templates/）
- 全部测试 fixtures（→ data/fixtures/）
- 12 层方法论 + 9 条流转规则（→ state_machine/）
- Markdown 文件约定（NEXT.md, docs/changes/, .planning/）

**丢弃**:
- 25 个 SKILL.md → 1 个 CLI + 每平台 1 个薄 skill 文件
- 25 个 agents/openai.yaml → 不再需要，skill 文件内置说明
- 9 个 .sh / 9 个 .ps1 → Python 单实现
- 7 个 .mjs → Python
- package.json → pyproject.toml
- Harness Precondition 章节 → governed-start 命令程序化执行
- Codex 特定路径耦合 → .harness/config.toml 可配置

## 实施阶段

### Phase A: Core（2 周）
- pyproject.toml + 包骨架（src 布局）
- `cli.py`（click 主入口，所有子命令注册）
- `state_machine/`（layers + transitions + engine + classification）
- `models/schemas.py`（全部 Pydantic 模型）
- `config/`（settings + defaults）
- `file_ops/`（queue + packet + plan + checkpoint + entry）
- 3 个子命令: `harness init`, `harness governed-start`, `harness packet {init,check}`
- `data/`（全部模板 + 参考文档 + fixtures）
- tests/conftest.py + 核心测试
- `harness --help` 输出完整命令树

### Phase B: Full（2 周）
- 剩余子命令: entry, plan, check, status, verify, review, config, runner
- `runner/`（base + loop + checkpoint + adapters/generic）
- `plugins/session_catchup.py`
- `skills/`（claude-code + codex + cline + generic）
- 85% 测试覆盖

### Phase C: Polish（1 周）
- 与现有 .mjs 脚本行为 parity 测试
- 大仓库性能（缓存、懒加载）
- 错误消息中英双语
- README + 5 分钟入门指南
- PyPI 发布
- `harness init` 自动检测 Agent 平台

## 验证策略

1. `pytest` 全部测试通过
2. 临时 repo fixture 端到端：`harness init` → `harness governed-start` → `harness packet init` → `harness check --all` → `harness status`
3. 状态机流转规则：每种违规都被拦住
4. 三分法分类：Fast/Trivial/Governed 边界案例
5. 与现有 .mjs 脚本行为 parity（同输入 → 同输出）
6. 实际 Claude Code + skill 文件加载 → Agent 正确调用 CLI
