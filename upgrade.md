# Harness-Governance 升级建议

> 对比 Trellis + OpenSpec + Superpowers + GStack 四件套，整理值得借鉴的设计点，按优先级排序。

---

## 优先级 P0：立即值得借鉴

### 1. 红旗清单 + 拒绝理由提示（已完成）

**来源**：Superpowers

**现状问题**：
- gate check 失败时，agent 只收到 "exit code != 0"，不知道具体原因
- agent 会尝试找借口绕过规则，如 "这只是小改动"、"测试太难写"

**Superpowers 的设计**：
每个 skill 开头写明不可协商规则，后面跟"红旗清单"——列出 AI 最可能用来绕过的借口：

```markdown
# 规则：必须先写测试
TDD is not optional. No implementation before tests.

# 红旗清单（AI 可能找的借口）
## RED FLAGS - AI EXCUSES WE DON'T ACCEPT:
- "The test is too hard to write first"
- "This is just a quick fix"
- "I'll write tests later"
- "The existing tests cover this"
```

**建议改进**：
在 gate 失败消息中增加红旗清单：

```bash
$ harness layer advance LAYER_5_TEST
✗ Gate check failed: tests not passing

This is a common excuse we don't accept:
- "It's just a small change, tests aren't needed"
- "I'll add tests later"
- "The existing tests cover this"

Required actions:
1. Run: your-test-command --coverage
2. Ensure coverage >= 80%
3. Re-run: harness gate check LAYER_5_TEST
```

**实现位置**：
- `src/harness_governance/messages.py` — 已增加 gate failure guidance / red flag 消息
- `src/harness_governance/commands/gate_failure.py` — 已增加共享失败提示格式化
- `src/harness_governance/commands/gate.py` — `harness gate check` 失败时输出缺失要求、红旗清单和下一步动作
- `src/harness_governance/commands/layer.py` — `harness layer advance` 被 gate 阻止时输出同样提示
- `tests/test_commands/test_gate_cmd.py`、`tests/test_commands/test_layer_cmd.py` — 已覆盖非 JSON 提示和 JSON 输出兼容性

**完成状态**：
P0 已实现。状态机 gate 判定逻辑未改变；改动集中在 CLI 输出层，避免把展示文案耦合进 `state_machine/gates.py`。

---

## 优先级 P1：近期值得借鉴

### 2. Slash 命令 Alias 层

**来源**：GStack

**现状问题**：
- harness 命令偏向"系统管理"，需要理解 layer、gate、entry 等概念
- 用户上手门槛高，不如 `/office-hours`、`/qa`、`/ship` 直观

**GStack 的设计**：
```
/office-hours    ← 直接说需求，CEO 角色验证方向
/qa              ← 打开浏览器测试
/review          ← 深度代码审查
/ship            ← 发布
```

**建议改进**：
增加直观的 alias 层：

```bash
# 当前（需要理解概念）
harness governed-start "登录功能有bug"
harness layer advance LAYER_4
harness gate check LAYER_4

# 借鉴 GStack 的直观方式
/harness start "登录功能有bug"   # 自动判断类型，触发 governed-start
/harness plan                    # 查看当前状态 + 下一步建议
/harness review                  # 进入 REVIEW 层，触发审查流程
/harness ship                    # 进入交付流程，检查所有 gate
```

**实现位置**：
- `src/harness_governance/cli.py` — 增加 alias 命令组
- `src/harness_governance/data/skills/` — skill 文件中增加 alias 触发说明

---

### 3. 完整场景示例（文档已完成，命令暂缓）

**来源**：GStack

**现状问题**：
- 文档以命令参考为主，缺少"完整场景 + 实际输出"的示范
- 用户不知道"从需求到交付"的完整流程是什么样的

**GStack 的设计**：
文档中有一个非常具体的例子：

```bash
你: 我想构建一个每日简报应用。
你: /office-hours
Claude: [询问痛点 — 具体例子，而非假设]
你: 多个 Google 日历，事件信息过时，地点错误...
Claude: 我要挑战你的框架...
你: /plan-eng-review
Claude: [ASCII图表展示数据流]
你: 批准计划。退出计划模式。
Claude: [写入2,400行代码，跨11个文件。约8分钟]
你: /review
Claude: [自动修复2个问题。标记1个竞态条件]
你: /qa https://staging.myapp.com
Claude: [打开真实浏览器，点击流程，发现并修复Bug]
你: /ship
```

**建议改进**：
增加示例命令和文档：

```bash
# 新增示例命令
harness example full-stack    # 完整场景：需求 → 设计 → 实现 → 验证 → 交付
harness example bug-fix        # 场景：bug修复 + TDD
harness example refactor      # 场景：架构重构
```

每个示例包含：
1. 完整的命令序列
2. 预期的 AI 响应
3. gate check 的实际输出
4. 最终的交付物

**实现位置**：
- `QUICKSTART.md` — 已增加 "Walkthrough: bug fix with a gate" 章节
- `src/harness_governance/commands/governed_start.py` — 已在 governed 输出中展示 layer path、next layer 和状态检查命令
- `tests/test_commands/test_governed_start.py` — 已覆盖文本和 JSON 中的 layer path / next layer 输出

