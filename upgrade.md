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

### 2. Slash 命令 Alias 层（CLI alias v1 已完成，slash 暂缓）

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
- `src/harness_governance/commands/aliases.py` — 已新增 `harness start`、`harness next`、`harness ship`
- `src/harness_governance/cli.py` — 已注册 alias 命令
- `tests/test_commands/test_aliases.py` — 已覆盖 alias 行为
- `README.md`、`QUICKSTART.md` — 已记录普通 CLI alias 用法

**完成状态**：
普通 CLI alias v1 已完成。`harness ship` 只做交付就绪检查，不发布、不部署、不 push、不打 tag。

**暂缓跟踪项**：
- `/harness start`、`/harness ship` 等 slash 形式：平台交互语法，不作为 Python CLI 命令实现；后续放入各平台 skill 文档。
- `harness plan` alias：已有 `harness plan` 命令组，暂不复用该名称避免冲突。
- `harness review` alias：已有 `harness review close`，如需扩展 review 语义需单独设计。

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

### 3A. State Contract Closure / 状态契约闭环（新增，P1）

**来源**：本项目 governed strict 链路事故复盘

**现状问题**：
- CLI 可以输出 `confirmed` / `recorded` / `passed`，但测试可能只覆盖输出或单个写入字段。
- gate/check 读取的是另一份状态 schema 时，单元测试仍可能全部通过，真实 strict/governed 链路却卡死。
- 派生项目如果只继承 harness 的流程提示，而没有集成测试和端到端测试约束，会复现同类“状态写入与消费不闭环”问题。

**建议改进**：
把“状态契约闭环”作为 harness 对自身和派生项目的 P1 治理约束：

```text
CLI 承诺状态已 confirmed/recorded
-> 持久化状态写入
-> 下游 check/gate 能读取并认可
-> 集成测试或 E2E 测试固定该链路
```

派生项目最低要求：
1. **集成测试**：每个治理状态 writer 必须证明对应 check/gate consumer 能消费它。
2. **端到端 smoke**：至少一条真实 governed-path 最小推进链路可走通。
3. **负例测试**：缺少该状态时，gate/check 仍必须阻止推进。

后续可新增 harness 能力：

```bash
harness state-contract check
```

该命令用于扫描/登记：
- 哪些 CLI 命令写入持久化治理状态。
- 哪些 gate/check 读取这些状态。
- 是否存在对应的 integration/e2e 回归测试。

配套 UX 能力：

```bash
harness layer ask intake-orientation
# 或
harness layer intake
```

该命令用于补齐 strict/governed-path 的真实使用体验：
- 自动读取当前 layer guide 的 Author Questions。
- 逐题提示用户回答，而不是只展示整段 guide。
- 将每个答案写入 session 的 `layer_qa`，等价于多次执行 `harness layer answer ...`。
- 回答完成后显示当前 gate 还缺什么，例如 tech-stack lint/docstyle 或其他 confirmation item。
- 不伪造 gate 通过；只提供正式状态写入入口和下一步提示。

**实现位置**：
- `upgrade.md`：记录为 P1 跟踪项。
- `tests/STATE_CONTRACTS.md`：已定义状态契约闭环测试约束。
- `tests/test_e2e/test_governed_path_smoke.py`：已新增最小 strict governed-path E2E smoke。
- `src/harness_governance/commands/state_contract.py`：已新增 `harness state-contract check` 第一版显式证据检查。
- `src/harness_governance/commands/layer.py`：已新增 `harness layer ask <layer>` 和 `harness layer intake`。
- `tests/test_commands/test_layer_cmd.py`、`tests/test_commands/test_state_contract_cmd.py`：已覆盖交互式问答和 state-contract check。
- 后续可在 `harness init` 中生成派生项目测试骨架。
- 后续可在 `verification` gate 或 `harness check` 中要求 state-contract 证据。

**完成状态**：
P1 第一版已实现。已具备正式问答入口、状态契约文档、最小 E2E smoke 和 `harness state-contract check`。剩余增强是派生项目模板生成、接入 verification gate / harness check，以及更自动化的 writer/consumer 扫描。

---

### 3B. Tag-only Release Verification Hook / 仅 tag 推送的发布前验证（新增，P1）

**来源**：GitHub CI #32 失败复盘

**范围声明**：
该能力第一版只针对 `harness-governance` 本仓库的 release hygiene。它固定使用本项目 Python 包的 CI/release 验证命令，不承诺作为派生项目的通用 release policy，也不要求派生项目必须有 CI。

**现状问题**：
- 普通 commit / push 阶段没有本地前置验证，格式问题会等到 GitHub CI 才暴露。
- 但如果对所有 commit 或普通 push 都强制全量验证，会显著增加日常开发摩擦。
- 项目真正需要更强约束的是 release/tag 前验证：tag 一旦推到远端，失败成本高于普通提交。
- Git 没有标准 `pre-tag` hook，不能直接在 `git tag` 前自动拦截。

**建议改进**：
实现“只拦 tag push，不拦普通提交/普通 push”的 release 验证能力。

第一阶段新增本地验证命令：

