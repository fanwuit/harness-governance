# CLAUDE.md — harness-governance project guidance

## Project identity

`harness-governance` is a Python CLI that enforces AI engineering governance — 12 layers, 5-layer defense, gate engine, lock files, and autonomous runner. The primary artifact is the `harness` command installed via `pip install -e .`.

## Before any implementation work

```bash
harness governed-start "<task description>" --rigor standard
```

This classifies the request (Fast / Trivial / Governed) and creates a session with auto-detected rigor tier.

## Key architecture (v0.8.0)

```
src/harness_governance/
  cli.py                  — click entry point, 19 command groups
  state_machine/
    layers.py             — HarnessLayer enum (12 values)
    engine.py             — StateMachineEngine, 10 transition rules (T1-T10)
    classification.py     — 3-way classifier + RigorTier integration
    rigor.py              — STRICT/STANDARD/LIGHT detection
    gates.py              — GATE_CATALOG (12), LayerGateEngine, LockFileManager
    transitions.py        — TransitionContext + TransitionVerdict
  commands/
    init.py               — 4-tier skill injection (strict/standard/light/monitor × 8 platforms)
    governed_start.py     — entry router + session creation
    gate.py               — gate check/status/reset/timing
    layer.py              — layer advance/show/guide (gate-enforced)
    check.py              — check routing/packets/entry/inventory/docs/priority/all
    packet.py, entry.py, plan.py, status.py, verify.py, review.py
    runner.py, config_cmd.py, session_cmd.py
  session/                — SessionState + store (JSON persistence)
  models/schemas.py       — Pydantic v2 (20+ models)
  runner/                 — autonomous loop, orchestrator, result parser
  data/
    skills/{strict,standard,light,monitor}/  — 32 skill files (8 platforms × 4 tiers)
    role-prompts/          — 10 role templates
    references/            — layer-author-guide, layer-progression, etc.
    templates/             — change-packet, planning artifacts
  messages.py             — bilingual i18n catalog (~170 message IDs)
```

## Testing

```bash
pytest tests/ -x --tb=short          # full suite (~1570 tests)
pytest tests/test_skill_versions.py  # 32 skill file validation
pytest tests/test_commands/          # CLI integration tests
```

## Versioning

- `__init__.py` and `pyproject.toml` must stay in sync
- Skill files carry `<!-- harness-skill-version: X.Y.Z -->` sentinel
- `harness init` compares disk sentinel vs template to detect staleness
- `harness check docs` scans for version mismatches across all docs

## Style

- `bilingual("msg.id", **kwargs)` for all user-facing strings
- Pydantic v2 `extra="forbid"` on all schemas
- `time.perf_counter()` for timing (not `time.time()`)
- Pure logic functions accept `repo_root: Path` and return structured models
- Click commands are thin wrappers
