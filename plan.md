# 实施方案：5项治理缺陷修复 (v0.7.1 → v0.8.0)

## 背景

用户测试最新版 harness-governance 后发现 5 个系统性问题——全部是架构层面的执行缺失，不是简单 bug。当前系统有丰富的提示词层面引导（角色提示、技能模板、编排器指令），但缺少程序化执行机制来保证：角色隔离、字段对齐、漂移防护、技术栈版本管理、技能调用链追踪。本方案为这 5 个缺口在 gate/layer/check 层面增加机械化执行。

## 总体变更范围

- **5 个新状态机模块**: `isolation.py`, `alignment.py`, `drift.py`, `tech_stack.py`（含 lint 工具目录）, `skill_chain.py`
- **5 个新 CLI 命令组**: `harness isolation`, `harness alignment`, `harness drift`, `harness tech-stack`（含 `lint` 子命令）, `harness skill-chain`（14→19 组）
- **约 21 个新 Pydantic 模型** 加入 `schemas.py`（含 `LintGap`、`DocStyleGap`）
- **1 条新转换规则**: T10-DRIFT-CONTRACT-BOUNDARY
- **1 个 Gate 引擎增强**: `LayerGateEngine.check()` 改为产物阻塞 + 可选的程序化确认钩子
- **Gate 目录扩展**: 6 个层（INTAKE_ORIENTATION、CONTRACT、READINESS、IMPLEMENTATION、VERIFICATION、REVIEW_NEXT）新增确认项 + 产物要求
- **约 90 条新 i18n 消息键**
- **约 350-400 个新测试**（920→约 1270-1320）
- **版本号**: 0.7.1 → 0.8.0

### 前置条件：Gate 引擎增强（实施第一步）

当前 `LayerGateEngine.check()`（`gates.py:433-437`）仅按 Q&A 数量判断 gate 是否通过——`required_artifacts` 和 `confirmation_items` 都是纯信息性的。这导致 5 个缺口新增的所有产物要求和确认项都不会真正阻塞 gate。**在开始任何缺口实施之前，必须先完成以下 gate 引擎改造：**

1. **新增 `blocking_artifacts` 字段（与现有 `required_artifacts` 分离）**：
   - `LayerGateDefinition` 增加 `blocking_artifacts: tuple[str, ...] = ()` 字段（需修改 `__slots__` 和 `__init__`，默认空元组，参照下方 TransitionContext 的验证清单）。
   - `check()` 中 `blocking_artifacts` 的 glob 匹配为空时 `passed = False`。
   - **为什么不能直接让 `required_artifacts` 阻塞**：现有 `required_artifacts` 包含 `.harness/sessions/*.json`（INTAKE_ORIENTATION，session 创建前不存在）和 `.harness/gates/10-implementation.lock`（IMPLEMENTATION，lock 在 gate 通过后才写入 `layer.py:181`）——全局阻塞会导致死锁。`blocking_artifacts` 是空元组时对现有 12 个 gate 行为完全无影响。
   - 只有缺口产出的 NDJSON/JSON 文件进入 `blocking_artifacts`。**规则：`blocking_artifacts` 中的文件必须由 gate 外部产生（runner、CLI 命令、用户操作），不能由 hook 自身生成**——因为 `check()` 先检查 artifacts 再执行 hooks。
     - VERIFICATION: `".harness/skill-chains/*.ndjson"`（由 autonomous runner 在实现阶段产出，gate 检查时已存在）
   - 缺口 1（隔离）、缺口 2（对齐）、缺口 3（漂移）的校验完全通过钩子实现，不依赖 `blocking_artifacts`：
     - 隔离 NDJSON（`.isolation.ndjson`）在 session 中逐步追加，gate 检查时可能尚无记录 → 钩子读取并检查
     - 对齐 NDJSON 由 IMPLEMENTATION 钩子调用 `compute_alignment()` 动态生成 → 不能放入 `blocking_artifacts`
     - scope 声明（`.harness/scopes/*.json`）由用户或 planner 子代理写入 → 钩子读取并比对 git diff

