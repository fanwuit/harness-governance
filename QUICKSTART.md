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
harness init --platform codex      # writes .codex/skills/...
harness init --platform cline      # writes .clinerules/
harness init --platform cursor     # writes .cursor/rules/
harness init --platform qoderwork  # writes AGENTS.md
harness init --platform generic    # writes AGENTS.md
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

## 4. Use the queue (NEXT.md)

`harness init` creates a `NEXT.md` file in your project root. This is
the task queue that `harness status` and the autonomous runner read
from. Each item starts with a status label and optional metadata:

```markdown
[ready] Add /v2/widgets endpoint
- Layer: implementation
- Change: add-v2-widgets
Role: Implementer
Verification command: npm test
Done when: endpoint returns 200 with valid JSON
Forbidden shortcut: no mock data in production
```

Status labels: `[ready]` (can start now), `[active]` (in progress),
`[blocked]` (waiting on dependency), `[done]` (completed),
`[not-now]` (parked). The runner picks the first `[ready]` or
`[active]` item.

```bash
harness status              # see queue + packets + checkpoint
harness status --json       # machine-readable
```

## 5. Plan, attest, and check the harness (2 min)

```bash
harness plan init add-v2-widgets    # creates .planning/2026-06-13-add-v2-widgets/
harness plan attest                 # SHA-256 lock
harness plan show                   # print the stored hash
harness check --all                 # routing + packets + entry + inventory
harness status --refresh            # write .harness/status.{md,json}
```

## 6. Hand off to the autonomous runner (1 min)

The runner has three executors. **Orchestrator** is the most universal —
it generates a complete prompt document that any agent can load:

```bash
# generate an orchestrator prompt (platform-aware from .harness/config.toml)
harness runner start --executor orchestrator --dry-run

# write the prompt to a file for your agent to load
harness runner start --executor orchestrator --output prompt.md
```

**Subprocess** wraps any external command. The command receives the
prompt via `{prompt}` substitution or as a CLI argument:

```bash
# dry-run prints the prompt that would be sent
harness runner start \
    --executor subprocess \
    --command 'echo "{prompt}"' \
    --dry-run

# Codex
harness runner start \
    --executor subprocess \
    --command 'codex exec' \
    --max-rounds 5

# Claude Code
harness runner start \
    --executor subprocess \
    --command 'claude --print' \
    --max-rounds 5

# any other agent with a CLI
harness runner start \
    --executor subprocess \
    --command 'your-agent-cli --prompt' \
    --prompt-as-arg \
    --max-rounds 3
```

All modes support `--verification routing-guardrails` to run a
sanity check after each round.

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