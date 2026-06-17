# Changelog / 变更日志

All notable changes to `harness-governance` are documented in this file.
本文件记录了 `harness-governance` 的所有重要变更。

---

## [0.8.1] - 2026-06-17

### Fixed / 修复

- **Security**: `plan_id` path traversal prevention (slug sanitization + `set_active_plan` validation) / plan_id 路径穿越防御
- **Security**: `assert_inside` guard on `--output`, `--checkpoint`, `--invocation-log` paths / 输出路径越界检查
- **Security**: `write_lock` refuses to write failed gate locks; `read_lock`/`exists` validate content / 写锁拒绝失败 gate + 读锁校验
- **Security**: `config set` validates TOML before writing + type coercion + Literal validation / 配置写入前校验
- **Correctness**: `gate reset --all --confirmed` now works (LAYER made optional + early validation) / gate reset --all 可用
- **Correctness**: `plan show/clear <id>` no longer crashes with `AttributeError` / plan show/clear 不再崩溃
- **Correctness**: `check` uses `rglob` to find tiered SKILL.md files / check 用递归 glob 找 skill 文件
- **Correctness**: `scope_drift_detected` wired into `TransitionContext` + T8 no longer over-blocks / scope_drift 接入 + T8 不再误拦
- **Correctness**: tech-stack lint per-language check (Python ruff no longer covers Java) / lint 按语言判定
- **Correctness**: Windows NDJSON lock position consistency / Windows 锁位置一致性
- **Correctness**: Atomic writes for session/checkpoint files / session/checkpoint 原子写
- **Correctness**: Hook registration flag set after import loop / 钩子注册标志位修正
- **UTF-8 no-BOM guarantee**: `_strip_bom` + `write_text_no_bom` + `atomic_write_text` defensive strip; `init.py` 7 writes + `config_cmd.py` 2 writes all funnel through / UTF-8 无 BOM 强制保证

### Added / 新增

- **Queue numbered/bullet list support**: NEXT.md now accepts `1. [ready]`, `- [ready]`, `* [ready]` and numbered field lines like `1. Layer: implementation` / 队列支持编号列表和 bullet 列表格式

### CI/CD

- `ci.yml`: tag trigger + SHA-pinned actions + mypy/cov threshold + macOS matrix
- `publish.yml`: ci gate + version verification + TestPyPI + production PyPI

### Docs / 文档

- 24→32 skill files, 3→4 tiers, 9→10 rules, 14→19 command groups, ~1390 tests

---

## [0.8.0] - 2026-06-17

### Added / 新增

- **Gap 1 — Role isolation** (`isolation.py`): Per-role workspace directories under `.harness/isolation/`, NDJSON event log, READINESS gate hook / 角色隔离工作区 + 事件日志 + READINESS 门禁钩子
- **Gap 2 — Field alignment** (`alignment.py`): Contract field spec extraction (markdown tables + JSON schema), Python AST implementation scanning, CONTRACT + IMPLEMENTATION gate hooks. v0.8.0 Python only; non-Python downgrades to warning / 契约-实现字段对齐检查，v0.8.0 仅支持 Python
- **Gap 3 — Scope drift** (`drift.py`): `git diff`-based scope boundary enforcement, decomposition triggers, T10 transition rule (`T10-DRIFT-CONTRACT-BOUNDARY`), IMPLEMENTATION gate hook / 基于 git diff 的范围漂移检测 + T10 转换规则
- **Gap 4 — Tech stack management** (`tech_stack.py`): Language/framework/lint-tool detection, `LINT_TOOL_CATALOG` (14 languages) + `DOC_STYLE_CATALOG` (15 languages), INTAKE_ORIENTATION gate hook / 技术栈版本管理 + lint/文档规范目录
- **Gap 5 — Skill chain tracing** (`skill_chain.py`): UUID-based invocation lineage, ASCII tree + Mermaid diagrams, VERIFICATION + REVIEW_NEXT gate hooks / 技能调用链追踪 + 可视化
- **4th governance tier `monitor`**: 8 platforms × 4 tiers = 32 skill files (was 24) / 第 4 个治理 tier `monitor`，skill 文件数 24→32
- **Gate engine enhancement**: `blocking_artifacts` (separate from `required_artifacts` — avoids deadlock), `GATE_HOOK_REGISTRY` extensible hook system, `_ensure_hooks_loaded()` / 门禁引擎增强：产物阻塞 + 钩子注册表
- **`NDJSONWriter`** (`file_ops/ndjson_writer.py`): Inter-process NDJSON append with file locking (Windows `msvcrt` / Unix `fcntl`) / 带文件锁的 NDJSON 追加工具
- **`SubagentResult`**: 7 new optional fields (isolation, drift, skill-chain gaps) / 新增 7 个可选字段
- **10th transition rule**: `T10-DRIFT-CONTRACT-BOUNDARY` / 第 10 条转换规则
- **5 new CLI command groups** (14→19): `tech-stack`, `isolation`, `drift`, `alignment`, `skill-chain` / 5 个新命令组
- ~65 new i18n message keys / 约 65 条新 i18n 消息

### Changed / 变更

- `TransitionContext` gains `scope_drift_detected: bool = False` / 新增范围漂移标记
- `LayerGateDefinition` gains `blocking_artifacts: tuple[str, ...] = ()` / 新增阻塞产物字段

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