2. **Gate 钩子注册表（避免循环导入）**：
   - **不在 `LayerGateDefinition` 上增加 `check_hooks` 字段**——因为 `GATE_CATALOG` 是 `gates.py` 中的模块级字面量，在 catalog 中引用 `isolation.py`/`alignment.py` 等 gap 模块的钩子函数会导致循环导入（gap 模块需要 `from .gates import LayerGateDefinition`，而 `gates.py` 需要 `from .isolation import ...`）。
   - 替代方案：在 `gates.py` 中增加独立的**钩子注册表**：
     ```python
     # gates.py 新增
     GATE_HOOK_REGISTRY: dict[HarnessLayer, list[Callable]] = {}

     def register_gate_hook(layer: HarnessLayer, hook: Callable) -> None:
         """注册一个 gate 确认钩子。各缺口模块在 import 时调用。"""
         GATE_HOOK_REGISTRY.setdefault(layer, []).append(hook)

     def get_gate_hooks(layer: HarnessLayer) -> list[Callable]:
         """返回该层所有已注册的确认钩子（可能为空）。"""
         return GATE_HOOK_REGISTRY.get(layer, [])
     ```
   - 钩子签名：`(session, project_root) -> list[str]`，返回失败消息列表（空列表 = 全部通过）。
   - `LayerGateEngine.check()` 在计算 `confirmation_items_unmet` 时调用 `get_gate_hooks(layer)`，执行所有钩子，收集非空返回值。
   - **无需修改 `LayerGateDefinition` 的 `__slots__` / `__init__`**。
   - **`_ensure_hooks_loaded()`**：在 `gates.py` 中增加该函数，显式 import 所有缺口模块（`isolation`、`alignment`、`drift`、`tech_stack`、`skill_chain`），用 `try/except ImportError` 包裹以便缺口模块缺失时降级。`LayerGateEngine.check()` 开头调用此函数，确保任意 CLI 路径进入 gate check 时钩子已注册。

3. **向后兼容**：无钩子的 gate 行为不变（注册表查询返回空列表）。钩子抛异常时记录日志但不崩溃（单个钩子失败不影响其他钩子）。`blocking_artifacts` 默认为空元组，现有 12 个 gate 无需修改。

**`LayerGateDefinition` 修改验证**：增加 `blocking_artifacts: tuple[str, ...]` 需修改：
- `__slots__` 元组（第 44-50 行）增加 `"blocking_artifacts"`
- `__init__` 签名（第 52-58 行）增加 `blocking_artifacts: tuple[str, ...] = ()`
- `GATE_CATALOG` 中仅 VERIFICATION（`".harness/skill-chains/*.ndjson"`）显式传 `blocking_artifacts`，其余 11 个 gate 使用默认值。CONTRACT 和 IMPLEMENTATION 的对齐报告由钩子动态生成，不进入 `blocking_artifacts`。

各缺口在自身模块 `import` 时注册钩子（模块级调用 `register_gate_hook()`）：
- Gap 1（隔离）→ READINESS gate：读取 `.isolation.ndjson` 检查违规记录
- Gap 2（对齐）→ CONTRACT + IMPLEMENTATION gate：读取对齐报告检查通过状态；非 Python 项目降级为 warning
- Gap 3（漂移）→ IMPLEMENTATION gate：读取 scope 声明比对 git diff
- Gap 4（技术栈）→ INTAKE_ORIENTATION gate：检查 lint/doc-style 是否全部确认
- Gap 5（技能链）→ VERIFICATION gate：读取调用链检查孤儿节点

---

## 缺口 1：角色 + 子代理隔离

**问题**：编排器指示 AI 平台按角色生成子代理，但没有文件系统级别的隔离执行。子代理可以读写其角色范围之外的文件。

**核心思路**：在 `.harness/isolation/<session_id>/<role>/` 下为每个角色创建独立工作目录，记录所有跨角色文件访问事件到 `.isolation.ndjson`，在 READINESS 门禁处校验。

### 新建文件
- `src/harness_governance/state_machine/isolation.py` — `IsolationManager` 类
  - `create_workspace(role, session_id, change_id)` → 创建隔离目录
  - `check_violations(role, files_touched)` → 返回超出范围的路径列表
  - `append_event(record)` → 写入隔离事件日志
  - `verify_workspace(session_id)` → `IsolationSummary`
- `src/harness_governance/commands/isolation.py` — Click 命令组：`init`, `check`, `list`
- 对应测试文件

### 新增模型 (schemas.py)
- `IsolationWorkspace` — role, workspace_path, isolation_kind, session_id, allowed_paths（glob patterns）, allowed_roles（可协作的角色列表）
- `IsolationRecord` — event 类型, role, workspace_path, timestamp, files_touched, cross_role_accesses
- `IsolationSummary` — roles_isolated, cross_role_violations, files_outside_scope, workspaces_valid

### 修改文件
- `runner/result_parser.py` — `SubagentResult` 增加 `isolation_workspace` 和 `isolation_violations` 字段
- `runner/orchestrator.py` — `_determine_roles()` 之后计算隔离路径并嵌入提示词
- `state_machine/gates.py` — READINESS 门禁新增 3 个确认项：
  - "所有必需角色均已创建隔离工作区"
  - "未检测到跨角色文件访问违规"
  - "隔离事件日志与调用日志一致"

### 目录结构
```
.harness/isolation/<session_id>/
  workspace.json          # 持久化 IsolationWorkspace（allowed_paths, allowed_roles 等）
  planner/
  contract-writer/
  implementer/
  reviewer/
  .isolation.ndjson
```

