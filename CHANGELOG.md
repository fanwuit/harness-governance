# Changelog

All notable changes to `harness-governance` are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-06-15

### Added

- **12-layer state machine** — intake-orientation through review-next, with 9 transition rules (T1–T9) enforced by `StateMachineEngine`.
- **CLI command surface** — `init`, `governed-start`, `packet {init,check}`, `entry {check,record}`, `plan {init,attest,show,clear,complete}`, `check {routing,packets,entry,inventory,all}`, `status`, `verify`, `review close`, `config {init,show,set,validate}`, `runner {start,render,parse-result}`.
- **Three-way classification** — `classify()` routes incoming requests to Fast Path, Trivial Safe Change, or Governed Path.
- **Change packets** — five-template document discipline (proposal, design, tasks, contracts, verification) under `docs/changes/<id>/`.
- **Planning sessions** — `.planning/<id>/` with task-plan, findings, progress, and SHA-256 attestation.
- **NEXT.md scheduler queue** — `[active]` / `[ready]` items with layer, change-id, and evidence metadata.
- **Bilingual i18n** — `HARNESS_LANG=zh-CN` produces `中文 / English` dual output; 70+ message IDs.
- **7 platform adapters** — claude-code, codex, cline, cursor, opencode, qoderwork, generic.
- **Autonomous runner** — `AgentExecutor` base, `SubprocessAgentExecutor`, `CodexCliExecutor`, `AutonomousReadyLoop`, `OrchestratorPromptBuilder`, `TemplateRenderer`, `ResultParser`, `VariableExtractor`.
- **Logging system** — `logging_setup.py` with `--verbose` / `--debug` global CLI flags; strategic logging at classification, state-machine, and config decision points.
- **Config management** — `harness config show/set/validate` subcommands with TOML read-modify-write and schema validation.
- **CI/CD** — GitHub Actions workflows (`ci.yml`, `publish.yml`).
- **Comprehensive test suite** — 520 tests, 94% coverage.

### Changed

- **Path unification** — `build_status()` now loads `HarnessConfig` and uses config-derived paths instead of hardcoded `DEFAULT_PROJECT_CONFIG`; `load_config()` guarantees all path fields are absolute.
- **De-Codex coupling** — `layer-progression.md` and runner documentation generalized to be platform-agnostic.
- **Legacy cleanup** — removed disabled skills, stale test fixtures, and outdated reference files.

### Fixed

- Config path resolution when no `.harness/config.toml` exists (defaults were left as relative paths).
- Skill adapter references to removed Phase B terminology.
- Role prompts missing `QUEUE_ITEM` field documentation.
- OpenCode platform missing `ENV_HINT` in defaults.
- `pyproject.toml` package-data glob patterns for recursive template/skill inclusion.

[0.1.0]: https://github.com/fanwuit/my-agent-first-skills/releases/tag/v0.1.0
