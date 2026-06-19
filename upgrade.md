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

### 1B. User-Perceived Integration Evidence Gate / 用户感知集成证据门禁（新增，P0）

该项已从 P1 提升为 P0。原因是它约束的不是测试体验优化，而是“测试通过是否真的证明用户可感知功能可交付”的硬门禁；如果继续允许 smoke / contract / 自造数据冒充 MVP、闭环、保存、发布等真实用户验收，派生项目会系统性地产生假闭环。

P0 落地顺序：
1. 已实现 `harness check user-evidence`，先做文档级机器检查。
2. 已接入 `harness check all` / `harness ship` / verification gate，缺失证据时阻止交付收口。
3. 已在 `harness init` 中生成 user-evidence 模板，并加入反例测试防止回归。

详细规则、字段和实现位置见 3E。

### 1C. Subagent Separation Gate / 子代理责任隔离门禁（新增，P0）

该项应作为与 User-Perceived Integration Evidence Gate 并列的 P0 治理升级项。User-Evidence 解决“测试证据是否证明真实用户闭环”；Subagent Separation 解决“谁定义验收、谁实现、谁最终验收”的上下文污染问题。它约束的是交付收口权和验收独立性，直接防止 agent 自己写契约、写测试、写实现、再自己验收的假闭环。

**现状问题**：
- 当前已有 heartbeat、invocation log、parse-result、skill-chain、isolation 等机制，但没有强制触发 subagent，也没有强制验收独立性。
- 同一个上下文可以连续完成 contract、test/evidence、implementation、verification，并最终声明 `MVP complete` / `closed loop complete` / `ship ready`。
- 即使存在 runner invocation 记录，也缺少按角色验证的“谁做了什么”和“谁有权收口”的硬检查。

**建议改进**：
新增门禁命令：

```bash
harness check subagent-separation
```

第一版以“证据检查”为主，不要求自动启动 subagent；后续可再增强为 runner 自动分派和角色 prompt 强制渲染。

**触发条件**：
- strict 路由或 P0/P1 治理项。
- 变更 public contract、schema、API、CLI contract、文档化验收契约。
- 涉及 persistence、外部状态、save/publish/login/payment/upload/import/export 等真实用户闭环。
- 用户或 agent 声明 MVP、closed loop、ship ready、release ready、user-visible save complete。
- verification retry、失败后重验、或曾由同一上下文修改验收证据后再次验收。

**必须声明角色矩阵**：

```markdown
## Subagent Separation
- Required: yes | no
- Contract Owner:
- Test/Evidence Owner:
- Implementer:
- Verifier:
- Waiver:
```

**必须有独立执行证据**：
- `.harness/invocations.ndjson` 或 `docs/changes/<change-id>/.invocations.ndjson` 必须存在 role result。
- 至少能区分 contract owner、test/evidence owner、implementer、verifier 的执行记录。
- `Required: no` 时必须写明 waiver 理由、替代验证和残余风险。

**文件所有权检查**：
- implementer 不能在未批准情况下修改 contract/evidence 文件。
- test/evidence owner 不能在没有声明的情况下修改实现文件。
- verifier 如果修改了实现文件，不能再作为最终 accept / ship-ready verifier。

**收口权限检查**：
- 只有 verifier 可以关闭 `MVP complete`、`closed loop complete`、`ship ready`、`release ready`、`user-visible save complete` 等声明。
- 如果 verifier 与 implementer 是同一上下文或同一 invocation，必须失败，除非存在明确 waiver。
- 如果 verifier 缺少独立证据，只能声明 `implementation smoke passed` 或 `integration not yet independently accepted`，不能声明交付完成。