```bash
harness verify local --release
```

建议执行内容：
- `ruff format --check src/ tests/`
- `ruff check src/ tests/`
- `mypy src/`
- `pytest`
- `python -m build --wheel`
- wheel contents check

第二阶段新增 hook 安装命令：

```bash
harness hook install --tag-release
```

安装 `.git/hooks/pre-push`，hook 只检测 tag ref：

```sh
while read local_ref local_sha remote_ref remote_sha
do
  case "$local_ref" in
    refs/tags/*)
      harness verify local --release || exit 1
      ;;
  esac
done
```

预期行为：
- `git push origin main`：不触发 release 验证。
- `git push origin v0.8.2`：触发 `harness verify local --release`；失败则阻止 tag push。

后续可选封装：

```bash
harness release tag v0.8.2
```

该命令在创建 tag 前先跑 release 验证，再执行 `git tag`。它补足 Git 没有 `pre-tag` hook 的缺口，但第一版可以先做 tag-only `pre-push`。

**实现位置**：
- `src/harness_governance/commands/verify.py`：已新增 `harness verify local --release`。
- `src/harness_governance/commands/hook.py`：已新增 `harness hook install --tag-release`。
- `tests/test_commands/test_verify_review_config.py`、`tests/test_commands/test_hook_cmd.py`：已覆盖 release 验证和 tag-only hook 安装。
- 后续可在 `harness ship` 输出中提示 tag release 前安装/运行该验证。

**完成状态**：
P1 第一版已实现。普通 commit / 普通 push 不拦截；安装 tag-release hook 后，仅 `refs/tags/*` push 会触发 `harness verify local --release`。当前验证内容按本仓库 Python 包 release 流程固定。剩余增强是 `harness ship` 提示和可选 `harness release tag <version>` 封装。

---

### 3C. Agent Preflight Assessment / 代理侧预评估路由（新增，P1）

**来源**：本项目 dogfood 反馈

**现状问题**：
- 用户实际是在和 agent 对话，而不是直接和 `harness governed-start` 对话。
- 当前 agent 往往把用户原话直接传给 `harness governed-start`，导致 harness 只能靠关键词和规则猜测任务难度。
- 只靠关键词会不断增加触发词，仍然无法可靠表达上下文、文件范围、风险和 agent 已经理解到的任务意图。
- 例如“加入 upgrade.md 并排序优先级”这类任务，agent 已知道是文档跟踪项更新，但 harness 可能因为“文件修改/持久化状态”等关键词进入 governed-path。

**建议改进**：
在 `harness governed-start` 前增加 agent-side preflight：agent 先把自然语言请求理解为结构化 assessment，再交给 harness 做最终路由和审计。

目标链路：

```text
用户自然语言
-> agent 预评估任务类型、范围、风险、文件影响
-> harness governed-start 接收结构化 assessment
-> harness 输出最终 routing + rationale + disclosure
```

建议第一版支持两种输入：

```bash
harness governed-start "记录 tag-only hook 到 upgrade.md" \
  --files upgrade.md \
  --no-contracts \
  --no-external \
  --change-kind docs-tracking \
  --risk low \
  --recommended-route trivial-safe-change
```

或：

```bash
harness governed-start --assessment .harness/tmp/agent-assessment.json
```

assessment 示例：

```json
{
  "user_request": "先加入 upgrade.md，并排优先级",
  "agent_interpretation": "Update the tracking document only.",
  "intended_files": ["upgrade.md"],
  "operation": "documentation_update",
  "writes_files": true,
  "touches_public_contract": false,
  "has_external_side_effects": false,
  "scope_unclear": false,
  "risk": "low",
  "recommended_route": "trivial-safe-change",
  "recommended_rigor": "light",
  "change_kind": "docs-tracking"
}
```

路由原则：
- agent 负责上下文理解，不只传用户原话。
- harness 保留最终裁决权，可以接受、升级或拒绝 agent 的建议。
- disclosure 中显示 agent recommendation 与 harness final route 的差异。
- 关键词检测退为兜底，而不是主路径。

**实现位置**：
- `src/harness_governance/models/schemas.py`：已新增 `AgentAssessment` schema。
- `src/harness_governance/commands/governed_start.py`：已支持 `--assessment`、`--change-kind`、`--risk`、`--recommended-route` 等结构化输入。
- `src/harness_governance/state_machine/classification.py`：已把 assessment 作为主要路由信号，关键词作为 fallback。
- `tests/test_state_machine/test_classification.py` 和 `tests/test_commands/test_governed_start.py`：已覆盖 assessment 优先、冲突升级、JSON 输入。
- `src/harness_governance/commands/init.py` 和 `src/harness_governance/data/skills/*`：已同步 AGENTS/skill 入口规则，要求 agent 优先传 structured preflight flags 或 `--assessment`。

**当前状态**：
P1 第一版已实现。agent 可通过 assessment 文件或 CLI 结构化参数把“单文件低风险文档/本地修改”等判断传给 `governed-start`；harness 保留最终裁决权，遇到 public contract、external side effects、unclear/high risk 会升级到 governed-path。初始化生成的 AGENTS/skill 模板已要求 agent 不要只传原始用户措辞。

