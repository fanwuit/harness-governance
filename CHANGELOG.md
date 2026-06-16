# Changelog / 变更日志

All notable changes to `harness-governance` are documented in this file.
本文件记录了 `harness-governance` 的所有重要变更。

---

## [0.7.1] - 2026-06-16

### Added / 新增

- **`harness check docs`** — Document gardener check: stale ADRs, broken cross-references, version drift, empty sections / 文档园丁检查：过期 ADR、断链、版本漂移、空段落
- **Subagent Dispatch section** in all 24 skill files — context isolation rules for subagent delegation / 全部 24 个 skill 文件加入子代理分发防污染规则
- **`harness gate timing`** — per-layer timing from session transitions and gate lock files / 从 session 转换记录和锁文件读取每层耗时
- **`duration_seconds`** on `TransitionRecord` — wall-clock timing of each layer advance / 每次层推进的耗时记录
- **`check_duration_ms`** on `GateStatus` and lock files — gate check performance profiling / 门控检查耗时
- **`CLAUDE.md`** — project-level agent guidance replacing outdated AGENTS.md / 项目级 agent 指引
- Bilingual README, QUICKSTART, CHANGELOG / README、QUICKSTART、CHANGELOG 中英双语
- 47 new tests (total: ~920) / 新增 47 个测试

### Changed / 变更

- Skill version sentinel: `0.7.0` → `0.7.1` (all 24 files)
- `harness check all` now includes `check_docs`
- Version test now uses dynamic `__version__` import instead of hardcoded string

### Removed / 移除

- `AGENTS.md` at repo root (replaced by `CLAUDE.md`) / 仓库根目录的 AGENTS.md（已替换为 CLAUDE.md）

---

## [0.7.0] - 2026-06-16

### Added / 新增

- **5-layer defense system** / 五层防御体系
  - Layer 0: 3-Skill entry routing (strict/standard/light × 8 platforms = 24 skill files)
  - Layer 1: `RigorTier` auto-detection engine with 86 Chinese+English keywords
  - Layer 2: `LayerGateEngine` — programmatic gate verification for all 12 layers
  - Layer 3: `LockFileManager` — disk-level capability locks (`.harness/gates/`)
- **`harness gate` CLI** — `check`, `status`, `reset` subcommands
- **`harness layer advance` hardening** — mandatory gate check before advance, `--skip-gate --confirmed` safety interlock
- **`harness governed-start --rigor`** — explicit rigor tier override
- **`RigorTier`** enum — `LIGHT` (6 layers), `STANDARD` (12, flexible), `STRICT` (12, all questions)
- **`GATE_CATALOG`** — 12 structured gate definitions extracted from `layer-author-guide.md`
- 5 new Pydantic models: `QAPair`, `GateStatus`, `GateResult`, `RigorProfile`, `GateCheckInput`
- `SessionState.rigor_tier` + `SessionState.layer_qa` fields
- 20+ bilingual i18n messages (gate, rigor, layer)
- 168 new tests (total: 889)

### Changed / 变更

- `harness init` now writes 3 skill files per platform (strict/standard/light)
- `PLATFORM_SKILL_PATHS_BY_TIER` added to `config/defaults.py`
- `classify()` accepts `rigor` parameter; `RoutingDecision` carries `rigor_tier`
- Old flat skill files removed; replaced by `strict/`, `standard/`, `light/` directories

---

## [0.6.2] - 2026-06-15

### Fixed / 修复

- AGENTS.md false-positive stale detection / AGENTS.md 误报修复

---

## [0.6.1] - 2026-06-15

### Fixed / 修复

- UTF-8 BOM defense in skill files / skill 文件 BOM 防御
- Template version detection system / 模板版本检测系统
- Removed BOM from 8 platform skill files / 移除 8 个平台 skill 文件的 UTF-8 BOM

---

## [0.6.0] - 2026-06-15

### Added / 新增

- Layer author interactive guidance system / 层作者交互引导系统
- Subagent dispatch fix / subagent dispatch 修复

---

## [0.5.2] - 2026-06-15

### Added / 新增

- `harness session` command group / session 命令组
- Session catchup plugin / session 追赶插件
- Priority check hardening / 优先级检查加固

---

## [0.5.1] - 2026-06-15

### Added / 新增

- `harness priority` check / 优先级检查
- Competing skill detection / 竞争 skill 检测

---

## [0.5.0] - 2026-06-15

### Added / 新增

- `harness review` command / review 命令
- `harness verify` command / verify 命令
- `harness status` JSON output / status JSON 输出

---

## [0.1.0] - 2026-06-15

### Added / 新增

- **12-layer state machine** — intake-orientation through review-next, with 9 transition rules (T1–T9) enforced by `StateMachineEngine`.
- **CLI command surface** — `init`, `governed-start`, `packet {init,check}`, `entry {check,record}`, `plan {init,attest,show,clear,complete}`, `check {routing,packets,entry,inventory,all}`, `status`, `verify`, `review close`, `config {init,show,set,validate}`, `runner {start,render,parse-result}`.
- **Three-way classification** — `classify()` routes to Fast Path, Trivial Safe Change, or Governed Path.
- **Change packets** — five-template document discipline under `docs/changes/<id>/`.
- **Planning sessions** — `.planning/<id>/` with task-plan, findings, progress, and SHA-256 attestation.
- **NEXT.md scheduler queue** — `[active]` / `[ready]` items with layer, change-id, and evidence metadata.
- **Bilingual i18n** — `HARNESS_LANG=zh-CN` produces `中文 / English` dual output.
- **8 platform adapters** — claude-code, codex, cline, cursor, opencode, windsurf, qoderwork, generic.
- **Autonomous runner** — `AgentExecutor`, `AutonomousReadyLoop`, `OrchestratorPromptBuilder`, `TemplateRenderer`, `ResultParser`.
- **Comprehensive test suite** — 520 tests, 94% coverage.

### Changed / 变更

- Path unification — config-derived paths.
- De-Codex coupling — platform-agnostic documentation.
- Legacy cleanup — removed disabled skills and stale references.

### Fixed / 修复

- Config path resolution when no `.harness/config.toml` exists.
- Skill adapter references to removed Phase B terminology.
- `pyproject.toml` package-data glob patterns.

---

[0.7.1]: https://github.com/fanwuit/harness-governance/releases/tag/v0.7.1
[0.7.0]: https://github.com/fanwuit/harness-governance/releases/tag/v0.7.0
[0.6.2]: https://github.com/fanwuit/harness-governance/releases/tag/v0.6.2
[0.6.1]: https://github.com/fanwuit/harness-governance/releases/tag/v0.6.1
[0.6.0]: https://github.com/fanwuit/harness-governance/releases/tag/v0.6.0
[0.5.2]: https://github.com/fanwuit/harness-governance/releases/tag/v0.5.2
[0.5.1]: https://github.com/fanwuit/harness-governance/releases/tag/v0.5.1
[0.5.0]: https://github.com/fanwuit/harness-governance/releases/tag/v0.5.0
[0.1.0]: https://github.com/fanwuit/harness-governance/releases/tag/v0.1.0