**实现位置**：
- `src/harness_governance/commands/check.py`：新增 `subagent-separation` 检查并接入 `check all`。
- `src/harness_governance/commands/aliases.py`：在 `harness ship` 中纳入该检查。
- `src/harness_governance/commands/runner.py`：输出 role result 并记录角色矩阵所需字段。
- `src/harness_governance/state_machine/gates.py`：在 readiness / verification / review-next gate 中加入角色隔离问题和检查 hook。
- `src/harness_governance/state_machine/skill_chain.py`：约束 role handoff 与 clean-worker 证据。
- `tests/test_commands/test_check_cmd.py`：覆盖缺失角色矩阵、缺失 invocation、所有权越界、收口权限失败和 waiver。
- `tests/test_commands/test_runner_cmd.py`：覆盖 runner role result 记录。
- `tests/test_state_machine/test_skill_chain.py`：覆盖角色隔离链路和 verifier 独立性。

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
- `src/harness_governance/commands/check.py`：已新增 `harness check state-contract` 并接入 `harness check all`。
- `src/harness_governance/state_machine/gates.py`：verification gate 已要求 state-contract 证据。
- `src/harness_governance/commands/init.py`：已在非 minimal 初始化中生成派生项目 state-contract 测试骨架。
- `docs/verification/state-contract-p1.md`：已记录本次 P1 增强验证证据。

**完成状态**：
P1 第二版已实现。已具备正式问答入口、状态契约文档、最小 E2E smoke、`harness state-contract check`、`harness check state-contract`、`check all` 集成、verification gate 集成，以及 `harness init` 派生项目测试骨架。剩余增强是更自动化的 writer/consumer 扫描。

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

### 3E. User-Perceived Integration Evidence Gate / 用户感知集成证据门禁（已提升为 P0）

**来源**：本项目 dogfood 反馈；产品交付可用性风险

**现状问题**：
- 单元测试、集成测试、E2E 测试都可能变成“自造数据自证”：测试自己创建输入、自己 mock 掉关键风险、自己断言刚写入的值，却没有证明真实产品路径可用。
- E2E 可能绕过真实用户入口，点击隐藏按钮或 test-only 控件，不验证 reload / reopen / readback。
- 集成测试可能只集成 fake / in-memory 依赖，关键 writer -> consumer 链路没有被真实消费。
- 单元测试可能只断言 mock 被调用、覆盖私有实现细节或 happy path，无法证明公开行为和边界条件。
- agent 可能把 smoke / contract 测试偷换成 MVP complete / closed loop complete / user-visible save complete。
- 这些问题不能靠 agent 自觉解决；它们直接影响 `ship` 前对产品可用性和用户可感知闭环的判断。

**建议改进**：
新增用户感知集成证据门禁，约束所有涉及 MVP、闭环、保存、发布、导入导出、登录、支付、上传、运行、预览、生成、同步等用户可感知功能的任务：

```bash
harness check user-evidence
```

核心规则：
1. **不能只验内部路径**：E2E / real-user acceptance 必须从真实用户入口开始，不能从 internal helper、隐藏验收区、fixture-only 控件、测试专用按钮开始。
2. **不能只断言自造数据**：测试可以输入数据，但必须证明输入来自真实可见 UI，后端请求 payload 等于 UI 当前值，后端读回后重新进入同一真实 UI 能显示该值。
3. **必须区分三类证据**：
   - `smoke`：技术链路跑通。
   - `contract`：API / 数据契约正确。
   - `real-user acceptance`：用户实际路径闭环可见。
   MVP / closed loop / user-visible save 只能由 `real-user acceptance` 收口。
4. **选择器约束**：real-user acceptance 不允许依赖内部结构捷径，例如 `.lifecycle-actions button:first()`、hidden test panels、acceptance drawer、mock/fallback buttons，除非该控件就是用户真实主入口并在 contract 中登记。
5. **必须有 anti-self-proof 断言**：保存类至少证明页面主编辑器当前值、PUT/POST request payload、GET/readback response、刷新后主编辑器显示值四者一致。其他闭环也要定义“用户输入 / 系统输出 / 后端状态 / 重新打开状态一致”的等价断言。
6. **命名禁止偷换**：如果只有 smoke / contract，不能标记 `MVP complete`、`closed loop complete`、`user-visible save complete`，只能标记 `API-backed smoke passed`、`prototype proof passed`、`integration not yet accepted`。