**优先级判断**：
P1。原因是它解决的是治理入口架构问题：没有 agent preflight，harness 会继续变成关键词分类器，并且 dogfood 过程中会反复出现“任务实际很简单但路由过重”的问题。该项优先级高于 P2 规格/安装能力，但低于已经完成的状态闭环和 release hook 第一版。

---

### 3D. NEXT.md Queue Closure / 队列闭环（新增，P1）

**来源**：本项目 dogfood 反馈

**现状问题**：
- `harness init` 会创建 `NEXT.md` 模板，但 `harness governed-start` 默认只写 `.harness/sessions/*.json`，不会把 governed task 登记为真实队列项。
- 多个任务执行后会出现大量 active session，但 `NEXT.md` 仍然只有模板注释或没有真实 `[ready]` / `[active]` / `[done]` 项。
- `harness runner`、status dashboard、跨轮恢复依赖 `NEXT.md` 作为 scheduler queue；如果入口和收口不更新队列，session 状态和 queue 状态会分裂。

**建议改进**：
把 `NEXT.md` 从可选 runner 输入提升为 governed workflow 的稳定任务索引：

```text
governed-start(governed-path)
-> append [active] queue item with Session / Layer / Verification command / Done when
-> review close
-> mark matching queue item [done] and append evidence/risk summary
```

第一版边界：
- 只对 `governed-path` 自动登记；`fast-path` 和 `trivial-safe-change` 仍不污染队列。
- `NEXT.md` 仍是本地个人队列，可继续被 `.gitignore` 忽略。
- 队列写入必须幂等：同一个 session 不重复追加。
- 收口更新应保留原条目内容，只把 `[active]` / `[ready]` 标记改为 `[done]` 并追加 evidence。

**实现位置**：
- `src/harness_governance/file_ops/queue.py`：已新增队列追加与完成标记 helper。
- `src/harness_governance/commands/governed_start.py`：governed-path session 创建后已同步追加 `[active]` 队列项。
- `src/harness_governance/commands/review.py`：`harness review close <task-id>` 已同步把匹配 session/task 的队列项标记为 `[done]`。
- `tests/test_commands/test_governed_start.py`、`tests/test_commands/test_verify_review_config.py`：已覆盖入口登记和收口更新。

**完成状态**：
P1 第一版已实现。`fast-path` / `trivial-safe-change` 不写队列；`governed-path` 创建 session 后会在 configured `queue_file` 中追加 `[active]` 项；`harness review close <task-id>` 会把匹配 `Session:` / `Change:` / 标题的 `[active]` 或 `[ready]` 队列项改为 `[done]` 并追加 evidence / risk。

**优先级判断**：
P1。原因是它修复任务状态的核心闭环：session 能驱动单次治理流程，但 `NEXT.md` 才是多任务排队、runner 调度、跨轮恢复和 review-next 收口的稳定索引。没有该闭环时，治理流程可运行但任务列表不可审计。

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
| **P1** | Slash 命令 Alias 层 | GStack | 中 | 已完成（CLI alias v1；slash 暂缓） |
| **P1** | 完整场景示例 | GStack | 中 | 已完成（文档） |
| **P1** | State Contract Closure / 状态契约闭环 | 事故复盘 | 中 | 第一版已完成 — 文档、E2E smoke、`state-contract check`、`layer ask/intake` |
| **P1** | Tag-only Release Verification Hook | CI 复盘 | 中 | 第一版已完成 — `verify local --release`、tag-only hook install |
| **P1** | Agent Preflight Assessment / 代理侧预评估路由 | Dogfood | 中 | 第一版已完成 — assessment schema、CLI 输入、分类器优先级 |
| **P1** | NEXT.md Queue Closure / 队列闭环 | Dogfood | 中 | 第一版已完成 — `governed-start` 写 `[active]`，`review close` 更新 `[done]` |
| **P2** | 轻量规格模式 | OpenSpec | 中 | 中 — 简单任务不需要 5 个文件 |
| **P2** | 渐进式安装 | Superpowers | 低 | 中 — 降低试用门槛 |
| **P3** | Skill 组合灵活性 | Superpowers | 高 | 低 — 适合 skill 市场模式 |
| **P3** | 快速上手引导 | 四件套 | 低 | 已完成 |

---

## 下一步行动

1. **P1 增强**：评估是否将 `harness state-contract check` 接入 `verification` gate / `harness check`。
2. **P1 增强**：在 `harness init` 中生成派生项目 state-contract 测试骨架。
3. **P1 增强**：在 `harness ship` 输出中提示 tag release 前安装/运行 release 验证（仅本仓库）。
4. **P2 设计**：定义 `spec quick` 与完整 change packet 的升级边界。
5. **P2 评估**：在已有 `--minimal` 基础上决定是否增加 `harness init --tier light`。
6. **暂缓项跟踪**：后续在平台 skill 文档中描述 `/harness ...` slash 触发方式。

---

*文档创建时间：2026-06-17*
*对比对象：Trellis + OpenSpec + Superpowers + GStack*
