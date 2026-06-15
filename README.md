# harness-governance

[![Python](https://img.shields.io/badge/python-≥3.10-blue)](https://www.python.org)
[![License](https://img.shields.io/badge/license-MIT-green)](./LICENSE)
[![Status](https://img.shields.io/badge/status-alpha-orange)](./plan.md)

AI engineering governance CLI. Encodes a 12-layer state machine, nine
transition rules, and the Fast / Trivial / Governed routing decision as
a single Python tool. Any agent with shell access — Claude Code, Codex,
Cline, Cursor, OpenCode, generic assistants — can load a per-platform skill
adapter and gain access to the same governance commands.

> **Alpha preview** — the `product` branch ships the working CLI. See
> [`plan.md`](./plan.md) for the Phase A → B → C roadmap; PyPI
> publishing is intentionally deferred.

---

## Why this exists

The legacy Codex skill set exposed 25 separate `SKILL.md` files plus
20 shell / Node scripts to enforce the same governance. `harness-governance`
consolidates that into one `harness` command while preserving the
existing methodology verbatim:

* **12 harness layers** from `intake-orientation` to `review-next`
  (see [`src/harness_governance/data/references/layer-progression.md`](./src/harness_governance/data/references/layer-progression.md))
* **9 transition rules** — readiness before implementation, ADR
  durability, contract-before-implementation, etc.
* **Fast / Trivial / Governed** classification with the canonical
  disclosure block.
* **Markdown file conventions**: `NEXT.md`, `docs/changes/<id>/`,
  `.planning/<id>/`, `.harness/run-checkpoint.md`.

## How It Works

Every engineering task moves through a **12-layer state machine**:

```
intake → orientation → idea → fact-discovery → brainstorming → brief
       → architecture → adr → contract → readiness → implementation
       → verification → review-next
```

The state machine enforces nine transition rules — for example, a
readiness gate must pass before implementation starts, and architectural
decisions must be recorded as durable ADRs rather than left in chat.
Violations are reported without side effects, so the caller (human or
agent) decides how to respond.

Before any work begins, the CLI classifies the request as **Fast**
(pure question, no file changes), **Trivial** (single-file safe change
with a clear verification command), or **Governed** (anything touching
contracts, persistence, deployment, or multiple layers). Fast and
Trivial tasks skip the full pipeline; Governed tasks produce a
canonical disclosure block and enter the layer progression.

When a Governed task spans more than one layer, it gets a **change
packet** — a directory under `docs/changes/<id>/` containing five
template files: `proposal.md`, `design.md`, `tasks.md`, `contracts.md`,
and `verification.md`. The packet is the durable carrier for everything
the state machine needs to track. See the [glossary](./GLOSSARY.md)
for a full list of terms.

## Install

```bash
pip install harness-governance
harness --version
```

Or run from a checkout:

```bash
git clone <repo>
cd <repo>
pip install -e .[test]
harness --help
```

Requires Python ≥ 3.10 and `click` + `pydantic` v2 (installed automatically).

## 5-minute tour

```bash
cd my-project
harness init                              # writes .harness/config.toml + skill adapter
harness governed-start "Add /v2/widgets" --files src/api.py --contracts
harness packet init scaffold-cli          # docs/changes/scaffold-cli/
# fill contracts.md + verification.md …
harness packet check                      # exit 0 when complete
harness status                            # Markdown dashboard
harness plan init phase-a && harness plan attest
harness check --all
harness review close task-1 --evidence "pytest passes" --risk "scope creep"
```

For a longer walkthrough see [`QUICKSTART.md`](./QUICKSTART.md).

## Command reference

| Command | Purpose |
|---|---|
| `harness init [--platform {claude-code,codex,cline,cursor,opencode,qoderwork,generic}] [--force]` | Write `.harness/config.toml` + per-platform skill adapter |
| `harness governed-start "<task>" [--files …] [--contracts] [--external] [--unclear]` | Classify and produce the canonical disclosure block |
| `harness packet init <id>` / `check [target …]` | Manage change packets under `docs/changes/<id>/` |
| `harness entry {check,record}` | Validate / render Implementation Entry Records |
| `harness plan {init,attest,show,clear,complete}` | Planning carrier (`planning-with-files` parity) |
| `harness check {routing,packets,entry,inventory,all}` | Governance checks |
| `harness status [--format text|markdown|json] [--refresh]` | Aggregate dashboard view |
| `harness verify <preset>` | Run a verification preset (`routing-guardrails`, `all-local-checks`, …) |
| `harness review close <task-id> --evidence "..."` | Persist review/next state |
| `harness config init` | Write `.harness/config.toml` only |
| `harness runner start --mode {bounded,boundary} [--max-rounds N]` | Autonomous-ready loop |

All commands accept `--project-root <path>` (must come **before** the
subcommand) and `--json` for machine-readable output.

## Internationalization

User-facing strings live in a single catalog at
[`src/harness_governance/messages.py`](./src/harness_governance/messages.py).
Default language is English. Set `HARNESS_LANG=zh-CN` to switch:

```bash
HARNESS_LANG=zh-CN harness packet check
# 变更包检查未通过:
# - docs/changes/scaffold-cli/verification.md 必须记录验证命令、结果或 unable-to-verify 原因。
# / Change packet check failed:
# - docs/changes/scaffold-cli/verification.md must record verification commands, results, or an unable-to-verify reason.
```

When Chinese is active, every error is rendered bilingually as
`中文 / English` so mixed-language teams can still grep the English
text.

## Architecture

```
src/harness_governance/
├── cli.py                 # click entry point (harness command)
├── messages.py            # bilingual message catalog
├── state_machine/         # 12-layer enum + 9-rule engine + classification
├── models/                # Pydantic schemas (CLI I/O contract)
├── commands/              # one module per CLI subcommand
├── config/                # .harness/config.toml loader + default paths
├── file_ops/              # Markdown file helpers + LRU cache
│   └── _cache.py          # mtime-aware caching for large repos
├── runner/                # AutonomousReadyLoop + AgentExecutor
├── plugins/               # session_catchup (planning-with-files port)
└── data/                  # 8 templates + 18 references + fixtures + skill adapters
```

The state machine engine evaluates proposed transitions against the
9-rule policy and reports violations without side effects — every
caller collects violations and decides what to do.

## Skill Map

The 25 bundled skills are grouped by when you need them:

**Start here** — entry points and routing:
`harness-engineering` (main governed entry), `governed-implementation-entry`
(entry record validation), `review-next-governance` (closing and review),
`skill-use-transparency` (agent disclosure), `agent-routing-guard` (layer-aware routing).

**Core pipeline** — the governance backbone:
`contract-first-development`, `implementation-readiness-gate`,
`adr-writing`, `architecture-boundary-design`, `change-packet-protocol`,
`state-machine-layers`, `transition-rules`.

**Execution** — autonomous and semi-autonomous loops:
`autonomous-ready-loop`, `execution-prompt-authoring`, `agent-role-isolation`,
`subagent-runner`.

**Supporting** — cross-cutting concerns:
`bilingual-output`, `verification-presets`, `planning-carrier`,
`config-management`, `status-dashboard`, `inventory-check`,
`governed-start-classifier`, `packet-check`, `entry-check`,
`review-close`, `session-catchup`.

Each skill ships as a standalone Markdown file under `data/skills/` and is
referenced by the per-platform adapter written by `harness init`.

## Compatibility & parity

The CLI is parity-tested against the legacy `.mjs` / `.sh` / `.py`
scripts on packet init/check, entry check, and planning init. Both
Python and Node/Bash produce identical outputs and exit codes for the
same inputs.

* `harness packet init <id>` writes the same five files as
  `harness-engineering/scripts/init-change-packet.mjs`.
* `harness packet check` enforces the same rules as
  `check-change-packet.mjs` (status whitelist, contract artifact /
  blocked reason, verification evidence, archived backlinks).
* `harness entry check` mirrors
  `governed-implementation-entry/scripts/check-entry-record.mjs`
  (required fields, placeholder rejection, readiness / packetization
  format).
* `harness plan init/attest/complete` matches
  `planning-with-files/scripts/init-session.sh` /
  `attest-plan.sh` / `check-complete.sh`.

## Tests

```bash
pip install -e .[test]
pytest
```

321 tests cover the state machine, file ops, models, every CLI
subcommand, the autonomous loop with a subprocess executor, session
catchup, the bilingual message catalog, and the 9-role Subagent Runner.

## License

MIT — see [`LICENSE`](./LICENSE).

## Roadmap

See [`plan.md`](./plan.md). The CLI is feature-complete against the
plan; remaining work is parity hardening, performance, and PyPI
publishing (currently deferred — see Phase C notes).