第一版要求每个待交付变更在 `docs/verification/<change-id>.md` 或 change packet `verification.md` 中提供结构化证据：

```markdown
## User-Perceived Integration Evidence
- Evidence level: smoke | contract | real-user acceptance
- Real User Entry:
- User-Visible State:
- Persistence/External State:
- Anti-Self-Proof Assertion:
- Forbidden Test Shortcuts:
- Command:
- Result:
```

如果存在 MVP / closed loop / user-visible save 交付声明，则 `Evidence level` 必须是 `real-user acceptance`，并且 `Anti-Self-Proof Assertion` 不能为空。

基础测试证据仍需保留，但不能冒充用户可感知闭环：

```markdown
## Unit Evidence
- Command:
- Behaviour under test:
- Boundary/negative cases:
- Mock boundary:
- Why mocks do not hide product risk:

## Integration Evidence
- Command:
- Real modules crossed:
- Writer:
- Consumer:
- Persisted/readback state:
- External systems mocked:
- Why acceptable:
```

不适用时必须显式写：

```markdown
## User-Perceived Integration Not Applicable
- Reason:
- Replacement verification:
- Residual risk:
```

机器检查第一版先做文档级硬约束：
- 必填字段不能为空。
- 涉及用户可感知功能时必须存在 `User-Perceived Integration Evidence` 或明确 `Not Applicable`。
- 若文本中出现 `MVP complete` / `closed loop complete` / `user-visible save complete`，但 evidence level 不是 `real-user acceptance`，检查失败。
- real-user acceptance 必须声明真实入口、用户可见状态、持久化/外部状态、anti-self-proof assertion 和 forbidden shortcuts。
- Unit evidence 必须包含边界/负例说明，不能只说明 mock 调用。
- Integration evidence 必须声明真实模块边界、writer、consumer 和 readback。
- 出现明显自证/规避词时失败，例如 `hidden`、`test-only`、`mock all`、`assert called`、`skip e2e`、`TODO evidence`、`not tested`。

接入硬门禁：
- `harness check all` 包含 `user-evidence`。
- `harness ship` 在缺少或不合格证据时失败。
- verification gate / review-next 前要求该检查通过。
- implementation readiness / verification 层 Author Questions 必须询问：
  - 用户真实入口是什么？
  - 哪个 UI 状态是用户感知结果？
  - 哪个后端/持久化状态证明不是 mock？
  - 测试是否验证 payload 与 UI 当前值一致？
  - 是否存在测试专用路径冒充产品路径？
- `harness init` 生成 user-evidence 模板，派生项目默认继承该约束。

**实现位置**：
- `tests/VERIFICATION_CONTRACTS.md`：已新增验证证据契约。
- `docs/verification/p0-user-evidence.md`：已记录本次 P0 门禁的验收证据。
- `src/harness_governance/commands/check.py`：已新增 `harness check user-evidence` 并接入 `check all`。
- `src/harness_governance/commands/aliases.py`：`harness ship` 已纳入 user-evidence 检查。
- `src/harness_governance/commands/init.py`：已生成 `docs/verification/user-evidence-template.md`。
- `src/harness_governance/state_machine/gates.py`：已在 readiness / verification 层加入用户感知证据问题和 verification gate hook。
- `tests/test_commands/test_check_cmd.py`：已覆盖缺字段、自证词、Not Applicable、MVP 命名偷换、通过样例和 `check all` 集成。
- `tests/test_commands/test_aliases.py`、`tests/test_commands/test_init.py`：已覆盖 `ship` 集成和 init 模板生成。