**完成状态**：
文档 walkthrough 已完成。`harness example ...` 命令暂缓；当前收益主要来自 QUICKSTART 的真实流程示例，不急于增加新的命令组。

---

## 优先级 P2：中期值得借鉴

### 4. 轻量规格模式

**来源**：OpenSpec

**现状问题**：
- change packet 需要 5 个独立文件（proposal + contracts + design + tasks + verification）
- 对简单任务可能过重，用户不愿意创建完整 packet

**OpenSpec 的设计**：
规格文档约 250 行，单文件包含核心要素：

```markdown
# Spec: 登录功能

## 接口
POST /api/login
- Body: { email, password }
- Returns: { token, user }

## 数据模型
User { id, email, password_hash }

## 边界条件
- 邮箱不存在 → 400
- 密码错误 → 401
- 账户锁定 → 423

## 异常处理
- 5次失败 → 锁定账户 15分钟
```

**建议改进**：
增加轻量规格模式：

```bash
# 当前（完整流程）
harness packet init CP-001
# 需要创建 5 个文件

# 借鉴 OpenSpec 的轻量模式
harness spec quick "登录功能"
# 生成单个 .harness/specs/login.md 文件
```

**实现位置**：
- `src/harness_governance/commands/spec.py` — 新增 spec 命令组
- `src/harness_governance/data/templates/spec-quick.md` — 轻量规格模板

---

### 5. 渐进式安装

**来源**：Superpowers

**现状问题**：
- `harness init` 一次性生成 4 个 tier + config + AGENTS.md
- 对只想试用的用户来说"太重了"

**Superpowers 的设计**：
- 可以只用 `/review` 做代码审查
- 可以只加 Test 补测试用例
- 渐进式引入，团队接受度高

**建议改进**：
提供渐进式安装选项：

```bash
# 当前（全部安装）
harness init

# 借鉴 Superpowers 的渐进式
harness init --tier light           # 只安装轻量级 skill
harness init --modules gate,layer  # 只安装门控和层管理
harness init --full                # 完整安装（默认）
```

**实现位置**：
- `src/harness_governance/commands/init.py` — 增加 --tier 和 --modules 参数

---

## 优先级 P3：长期值得借鉴

### 6. Skill 组合灵活性

**来源**：Superpowers

**现状问题**：
- harness 更像系统工具，skill 是预设的 4 个 tier
- 不支持用户自定义 skill 组合

**Superpowers 的设计**：
- 20+ 可组合 Skills
- 可以按需组合，不需要用全套

**建议改进**：
长期可以考虑 skill 市场模式，但当前不是核心问题。harness 的定位是"程序化门控系统"，skill 组合灵活性是方法论层面的问题。

---

### 7. 快速上手引导（已完成）

**来源**：四件套整体

**现状问题**：
- 安装简单，但"安装后做什么"缺少引导

**四件套的设计**：
```bash
# 第一步:安装三大框架
/install openspec
/install superpowers
/install gstack

# 后续步骤直接引导
```

**建议改进**：
`harness init` 后增加交互式引导：

```bash
$ harness init
✓ Created: .harness/config.toml
✓ Created: 4 skill files
✓ Created: AGENTS.md

📋 Quick start guide:
1. Describe your task: harness governed-start "your task here"
2. View current state: harness status
3. Try an example: harness example bug-fix

Need help? Run: harness guide quickstart
```

**实现位置**：
- `src/harness_governance/commands/init.py` — init 成功后已输出 quick start guide
- `src/harness_governance/messages.py` — 已增加 init quickstart 消息
- `QUICKSTART.md` — 已同步 init 输出示例
- `tests/test_commands/test_init.py` — 已覆盖 init 输出中的下一步引导

**完成状态**：
已实现。`harness init` 成功后会提示 `harness governed-start`、`harness status`、`harness layer guide` 和 QUICKSTART.md。

---

## 实现优先级总结

| 优先级 | 借鉴点 | 来源 | 实现成本 | 预期收益 |
|---|---|---|---|---|
| **P0** | 红旗清单 + 拒绝理由提示 | Superpowers | 低 | 高 — 直接提升 agent 遵循率 |
| **P1** | Slash 命令 Alias 层 | GStack | 中 | 高 — 降低学习门槛 |
| **P1** | 完整场景示例 | GStack | 中 | 已完成（文档） |
| **P2** | 轻量规格模式 | OpenSpec | 中 | 中 — 简单任务不需要 5 个文件 |
| **P2** | 渐进式安装 | Superpowers | 低 | 中 — 降低试用门槛 |
| **P3** | Skill 组合灵活性 | Superpowers | 高 | 低 — 适合 skill 市场模式 |
| **P3** | 快速上手引导 | 四件套 | 低 | 已完成 |

---

## 下一步行动

1. **P1 规划**：设计 alias 命令层，优先考虑普通 CLI alias（如 `harness start`），slash 形式先放在平台 skill 文档中
2. **P2 设计**：定义 `spec quick` 与完整 change packet 的升级边界
3. **P2 评估**：在已有 `--minimal` 基础上决定是否增加 `harness init --tier light`

---

*文档创建时间：2026-06-17*
*对比对象：Trellis + OpenSpec + Superpowers + GStack*
