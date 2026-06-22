# Quickstart — 5 minutes to governed development / 五分钟治理开发

This guide walks you from a clean directory to a fully working harness-governance project. For full command reference see [`README.md`](./README.md).

本指南带你从空目录走到完整可用的治理项目。完整命令参考见 README.md。

## 1. Install and initialize / 安装初始化 (30 s)

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
Created: .claude/skills/harness-governance-monitor/SKILL.md
Note: AGENTS.md triggers: AGENTS.md
Done. Your agent will now use harness governance for engineering work.

Quick start guide:
1. Describe your task: `harness governed-start "your task here"`
2. View current state: `harness status`
3. Read the current layer guide: `harness layer guide`
4. Full walkthrough: QUICKSTART.md
```

Each platform gets 4 skill tiers (strict/standard/light/monitor) / 每个平台 4 个 tier:

```bash
harness init --platform codex      # writes .agents/skills/
harness init --platform cline      # writes .clinerules/
harness init --platform cursor     # writes .cursor/rules/
harness init --platform opencode   # writes .opencode/agents/
harness init --platform windsurf   # writes .windsurf/skills/
harness init --platform qoderwork  # writes AGENTS.md
harness init --platform generic    # writes AGENTS.md
harness init --all-platforms       # all 8 platforms
```

## 2. Classify your first task / 分类任务 (30 s)

```bash
# Large task — auto-detected STRICT (12 layers) / 大型任务自动 STRICT
harness governed-start "Build a SaaS platform from scratch"

# Same entry via the ergonomic alias / 使用更直观的 alias
harness start "Build a SaaS platform from scratch"

# Medium task with explicit tier / 中型任务显式指定
harness governed-start "Add avatar field to user table" --rigor standard

# Small fix auto-detected LIGHT (6 layers) / 小修自动 LIGHT
harness governed-start "fix a typo in README"

# Pure Q&A — fast path / 纯问答 fast path
harness governed-start "What does layer 7 mean?"
```

With context flags / 带上下文标记:

```bash
harness governed-start "Add /v2/widgets endpoint" \
    --files src/api.py --contracts --external
```

## 3. Walk through layers with gates / 走层 + 门控

```bash
# Read the author interaction guide for current layer / 查看当前层的交互指南
harness layer guide
harness next

# Answer questions, then check the gate / 回答问题后检查门控
harness gate check intake-orientation
# → PASSED → lock file written / 锁文件写入
# or / 或
# → FAILED → complete remaining Q&A / 完成剩余问答

# Advance to next layer (gate-enforced since v0.7.0) / 推进到下一层
harness layer advance idea --confirmed

# Check timing — which layers took longest? / 耗时分析
harness gate timing
```

## 4. Walkthrough: bug fix with a gate / 示例：带门控的 bug 修复

This example shows the expected rhythm: classify, inspect the current layer,
answer or record evidence, check the gate, then advance.

这个示例展示常见节奏：先分类，再查看当前层，补齐问题或证据，检查门控，然后推进。

```bash
harness governed-start "Fix login redirect bug" --files src/auth.py --contracts
```

Expected output includes the route, rigor tier, current layer, and layer path:

预期输出会包含路由、严格程度、当前层和层路径：

```text
Routing: governed-path
Current layer: intake-orientation
Rigor tier: strict
Layer path: intake-orientation -> idea -> fact-discovery -> ... -> review-next
Next layer: idea
```

If the gate is not ready, the failure output tells you exactly what is missing:

如果门控尚未就绪，失败输出会明确列出缺失内容：

```bash
harness gate check intake-orientation
```

```text
Gate intake-orientation: FAILED (0/4 questions answered; artifacts missing: none)

Missing requirements:
- Questions answered: 0/4.

Red flags we do not accept:
- "This is just a small change, tests or evidence are not needed."
- "I'll add the missing gate evidence later."

Required actions:
1. Run `harness layer guide intake-orientation` and answer the required questions.
2. Create or record the missing evidence listed above.
3. Re-run `harness gate check intake-orientation`.
```

After the gate passes, advance to the next layer:

门控通过后，推进到下一层：

```bash
harness layer advance idea --confirmed
harness layer show
```

## 5. Run document gardener check / 文档园丁检查 (v0.7.1)

```bash
harness check docs
# Scans for / 扫描:
#   - Stale ADRs referencing deleted files / 过期 ADR 引用不存在的文件
#   - Broken cross-references in docs/ / docs/ 中的断链
#   - Version mismatches in documents / 文档版本号过时
#   - Empty sections in gate-required artifacts / 必需段落的缺失

harness check all   # includes docs check / 包含文档检查
```

## 6. Start a change packet / 创建变更包 (1 min)

```bash
harness packet init add-v2-widgets
ls docs/changes/add-v2-widgets
# contracts.md  design.md  proposal.md  tasks.md  verification.md
```

## 7. Use the queue (NEXT.md) / 使用队列

```markdown
[ready] Add /v2/widgets endpoint
- Layer: implementation
- Change: add-v2-widgets
Role: Implementer
Verification command: npm test
Done when: endpoint returns 200 with valid JSON
```

```bash
harness status              # dashboard / 仪表盘
harness status --json       # machine-readable / 机器可读
harness ship                # readiness check only; does not publish / 只做就绪检查，不发布
```

## Optional: bilingual output / 双语输出

```bash
# Windows
set HARNESS_LANG=zh-CN
harness packet check

# Unix
export HARNESS_LANG=zh-CN
harness packet check
# → 变更包检查通过: 共 1 项。 / Change packet check passed: 1 item(s).
```

## Optional: native subagent handoff / 原生 subagent 交接

```bash
harness runner prepare-native --role reviewer-verifier --queue <queue-id> --session-id <session-id>
harness runner record-native-spawn --session-id <session-id> --role reviewer-verifier --request-id <request-id> --agent-id <native-agent-id>
harness runner parse-result --role reviewer --session-id <session-id> --request-id <request-id> --agent-id <native-agent-id> --input result.json
harness gate check verification --session-id <session-id>
```

## What's next / 下一步

- `harness gate timing` — per-layer performance / 层耗时分析
- `harness check docs` — document quality scan / 文档质量检查
- `harness review close <id>` — close out completed work / 关闭完成的任务
- [`CHANGELOG.md`](./CHANGELOG.md) — version history / 版本历史

To tear down / 清理:

```bash
rm -rf .harness .claude .agents .clinerules .cursor .opencode .windsurf docs/ .planning/ NEXT.md AGENTS.md
```