`create_workspace()` 在创建目录时写入 `workspace.json`；`check_violations()` 从该文件读取角色范围配置。

---

## 缺口 2：字段对齐约束

**问题**：门禁只检查问题数量和产物是否存在，不检查内容一致性。契约可以定义 `user_id: UUID`，而实现写成 `uid: str`——系统完全检测不到。

**核心思路**：从契约文档中提取字段规格（正则解析 markdown 表格、JSON schema），用 AST 扫描实现代码找到对应字段，比较名称、类型、是否必填，生成对齐报告。同时支持跨层追溯矩阵。

### 语言支持范围

**v0.8.0 仅支持 Python**。`scan_implementation()` 使用 `ast` 模块解析 Python 源码。对于非 Python 项目，`AlignmentReport` 返回 `unsupported_languages: list[str]`，gate 钩子对此降级为 warning（不阻塞），`harness alignment check` 输出明确提示"字段对齐目前仅支持 Python，检测到 <语言>，跳过对齐检查"。

后续版本扩展策略（不在 v0.8.0 范围内）：
- TypeScript/JavaScript：tree-sitter 或 regex 回退
- Java：javaparser 或 regex 回退
- 通用回退：regex 模式匹配（字段赋值 `self.xxx =`、类型注解 `: YYY`）

### 新建文件
- `src/harness_governance/state_machine/alignment.py` — `FieldAlignmentEngine`
  - `extract_specs(contract_file)` → `list[FieldAlignmentSpec]`（正则解析 markdown 表格、JSON schema）
  - `scan_implementation(source_files, specs)` → `list[AlignmentFinding]`（Python 用 `ast` 模块，非 Python 返回空并标记 unsupported）
  - `compute_alignment(from_layer, to_layer, ...)` → `AlignmentReport`
  - `build_traceability_matrix(session, project_root)` → `TraceabilityMatrix`
- `src/harness_governance/commands/alignment.py` — Click 命令组：`check`, `trace`
- 对应测试文件

### 新增模型 (schemas.py)
- `FieldAlignmentSpec` — field_name, field_type, is_required, source_contract
- `AlignmentFinding` — contract_field vs implementation_field, severity, issue 类型（missing|renamed|type_mismatch|extra_field|required_missing）
- `AlignmentReport` — fields_expected, fields_matched, findings, passed, unsupported_languages（非 Python 项目时非空，gate 降级为 warning）
- `TraceabilityMatrix` / `TraceabilityEntry` — 跨层字段映射：contract→architecture→adr→implementation→verification

### 门禁变更
- CONTRACT 门禁：`required_artifacts` 增加 `".harness/alignment/contract-implementation.ndjson"`（信息性，对齐骨架可能尚不存在）；确认项增加字段可追溯性要求
- IMPLEMENTATION 门禁：确认项增加"所有契约字段均匹配实现字段（对齐检查通过）"、"无超出契约范围的额外公开字段"；**钩子负责调用 `compute_alignment()` 生成完整报告并校验**——对齐 NDJSON 不进入 `blocking_artifacts`

**对齐报告生成触发点**（修订）：
1. **CONTRACT 层**：用户回答完契约 Q&A 后，CONTRACT gate 钩子提取契约字段规格（只读，不写文件），校验规格格式完整性
2. **IMPLEMENTATION 层**：IMPLEMENTATION gate 钩子调用 `compute_alignment()` 动态生成完整对齐报告（契约 + 实现两侧），然后检查 mismatches → 失败消息写入 `confirmation_items_unmet`。**不依赖预存文件**。
3. CLI 手动触发：`harness alignment check` 随时可运行，生成报告供人工审查

---

## 缺口 3：功能粒度 / 漂移防护

**问题**：漂移防护仅存在于提示词层面。没有范围边界强制执行，没有自动分解触发，没有程序化检测实现是否超出契约。

**核心思路**：通过 `git diff` 获取实际变更文件列表，与声明的范围边界（ScopeBoundary）比较，超限时触发分解建议。新增 T10 转换规则，当检测到范围漂移时阻止进入 IMPLEMENTATION。

### 新建文件
- `src/harness_governance/state_machine/drift.py` — `DriftDetectionEngine`
  - `declare_scope(project_root, scope)` → 写入 `.harness/scopes/<change_id>.json`
  - `check_boundary(project_root, change_id, base_ref)` → `DriftDetection`（基于 `git diff --name-only --stat`）
    - `base_ref` 语义：当前分支与目标分支的 merge-base，由 `git merge-base HEAD <default-branch>` 计算。如果无法确定 merge-base（如浅克隆），回退到 `HEAD~1`。如果 `HEAD~1` 也不存在（初始 commit、depth=1 浅克隆），回退到 git 空树 hash `4b825dc642cb6eb9a060e54bf899d4e3c6e2c3a8`（与空树 diff 等价于 `git diff --name-only HEAD`）。调用方可以通过 CLI `--base-ref` 覆盖。`resolve_diff_base()` 抽取为独立函数以便测试和复用。
  - `detect_decomposition_trigger(drift, boundary)` → `list[DecompositionTrigger]`
