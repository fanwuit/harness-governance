# Quickstart — 5 minutes to governed development

This guide walks you from a clean directory to a fully working
harness-governance project in five focused steps. For full command
reference see [`README.md`](./README.md).

## 1. Install and initialize (30 s)

```bash
pip install harness-governance
mkdir my-project && cd my-project
harness init
```

Output:

```
Detected: claude-code
Created: .harness/config.toml
Created: .claude/skills/harness-governance/SKILL.md
Done. Your agent will now use harness governance for engineering work.
```

If you use a different agent platform:

```bash
harness init --platform codex    # writes .codex/skills/...
harness init --platform cline    # writes .clinerules/
harness init --platform generic  # writes AGENTS.md
```

## 2. Classify your first task (30 s)

```bash
harness governed-start "Add /v2/widgets endpoint" \
    --files src/api.py --contracts --external
```

You'll get a routing decision plus the canonical disclosure block. For
pure questions, drop the flags:

```bash
harness governed-start "What does layer 7 mean?"
# → fast-path: just answer the question
```

## 3. Start a change packet (1 min)

Change packets are the durable carrier for anything that touches more
than one harness layer.

```bash
harness packet init add-v2-widgets
ls docs/changes/add-v2-widgets
# contracts.md  design.md  proposal.md  tasks.md  verification.md
```

The packet starts in `draft` status. Edit the five files in place:

```bash
$EDITOR docs/changes/add-v2-widgets/contracts.md     # add artifact + path
$EDITOR docs/changes/add-v2-widgets/verification.md  # add commands + results
```

When the packet is structurally complete:

```bash
harness packet check
# Change packet check passed: 1 packet(s).
```

## 4. Plan, attest, and check the harness (2 min)

```bash
harness plan init add-v2-widgets    # creates .planning/2026-06-13-add-v2-widgets/
harness plan attest                 # SHA-256 lock
harness plan show                   # print the stored hash
harness check --all                 # routing + packets + entry + inventory
harness status --refresh            # write .harness/status.{md,json}
```

## 5. Hand off to the autonomous runner (1 min)

When you want to let the queue drive a Codex / Claude worker:

```bash
# dry-run prints the prompt that would be sent
harness runner start \
    --executor subprocess \
    --command 'echo "{prompt}"' \
    --dry-run

# real run (requires codex CLI on PATH)
harness runner start \
    --executor codex \
    --max-rounds 5 \
    --verification routing-guardrails
```

## Optional: bilingual output

```bash
HARNESS_LANG=zh-CN harness packet check
# 变更包检查未通过: / Change packet check failed:
# - docs/changes/add-v2-widgets/verification.md 必须记录验证命令、结果或 unable-to-verify 原因。
# / docs/changes/add-v2-widgets/verification.md must record verification commands, results, or an unable-to-verify reason.
```

## What's next

* `harness status` — full Markdown / JSON dashboard.
* `harness review close <task-id> --evidence "..."` — record
  review/next state when finishing work.
* [`plan.md`](./plan.md) — full design and Phase A → B → C roadmap.

To tear down the example:

```bash
rm -rf .harness .claude/skills/harness-governance docs/ .planning/ NEXT.md AGENTS.md
```