**优先级判断**：
P0 第一版已实现；P1 增强已实现。原因是它约束的是"测试证据是否能证明用户可感知功能真的可交付"，属于交付可靠性硬门禁，而不是 P1 增强项。State Contract 解决治理状态闭环；User-Perceived Integration Evidence Gate 解决 agent 用 smoke/contract/自造数据冒充真实用户闭环的问题。第一版先做文档级机器检查；第二版已增强到 Playwright trace / HAR request payload / selector 扫描（`src/harness_governance/commands/evidence_scanner.py`）。后续可逐步增强到 AST / Playwright screenshot comparison / 更深 payload 匹配。

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
| **P1** | State Contract Closure / 状态契约闭环 | 事故复盘 | 中 | 第二版已完成 — 接入 `check state-contract`、`check all`、verification gate、init 测试骨架 |
| **P1** | Tag-only Release Verification Hook | CI 复盘 | 中 | 第一版已完成 — `verify local --release`、tag-only hook install |
| **P1** | Agent Preflight Assessment / 代理侧预评估路由 | Dogfood | 中 | 第一版已完成 — assessment schema、CLI 输入、分类器优先级 |
| **P1** | NEXT.md Queue Closure / 队列闭环 | Dogfood | 中 | 第一版已完成 — `governed-start` 写 `[active]`，`review close` 更新 `[done]` |
| **P0** | User-Perceived Integration Evidence Gate / 用户感知集成证据门禁 | Dogfood | 中 | 第一版已完成 — `check user-evidence`、`check all`、`ship`、verification gate、init 模板 |
| **P0** | Subagent Separation Gate / 子代理责任隔离门禁 | Dogfood | 中 | 第一版已完成 — `check subagent-separation`、`check all`、`ship`、文档级证据检查 |
| **P1** | Governance UX Friction Reduction / 治理交互降噪 | Dogfood | 中 | 新增 P1 — 选择式问答、agent 预填、批量摘要确认、关键风险点强确认 |
| **P2** | 轻量规格模式 | OpenSpec | 中 | 中 — 简单任务不需要 5 个文件 |
| **P2** | 渐进式安装 | Superpowers | 低 | 中 — 降低试用门槛 |
| **P3** | Skill 组合灵活性 | Superpowers | 高 | 低 — 适合 skill 市场模式 |
| **P3** | 快速上手引导 | 四件套 | 低 | 已完成 |

---

## 下一步行动

1. **P1 已完成后续版**：Governance UX Friction Reduction。已实现 dependency-free CLI 切片：`harness layer answer` 对同层同问题去重并保留最新答案，`harness layer ask` 跳过已回答问题，gate failure guidance 去重重复缺失项并提供 `yes` / `no` / `back` 明确选择；后续版已增加 `harness layer wizard`、TTY 方向键/`j`/`k` 选择与编号 fallback、非交互 abort guidance、Codex 平台 `/harness ...` slash 触发方式文档。
2. **P1 增强**：在 `harness ship` 输出中提示 tag release 前安装/运行 release 验证（仅本仓库）。
3. **P1 已完成**：将 user-evidence 从文档级检查增强到 Playwright trace / HAR request payload / selector 扫描。已实现 `src/harness_governance/commands/evidence_scanner.py`，扫描 Playwright trace zip、HAR HTTP archive、测试源文件中的禁止 selector、空 payload、mock response 指标；自动接入 `check_user_evidence`，无 artifact 时优雅跳过。
4. **P1 后续增强**：将 state-contract 从显式要求列表增强为更自动化的 writer/consumer 扫描。
5. **P2 设计**：定义 `spec quick` 与完整 change packet 的升级边界。
6. **P2 评估**：在已有 `--minimal` 基础上决定是否增加 `harness init --tier light`。
7. **暂缓项跟踪**：后续在平台 skill 文档中描述 `/harness ...` slash 触发方式。

---

*文档创建时间：2026-06-17*
*对比对象：Trellis + OpenSpec + Superpowers + GStack*