- `src/harness_governance/commands/drift.py` — Click 命令组：`check`, `scope`, `boundary`
- 对应测试文件

### 新增模型 (schemas.py)
- `ScopeBoundary` — max_files, max_lines_per_file, max_total_lines, allowed_paths, forbidden_paths；提供 `for_tier(RigorTier)` 按严格等级设置默认阈值
- `DecompositionTrigger` — triggered_by, threshold, actual, recommendation
- `DriftDetection` — planned_files vs actual_files_changed, files_out_of_scope, triggers_decomposition
- `ScopeDeclaration` — 持久化到 `.harness/scopes/<change_id>.json`

### 新转换规则 T10
在 `transitions.py` 中新增：
```python
TransitionRule(
    code="T10-DRIFT-CONTRACT-BOUNDARY",
    title="范围漂移必须先回到契约层才能扩展",
    rule="当实现触碰了已批准范围边界之外的文件或行为时，"
         "必须先回到 `contract` 扩展契约，再继续实现。",
    target_layer=HarnessLayer.IMPLEMENTATION,
)
```
`TransitionContext`（`engine.py:25`，`@dataclass(frozen=True, slots=True)`）增加：
```python
scope_drift_detected: bool = False
```
**验证清单**：
- `__slots__` 随 `slots=True` 自动生成，只需加字段定义。
- 同步更新 docstring（第 29-64 行）增加 `scope_drift_detected` 的条目。
- 2 个生产构造点（`check.py:102`，`layer.py:195`）均使用显式关键字参数，新字段有默认值，无需修改。
- 测试文件 `test_transitions.py` 和 `test_engine_t6.py` 共 22 处 `TransitionContext(` 构造，均为显式关键字参数，无需修改。
- 在 `engine.py` 中参照 T7 模式（`implementation_reveals_uncontracted_behavior`）实现 T10 评估逻辑。插入位置：`evaluate()` 方法中 T9 检查之后，检查 `scope_drift_detected is True` 且 `to_layer is IMPLEMENTATION` 时产生 violation。

### 门禁变更
- READINESS 门禁：增加范围边界声明和粒度确认项
- IMPLEMENTATION 门禁：增加"无超出声明边界的范围漂移"、"所有实际文件变更均匹配计划范围"

### SubagentResult 变更
- 增加 `actual_scope: list[str]` 和 `scope_violations: list[str]`

---

## 缺口 4：技术栈版本管理

**问题**：只有自身版本追踪。当 harness 向用户确认技术栈时，不捕获具体版本号。当实现过程中引入新工具时，没有版本确认门禁。更关键的是三个缺失：
1. 每种语言应该用什么 **lint 工具**没有确认（Java 用 checkstyle 还是 spotbugs？JS 用 eslint 还是 biome？C# 用 StyleCop 还是 Roslyn？）
2. 每种语言应该用什么 **代码注释/文档规范**没有确认（Python 用 Google docstring 还是 Sphinx？Java 用 Javadoc 还是无要求？JS 用 JSDoc 还是 TSDoc？）
3. 引入新工具时没有要求锁定版本

**核心思路**：自动检测项目中的语言运行时、包管理器、框架、开发工具及其版本，持久化到 `.harness/tech-stack.json`。内置两个目录——**lint 工具目录**和**文档注释风格目录**——检测到项目语言后必须在 INTAKE_ORIENTATION 阶段让用户逐一确认。引入新工具时必须指定版本并获得确认（`confirmed=True`），否则门禁不通过。

### 内置 Lint 工具目录（`LINT_TOOL_CATALOG`）

按语言分类，每项包含：工具名、常见配置文件、可检测标志。

| 语言 | 可选 Lint 工具 | 配置文件检测 |
|------|---------------|-------------|
| **Python** | ruff, flake8, pylint, black, mypy | `[tool.ruff]`, `.flake8`, `.pylintrc`, `pyproject.toml` |
| **JavaScript/TypeScript** | eslint, prettier, biome, oxlint | `.eslintrc.*`, `.prettierrc.*`, `biome.json`, `oxlintrc.json` |
| **Java** | checkstyle, spotbugs, pmd, sonarlint | `checkstyle.xml`, `spotbugs-exclude.xml`, `pmd-ruleset.xml` |
| **Kotlin** | detekt, ktlint | `detekt.yml`, `.editorconfig` (ktlint) |
| **C#** | StyleCop, Roslyn analyzers, dotnet-format | `.stylecop.json`, `.editorconfig`, `Directory.Build.props` |
| **Go** | golangci-lint, staticcheck, gofmt | `.golangci.yml`, `staticcheck.conf` |
| **Rust** | clippy, rustfmt | `Cargo.toml` (`[lints]`), `rustfmt.toml` |
| **Ruby** | rubocop, standard | `.rubocop.yml`, `.standard.yml` |
| **Swift** | swiftlint | `.swiftlint.yml` |
| **C/C++** | clang-tidy, cppcheck, clang-format | `.clang-tidy`, `.clang-format`, `cppcheck.cfg` |
| **Shell** | shellcheck, shfmt | `.shellcheckrc` |
| **Docker** | hadolint | `.hadolint.yaml` |
| **通用** | editorconfig, pre-commit | `.editorconfig`, `.pre-commit-config.yaml` |

### 内置文档注释风格目录（`DOC_STYLE_CATALOG`）

每种语言对应一种或多种文档注释规范。检测到项目语言后，必须确认使用哪种风格。

| 语言 | 文档注释风格 | 格式示例 | 常见工具/配置 |
|------|------------|---------|-------------|
| **Python** | Google docstring, NumPy docstring, Sphinx reST, PEP 257 (plain) | `"""Args:\n    name: ...\n"""` | pydocstyle, interrogate, sphinx |
| **Java** | Javadoc, no-doc-required | `/** @param name ... */` | checkstyle (javadoc rules), spotbugs |
| **JavaScript/TypeScript** | JSDoc, TSDoc, no-doc-required | `/** @param {string} name */` | eslint-plugin-jsdoc, typedoc |
| **C#** | XML doc comments (///), no-doc-required | `/// <param name="x">...</param>` | StyleCop (SA16xx rules), DocFX |
| **Go** | godoc, no-doc-required | `// Package x ...` / `// FuncName does ...` | golangci-lint (revive), go doc |
| **Rust** | doc comments (///), no-doc-required | `/// Brief summary.\n///\n/// # Panics` | clippy (missing_docs), rustdoc |
| **Ruby** | YARD, RDoc, no-doc-required | `# @param name [String] ...` | rubocop (Documentation), yard |
| **Kotlin** | KDoc, no-doc-required | `/** @param name ... */` | detekt (comments rules), dokka |
| **Swift** | DocC markup, no-doc-required | `/// Brief summary.\n/// - Parameter name: ...` | swiftlint (missing_docs) |
| **C/C++** | Doxygen, no-doc-required | `/** @param name ... */` | clang-tidy, cppcheck |
| **Shell** | header-comment, no-doc-required | `# Usage: ...` | shellcheck (无专门规则) |
| **SQL** | header-comment, no-doc-required | `-- Purpose: ...` | 无专用工具 |
| **通用** | README-only, inline-only, or strict-every-public | — | — |

关键设计点：
- 每种语言默认 `no-doc-required` 需要用户显式选择才变为强制
- 选择了某种 doc 风格后，对应的 lint 工具应配置对应的文档检查规则
- doc 风格的选择应联动 lint 工具配置（例如选了 Google docstring → ruff 启用 `pydocstyle` 规则）

### 新建文件
- `src/harness_governance/state_machine/tech_stack.py` — `TechStackManager`
  - `capture(project_root)` → `TechStackManifest`（解析 pyproject.toml, package.json, go.mod 等 + 执行 `tool --version`）
  - `check(project_root)` → `TechStackCheckResult`
  - `introduce_tool(project_root, tool_name, version, rationale, session_id)` → `ToolIntroduction(confirmed=False)`
  - `confirm_tool(project_root, tool_name)` → 标记为已确认
  - `detect_unexpected(project_root)` → 发现未注册工具
  - `detect_project_languages(project_root)` → `list[str]` — 扫描文件扩展名统计判断项目语言
  - `suggest_lint_tools(language)` → `list[str]` — 根据语言从 `LINT_TOOL_CATALOG` 推荐 lint 工具
  - `suggest_doc_styles(language)` → `list[str]` — 根据语言从 `DOC_STYLE_CATALOG` 推荐文档注释风格
  - `detect_configured_lints(project_root)` → `dict[str, tuple[str, str | None]]` — 扫描配置文件，返回 `{language: (config_path, detected_version)}`，未检测到版本则 version 为 None
  - `detect_existing_doc_style(project_root, language)` → `str | None` — 扫描源码文件推断现有注释风格
  - `require_lint_confirmation(project_root, manifest)` → `list[LintGap]` — 找出有语言但没确认 lint 工具的情况
  - `require_docstyle_confirmation(project_root, manifest)` → `list[DocStyleGap]` — 找出有语言但没确认文档注释风格的情况
- `src/harness_governance/commands/tech_stack.py` — Click 命令组：`capture`, `check`, `add`, `show`, `lint`, `docstyle`
- 对应测试文件

### 新增模型 (schemas.py)
- `VersionConstraint` — tool_name, declared_version, detected_version, constraint_type（exact|range|unpinned）, is_satisfied, **tool_category**（language|package_manager|framework|dev_tool|lint|formatter|doc|security）
- `ToolIntroduction` — tool_name, version, introduced_by, confirmed（默认 False）, confirmation_method, **tool_category**
- `LintGap` — language, suggested_tools, detected_config（已检测到的配置文件路径，如 `".eslintrc.json"`，`None` 表示未检测到任何配置）, detected_version（从配置文件推断的版本，`None` 表示无法确定）, selected_tool（空=未选）, confirmed（False 直到用户确认）
- `DocStyleGap` — 新模型：language, suggested_styles（如 `["Google docstring", "Sphinx reST", "NumPy docstring", "no-doc-required"]`）, selected_style（空=未选）, detected_style（从现有代码推断的结果）, confirmed（False 直到用户确认）
- `TechStackManifest` — languages, package_managers, frameworks, dev_tools, **lint_tools（新增）**, **formatters（新增）**, **doc_styles（新增：`dict[str, str]` — `{language: doc_style}`）**, introduced_tools；持久化到 `.harness/tech-stack.json`
- `TechStackCheckResult` — passed, violations, new_tools_pending_confirmation, unchecked_tools, **lint_gaps（未确认 lint 工具的语言列表）**, **doc_style_gaps（未确认文档注释风格的语言列表）**

### 关键用户交互行为

**场景 A：harness init 时**
1. 自动检测项目语言（扫描文件扩展名：`.py`→Python, `.java`→Java, `.ts`→TypeScript 等）
2. 对每种检测到的语言：
   a. 扫描是否已有 lint 配置
   b. 扫描现有代码中的注释风格（推断 doc style）
3. 如果已有配置 → 自动捕获工具名+版本+风格到 manifest
4. 如果没有 lint 配置 → 提示："检测到项目使用 `<语言>`，但未配置 lint 工具。推荐：`<建议列表>`。请选择或指定："
5. 如果没有明确的 doc 注释风格 → 提示："检测到项目使用 `<语言>`，请确认代码文档注释规范。推荐：`<建议列表>`。请选择："
6. 用户选择后记录 `LintGap(selected_tool=..., confirmed=True)` 和 `DocStyleGap(selected_style=..., confirmed=True)`

**场景 B：harness governed-start 时（INTAKE_ORIENTATION 层）**
1. 加载 `TechStackManifest`
2. 调用 `require_lint_confirmation()` 和 `require_docstyle_confirmation()` 检查每门语言是否二者都已确认
3. 如果有 `LintGap`（语言存在但 lint 未确认）：
   - 询问："项目使用 `<语言>`，编码规范工具尚未确认。推荐：`<建议列表>`。请确认要使用哪个工具及版本？"
4. 如果有 `DocStyleGap`（语言存在但 doc 注释风格未确认）：
   - 询问："项目使用 `<语言>`，代码文档注释规范尚未确认。可选：`<选项列表>`。请确认使用哪种风格？"
   - 这两个作为 INTAKE_ORIENTATION 门禁的必答问题
5. 门禁在每种语言的 lint + doc style 都 `confirmed=True` 之前不会通过

**场景 C：实现过程中引入新工具**
1. `harness tech-stack check` 检测到未经注册的新工具（包括新的 lint/doc 工具）
2. 阻止继续，直到通过 `harness tech-stack add <tool> --version X.Y.Z --category lint` 确认
3. 如果是新语言引入的 lint/doc 工具，自动关联到对应语言

### 新增 CLI 子命令
- `harness tech-stack lint` — 列出所有语言的 lint 工具状态
- `harness tech-stack lint <language>` — 查看/设置特定语言的 lint 工具
- `harness tech-stack lint <language> --tool eslint --version 8.56.0` — 确认该语言的 lint 工具及版本
- `harness tech-stack docstyle` — 列出所有语言的文档注释风格状态
- `harness tech-stack docstyle <language>` — 查看/设置特定语言的 doc 注释风格
- `harness tech-stack docstyle <language> --style "Google docstring"` — 确认该语言的文档注释规范

### init.py 集成
`harness init` 时自动捕获技术栈（`--minimal` 模式除外），包括：
1. 检测项目语言
2. 扫描已有 lint 配置
3. 对缺失的 lint 工具发出提醒（不阻塞 init，但会在 INTAKE_ORIENTATION 门禁时拦截）

### 门禁变更
- INTAKE_ORIENTATION 门禁：`required_questions` 增加两条：
  - **"项目使用哪些编程语言？每种语言的 lint/编码规范工具是否已确认？"**
  - **"每种语言的代码文档注释规范是否已确认（docstring / Javadoc / JSDoc / XML doc 等）？"**
  确认项增加：
  - "技术栈版本已捕获并确认"
  - "未检测到未注册工具"
  - **"每种项目语言均已指定 lint 工具及版本"**
  - **"每种项目语言均已指定文档注释风格"**
  - **"lint 配置文件与文档注释风格一致（如选 Google docstring → lint 启用 pydocstyle 规则）"**
- READINESS 门禁：确认项增加：
  - "技术栈版本检查通过（与清单无漂移）"
  - "所有新工具引入已获作者确认"
  - **"所有 lint 工具版本已锁定，编码规范可执行"**
  - **"所有文档注释规范已确认，可由 lint/CI 自动检查"**

---

## 缺口 5：技能调用链

**问题**：调用日志只追踪执行回合，不追踪技能到技能的溯源关系。没有父子关系记录、没有调用树可视化、没有审计追踪显示哪个技能生成了哪个子代理。

**核心思路**：每次技能调用生成唯一 call_id，记录 parent_call_id 形成调用树。每次回合结束时追加 NDJSON 记录。提供 ASCII 树/Mermaid 图可视化。在 VERIFICATION 和 REVIEW_NEXT 门禁处校验调用链完整性。

### 新建文件
- `src/harness_governance/state_machine/skill_chain.py` — `SkillChainTracer`
  - `start_invocation(parent_call_id, child_skill, role, ...)` → 返回新 call_id（基于 UUID）
  - `end_invocation(call_id, exit_code, verdict, files_returned)` → 补全记录
  - `record_full_invocation(invocation)` → 追加 NDJSON
  - `build_tree(session_id)` → `InvocationTreeNode`（递归结构）
  - `compute_report(session_id)` → `SkillChainReport`
  - `validate_chain_integrity(session_id)` → 检测孤儿节点、环、不完整调用
- `src/harness_governance/commands/skill_chain.py` — Click 命令组：`trace`, `visualize`, `inspect`
- 对应测试文件

### 新增模型 (schemas.py)
- `SkillInvocation` — call_id, parent_call_id, parent_skill, child_skill, role, session_id, layer, round_index, files_passed, files_returned, started_at, finished_at, duration_seconds, exit_code, verdict, trace_depth（0=根节点）
- `InvocationTreeNode` — 递归树节点：call_id, skill, role, duration_s, verdict, children
- `SkillChainReport` — total_invocations, max_depth, unique_skills, longest_chain, orphan_invocations, tree

### 修改文件
- `runner/result_parser.py` — `SubagentResult` 增加 `parent_skill`, `skill_call_id`, `parent_call_id`，新增 `generate_call_id()` 静态方法
- `runner/loop.py` — 在 `_execute_queue_item()` 返回后、`_record_round()` 之前调用 `SkillChainTracer.record_full_invocation()`；`parent_call_id` 从 queue item 的 `metadata` 中获取（由编排器在分发时写入），根节点（首次调用）的 `parent_call_id` 为 `None`

### 门禁变更
- VERIFICATION 门禁：`blocking_artifacts` 增加 `".harness/skill-chains/*.ndjson"`；确认项增加"技能调用链完整性已验证（无孤儿节点）"、"所有子代理结果已链接到父技能调用"
- REVIEW_NEXT 门禁：确认项增加"完整技能调用链已归档供审计"、"调用树已生成并验证"

### 可视化
- `harness skill-chain visualize --format mermaid` → 输出可嵌入 markdown 的 Mermaid 流程图
- `harness skill-chain trace <skill>` → 终端 ASCII 树

---

## 跨切面关注点

### NDJSON 写入并发安全

三个缺口模块写入 NDJSON 日志（isolation 的 `.isolation.ndjson`、skill_chain 的调用链日志、drift 检测可能追加事件）。如果多个子代理并行运行，同时追加同一 NDJSON 文件会导致交错写入损坏。

**解决方案**：在 `src/harness_governance/file_ops/` 下新增 `ndjson_writer.py`，提供 `NDJSONWriter` 类：
- `append(path: Path, record: dict)` — 使用 `msvcrt.locking`（Windows）或 `fcntl.flock`（Unix）对文件加排他锁后追加一行 JSON
- 锁超时 5 秒，超时后重试一次
- 三个缺口模块统一使用 `NDJSONWriter` 而非自行 `open().write()`

### 缺口 5 技能链 NDJSON 存储路径

方案缺口 5 未指定 NDJSON 文件位置。统一路径：`.harness/skill-chains/<session_id>.ndjson`。`SkillChainTracer` 构造函数接收 `session_id` 和 `project_root`，自动解析路径。

### 缺口 1 `check_violations` 的角色范围来源

`IsolationManager.check_violations(role, files_touched)` 需知道每个角色的合法路径范围。`IsolationWorkspace` 模型增加：
- `allowed_paths: list[str]` — glob pattern 列表（如 `["src/**/*.py", "tests/**/*.py"]`）
- `allowed_roles: list[str]` — 允许协作的角色列表（如 planner 可以读取 contract-writer 产物）

范围由 orchestrator 在角色确定时写入 `IsolationWorkspace`，`check_violations` 据此判断。初始版本使用 glob 匹配；后续可扩展为 CODEOWNERS 风格。

### `LintGap` 模型与 `DocStyleGap` 的对等性

`DocStyleGap` 有 `detected_style: str | None`（从现有代码推断的结果），但 `LintGap` 缺少对应的 `detected_config: str | None`（已检测到的配置文件路径）。补齐：
- `LintGap` 增加 `detected_config: str | None` — 存储检测到的配置文件路径（如 `".eslintrc.json"`），`None` 表示未检测到任何配置
- `detect_configured_lints()` 返回类型从 `dict[str, str]` 改为 `dict[str, tuple[str, str | None]]`——`{language: (config_path, detected_version)}`

这样交互行为一致：用户看到的不是空白选择，而是"检测到 `.eslintrc.json`（eslint v8.56.0），是否确认？"

### `SubagentResult` 多缺口字段协调

缺口 1（`isolation_workspace`, `isolation_violations`）、缺口 3（`actual_scope`, `scope_violations`）、缺口 5（`parent_skill`, `skill_call_id`, `parent_call_id`）都需要向 `SubagentResult`（`runner/result_parser.py`，当前 22 字段的 `@dataclass(slots=True)`）添加字段。

**不要分 3 次修改同一文件**。在步骤 0（Gate 引擎增强）中一次性为 `SubagentResult` 添加所有 7 个新字段（均为带默认值的可选字段），后续各缺口直接使用。这样：
- 避免重复编辑同一 dataclass 造成的合并冲突
- 所有字段默认 `None`/空列表，未使用的缺口不受影响
- 各缺口的测试可以独立 mock 自己需要的字段

---

## 构建顺序（按依赖关系）

0. **Gate 引擎增强 + 全局基础设施（前置条件）** — 一次性完成以下四项，所有 5 个缺口依赖：
   - `LayerGateDefinition` 增加 `blocking_artifacts` 字段（与现有 `required_artifacts` 分离，避免死锁）
   - `LayerGateEngine.check()` 改为 `blocking_artifacts` 缺失时阻塞 + `GATE_HOOK_REGISTRY` 钩子注册表
   - `SubagentResult` 批量增加 7 个新字段（缺口 1/3/5 所需，全部带默认值）
   - `NDJSONWriter` 工具类（含文件锁）
1. **缺口 4（技术栈）** — 无依赖；init 集成是单向写入，逻辑独立
2. **缺口 1（隔离）** — 轻量依赖编排器；被缺口 3 需要
3. **缺口 3（漂移）** — 依赖隔离模块的文件追踪；新增 T10 规则
4. **缺口 2（对齐）** — 可复用漂移模块的 git diff 逻辑；建立在 T7/T10 模式之上
5. **缺口 5（技能链）** — 步骤 0 已批量添加所有 `SubagentResult` 字段，不再依赖缺口 1/3；可独立实施或与缺口 1-4 任意并行。唯一约束：需在步骤 0 完成后开始

每步执行：加模型 → 加引擎 → 加 CLI → 集成门禁 → 加测试 → 跑全量。

## 版本升级清单

- `src/harness_governance/__init__.py`: `__version__ = "0.8.0"`
- `pyproject.toml`: version = "0.8.0"
- `CHANGELOG.md`: 新增 `## [0.8.0] - Unreleased` 条目（发布日期在发版时填入）
- 24 个技能模板文件：更新 `<!-- harness-skill-version: 0.7.1 -->` → `0.8.0`
- `CLAUDE.md`: 更新版本引用

## 验证方式

1. **单元测试**: `pytest tests/test_state_machine/test_isolation.py test_alignment.py test_drift.py test_tech_stack.py test_skill_chain.py -x --tb=short`
2. **CLI 冒烟测试**: 每个新命令组 `--help` 正常输出
3. **门禁集成**: `harness gate check <layer>` 对 6 个修改过的层进行检查（INTAKE_ORIENTATION、CONTRACT、READINESS、IMPLEMENTATION、VERIFICATION、REVIEW_NEXT）
4. **全量测试**: `pytest tests/ -x --tb=short`（预期约 1270-1320 个测试）
5. **狗粮测试**: 对 harness-governance 自身运行 `harness governed-start "add isolation" --rigor strict`，验证新门禁生效
