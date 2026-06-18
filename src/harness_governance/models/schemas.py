"""Pydantic v2 schemas for harness-governance CLI I/O.

The schemas are the single source of truth for the JSON serialization
contract of every command. Command modules construct these models and
emit them via the ``--json`` flag where supported.

All models use ``model_config = ConfigDict(extra="forbid")`` to catch
typos in hand-written config files and CLI payloads.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ..state_machine.classification import RoutingPath
from ..state_machine.layers import HarnessLayer


class HarnessConfig(BaseModel):
    """``.harness/config.toml`` schema (loaded by ``config.settings``)."""

    model_config = ConfigDict(extra="forbid")

    schema_version: int = 1
    agent_platform: Literal[
        "claude-code",
        "codex",
        "cline",
        "cursor",
        "opencode",
        "windsurf",
        "qoderwork",
        "generic",
        "multi",
    ] = "claude-code"
    project_root: Path = Field(default_factory=Path.cwd)
    queue_file: Path = Path("NEXT.md")
    changes_root: Path = Path("docs/changes")
    planning_root: Path = Path(".planning")
    harness_dir: Path = Path(".harness")
    entry_block_marker: str = "Implementation Entry Record"
    blocked_statuses: tuple[str, ...] = ("blocked", "archived")
    check_frequency: Literal["targeted", "phase-closeout", "always"] = "targeted"
    require_session: bool = True
    scope_budget: ScopeBudget = Field(
        default_factory=lambda: ScopeBudget(max_files=10, max_diff_lines=800)
    )

    @field_validator("project_root")
    @classmethod
    def _absolutize(cls, value: Path) -> Path:
        return value if value.is_absolute() else Path.cwd() / value


class RoutingInput(BaseModel):
    """Inputs to :func:`state_machine.classify` exposed as a CLI flag bag."""

    model_config = ConfigDict(extra="forbid")

    description: str
    has_file_changes: bool = False
    is_public_contract: bool = False
    has_external_side_effect: bool = False
    is_unclear_or_high_risk: bool = False
    companion_skills: tuple[str, ...] = ()
    rigor_tier: str | None = None  # explicit --rigor override (light/standard/strict)


class RoutingResult(BaseModel):
    """Output of ``harness governed-start``."""

    model_config = ConfigDict(extra="forbid")

    path: RoutingPath
    rationale: str
    current_layer: HarnessLayer | None = None
    primary_skill: str | None = None
    disclosure: str
    recommended_next_command: str
    skill_version_warning: str | None = None
    rigor_tier: str | None = None  # resolved rigor tier for this session


class ChangePacketSummary(BaseModel):
    """Lightweight summary of a packet for status/dashboard output."""

    model_config = ConfigDict(extra="forbid")

    change_id: str
    path: Path
    status: str = "draft"
    blocking_layer: HarnessLayer | None = None
    missing_files: tuple[str, ...] = ()


class ChangePacketInitResult(BaseModel):
    """Output of ``harness packet init``."""

    model_config = ConfigDict(extra="forbid")

    change_id: str
    packet_dir: Path
    created_files: tuple[str, ...]
    today: date


class CheckFinding(BaseModel):
    """One finding produced by a ``harness check`` subcommand."""

    model_config = ConfigDict(extra="forbid")

    check: str
    target: str
    level: Literal["error", "warning", "info"] = "error"
    message: str


class CheckResult(BaseModel):
    """Aggregate result of one ``harness check`` invocation."""

    model_config = ConfigDict(extra="forbid")

    check: str
    passed: bool
    findings: tuple[CheckFinding, ...] = ()
    inspected: int = 0


class EntryRecord(BaseModel):
    """Parsed ``Implementation Entry Record`` block.

    The block is an inline Markdown section in chat or a status file.
    Field names match the headers documented in
    ``governed-implementation-entry/SKILL.md``.
    """

    model_config = ConfigDict(extra="forbid")

    current_layer: HarnessLayer
    target: str
    scope: str
    contract_evidence: str
    readiness_gate: str
    packetization: str
    verification_command: str
    review_next_state: str
    stop_conditions: str

    @field_validator("stop_conditions")
    @classmethod
    def _stop_conditions_non_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("stop_conditions must not be empty")
        return value


class PlanningSession(BaseModel):
    """In-memory representation of ``.planning/<id>/``."""

    model_config = ConfigDict(extra="forbid")

    plan_id: str
    plan_dir: Path
    task_plan_path: Path
    findings_path: Path
    progress_path: Path
    attested: bool = False
    attestation_sha256: str | None = None


class ScopeBudget(BaseModel):
    """Per-task scope budget carried in a NEXT.md ``[ready]`` block.

    Constrains how large a single task may grow before the runner forces
    a checkpoint or decomposition.  All fields default to ``0`` (unlimited)
    so that existing queue entries without a ``Scope:`` line continue to
    work without changes.
    """

    model_config = ConfigDict(extra="forbid")

    max_files: int = 0
    max_diff_lines: int = 0
    forbidden_paths: tuple[str, ...] = ()
    owner_files: tuple[str, ...] = ()


class QueueItem(BaseModel):
    """One entry of ``NEXT.md``.

    Field names mirror the markdown headings used by the existing
    fixtures: ``Layer:``, ``Change:``, ``Packetization:``, ``Evidence:``.
    """

    model_config = ConfigDict(extra="forbid")

    raw: str
    active: bool = False
    ready: bool = False
    layer: HarnessLayer | None = None
    change_id: str | None = None
    packetization: str | None = None
    evidence: str | None = None
    scope_budget: ScopeBudget | None = None


class StatusQueueItem(BaseModel):
    """Queue item as rendered in the status payload."""

    model_config = ConfigDict(extra="forbid")

    raw: str
    active: bool = False
    ready: bool = False
    layer: str | None = None
    change_id: str | None = None


class StatusQueueSummary(BaseModel):
    """Queue summary counters."""

    model_config = ConfigDict(extra="forbid")

    total: int = 0
    ready: int = 0
    active: int = 0


class StatusPacketItem(BaseModel):
    """Change packet as rendered in the status payload."""

    model_config = ConfigDict(extra="forbid")

    change_id: str
    path: str
    status: str = "draft"


class StatusActivePlan(BaseModel):
    """Active planning session as rendered in the status payload."""

    model_config = ConfigDict(extra="forbid")

    plan_id: str
    attested: bool = False
    task_plan_path: str


class StatusCheckpoint(BaseModel):
    """Checkpoint snapshot for the status payload."""

    model_config = ConfigDict(extra="forbid")

    found: bool = False
    path: str = ""
    last_worker: str = ""
    verification: str = ""
    stop_reason: str = ""


class StatusRunner(BaseModel):
    """Runner stats for the status payload."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    invocation_count: int = Field(default=0, alias="invocationCount")
    last_round: int | None = Field(default=None, alias="lastRound")
    last_exit_code: int | None = Field(default=None, alias="lastExitCode")


class StatusVerification(BaseModel):
    """Verification summary for the status payload."""

    model_config = ConfigDict(extra="forbid")

    summary: str | None = None
    stale: bool = True
    failed: bool = False
    source: str = "missing"


class StatusSessionItem(BaseModel):
    """Governance session as rendered in the status payload."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    status: str = "active"
    current_layer: str | None = None
    description: str = ""
    change_id: str | None = None


# ---------------------------------------------------------------------------
# Rigor tier and gate models (v0.7.0)
# ---------------------------------------------------------------------------


class QAPair(BaseModel):
    """One question/answer exchange recorded in a session."""

    model_config = ConfigDict(extra="forbid")

    layer: str  # HarnessLayer value
    question: str
    answer: str
    timestamp: str  # ISO 8601 UTC


class GateStatus(BaseModel):
    """Result of a :class:`LayerGateEngine` check for one layer."""

    model_config = ConfigDict(extra="forbid")

    layer: str
    passed: bool
    questions_answered: int = 0
    questions_required: int = 0
    artifacts_found: tuple[str, ...] = ()
    artifacts_missing: tuple[str, ...] = ()
    # v0.8.0: blocking artifacts whose absence fails the gate
    blocking_artifacts_missing: tuple[str, ...] = ()
    confirmation_items_met: tuple[str, ...] = ()
    confirmation_items_unmet: tuple[str, ...] = ()
    checked_at: str = ""
    # v0.7.1: wall-clock duration of the gate check in milliseconds
    check_duration_ms: float = 0.0


class GateResult(BaseModel):
    """Aggregate result of ``harness gate check``."""

    model_config = ConfigDict(extra="forbid")

    check: str = "layer-gate"
    layer: str
    passed: bool
    findings: tuple[CheckFinding, ...] = ()
    status: GateStatus | None = None


class RigorProfile(BaseModel):
    """Describes the governance profile for a given rigor tier."""

    model_config = ConfigDict(extra="forbid")

    tier: str  # RigorTier value
    required_layers: tuple[str, ...] = ()
    min_questions_per_layer: dict[str, int] = {}
    auto_interrupt_on_unknowns: bool = False


class GateCheckInput(BaseModel):
    """Input to ``harness gate check`` command."""

    model_config = ConfigDict(extra="forbid")

    layer: str
    session_id: str | None = None


class StatusPayload(BaseModel):
    """Aggregate dashboard emitted by ``harness status``.

    Replaces the legacy :class:`StatusView` (which was too minimal to
    represent the full status JSON contract). Both ``format_text`` and
    ``format_markdown`` accept this model.

    Field aliases preserve the camelCase JSON keys used by the legacy
    ``harness-visualization/scripts/harness-status.mjs`` so downstream
    consumers of ``.harness/status.json`` are not broken.
    """

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    repo: str
    generated_at: str = Field(alias="generatedAt")
    current_layer: str = Field(alias="currentLayer")
    queue_summary: StatusQueueSummary = Field(
        default_factory=StatusQueueSummary, alias="queueSummary"
    )
    queue_items: tuple[StatusQueueItem, ...] = Field(
        default_factory=tuple, alias="queueItems"
    )
    packets: tuple[StatusPacketItem, ...] = ()
    active_plan: StatusActivePlan | None = Field(default=None, alias="activePlan")
    checkpoint: StatusCheckpoint = Field(default_factory=StatusCheckpoint)
    runner: StatusRunner = Field(default_factory=StatusRunner)
    verification: StatusVerification = Field(default_factory=StatusVerification)
    warnings: tuple[str, ...] = ()
    sessions: tuple[StatusSessionItem, ...] = ()


# ---------------------------------------------------------------------------
# v0.8.0 Gap 4 — Tech stack version management
# ---------------------------------------------------------------------------


class VersionConstraint(BaseModel):
    """A single tool version declared by the user or detected on disk."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str
    language: str | None = None
    declared_version: str = ""
    detected_version: str | None = None
    constraint_type: Literal["exact", "range", "unpinned"] = "unpinned"
    is_satisfied: bool = True
    tool_category: Literal[
        "language",
        "package_manager",
        "framework",
        "dev_tool",
        "lint",
        "formatter",
        "doc",
        "security",
    ] = "dev_tool"


class ToolIntroduction(BaseModel):
    """Record of a new tool introduced during implementation."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str
    version: str
    introduced_by: str = ""  # session_id or role
    confirmed: bool = False
    confirmation_method: str = ""  # "cli", "gate-hook", "manual"
    tool_category: str = "dev_tool"


class LintGap(BaseModel):
    """A language that has no confirmed lint tool."""

    model_config = ConfigDict(extra="forbid")

    language: str
    suggested_tools: tuple[str, ...] = ()
    detected_config: str | None = None  # path to detected config file, or None
    detected_version: str | None = None  # version inferred from config, or None
    selected_tool: str = ""
    confirmed: bool = False


class DocStyleGap(BaseModel):
    """A language that has no confirmed documentation comment style."""

    model_config = ConfigDict(extra="forbid")

    language: str
    suggested_styles: tuple[str, ...] = ()
    selected_style: str = ""
    detected_style: str | None = None  # inferred from existing code, or None
    confirmed: bool = False


class TechStackManifest(BaseModel):
    """Complete technology stack snapshot persisted to ``.harness/tech-stack.json``."""

    model_config = ConfigDict(extra="forbid")

    languages: tuple[str, ...] = ()
    package_managers: tuple[str, ...] = ()
    frameworks: tuple[str, ...] = ()
    dev_tools: tuple[VersionConstraint, ...] = ()
    lint_tools: tuple[VersionConstraint, ...] = ()
    formatters: tuple[VersionConstraint, ...] = ()
    doc_styles: dict[str, str] = {}  # {language: doc_style}
    introduced_tools: tuple[ToolIntroduction, ...] = ()
    captured_at: str = ""


class TechStackCheckResult(BaseModel):
    """Result of ``TechStackManager.check()``."""

    model_config = ConfigDict(extra="forbid")

    passed: bool
    violations: tuple[str, ...] = ()
    new_tools_pending_confirmation: tuple[ToolIntroduction, ...] = ()
    unchecked_tools: tuple[str, ...] = ()
    lint_gaps: tuple[LintGap, ...] = ()
    doc_style_gaps: tuple[DocStyleGap, ...] = ()


# ---------------------------------------------------------------------------
# v0.8.0 Gap 1 — Role isolation
# ---------------------------------------------------------------------------


class IsolationWorkspace(BaseModel):
    """A role-specific isolation directory with declared path boundaries."""

    model_config = ConfigDict(extra="forbid")

    role: str
    workspace_path: str  # relative to project root
    isolation_kind: str = "directory"  # "directory" (v0.8.0, detective only)
    session_id: str
    allowed_paths: tuple[str, ...] = ()  # glob patterns
    allowed_roles: tuple[str, ...] = ()  # roles that can be collaborated with
    created_at: str = ""


class IsolationRecord(BaseModel):
    """A single isolation event recorded to ``.isolation.ndjson``."""

    model_config = ConfigDict(extra="forbid")

    event: str  # "workspace_created", "file_accessed", "violation_detected"
    role: str
    workspace_path: str
    session_id: str
    timestamp: str = ""
    files_touched: tuple[str, ...] = ()
    cross_role_accesses: tuple[str, ...] = ()  # roles accessed outside allowed list


class IsolationSummary(BaseModel):
    """Result of ``IsolationManager.verify_workspace()`` for a session."""

    model_config = ConfigDict(extra="forbid")

    roles_isolated: tuple[str, ...] = ()
    cross_role_violations: tuple[IsolationRecord, ...] = ()
    files_outside_scope: tuple[str, ...] = ()
    workspaces_valid: bool = True
    enforcement_level: str = "detective"  # v0.8.0: post-hoc detection, not prevention


# ---------------------------------------------------------------------------
# v0.8.0 Gap 3 — Scope drift protection
# ---------------------------------------------------------------------------


class ScopeBoundary(BaseModel):
    """Declared scope boundary for a change — what files/directories are in play."""

    model_config = ConfigDict(extra="forbid")

    max_files: int = 0
    max_lines_per_file: int = 0
    max_total_lines: int = 0
    allowed_paths: tuple[str, ...] = ()  # glob patterns within scope
    forbidden_paths: tuple[str, ...] = ()  # glob patterns explicitly out of scope

    @classmethod
    def for_tier(cls, tier: str) -> "ScopeBoundary":
        """Return sensible defaults for *tier* (``"strict"``, ``"standard"``, ``"light"``).

        These are soft thresholds — exceeding them triggers a decomposition
        suggestion, not a hard block.  The author can override via
        ``harness drift scope``.
        """
        if tier == "strict":
            return cls(
                max_files=8,
                max_lines_per_file=120,
                max_total_lines=500,
            )
        if tier == "standard":
            return cls(
                max_files=15,
                max_lines_per_file=200,
                max_total_lines=1000,
            )
        # light / default
        return cls(
            max_files=25,
            max_lines_per_file=300,
            max_total_lines=2000,
        )


class ScopeDeclaration(BaseModel):
    """Persisted scope declaration (``.harness/scopes/<change_id>.json``)."""

    model_config = ConfigDict(extra="forbid")

    change_id: str
    session_id: str = ""
    boundary: ScopeBoundary = Field(default_factory=ScopeBoundary)
    declared_files: tuple[str, ...] = ()  # files explicitly listed as in scope
    declared_at: str = ""


class DecompositionTrigger(BaseModel):
    """A recommendation to split work when scope drift is detected."""

    model_config = ConfigDict(extra="forbid")

    triggered_by: str  # e.g. "max_files", "max_total_lines", "forbidden_path"
    threshold: int = 0
    actual: int = 0
    recommendation: str = ""


class DriftDetection(BaseModel):
    """Result of ``DriftDetectionEngine.check_boundary()``."""

    model_config = ConfigDict(extra="forbid")

    planned_files: tuple[str, ...] = ()
    actual_files_changed: tuple[str, ...] = ()
    files_out_of_scope: tuple[str, ...] = ()
    files_in_forbidden_paths: tuple[str, ...] = ()
    lines_added: int = 0
    lines_deleted: int = 0
    triggers_decomposition: tuple[DecompositionTrigger, ...] = ()
    drift_detected: bool = False


# ---------------------------------------------------------------------------
# v0.8.0 Gap 2 — Field alignment
# ---------------------------------------------------------------------------


class FieldAlignmentSpec(BaseModel):
    """A single field specification extracted from a contract document."""

    model_config = ConfigDict(extra="forbid")

    field_name: str
    field_type: str  # e.g. "UUID", "str", "int", "Optional[str]"
    is_required: bool = True
    source_contract: str = ""  # contract file path
    source_line: int = 0  # line number in the contract doc


class AlignmentFinding(BaseModel):
    """One mismatched or missing field between contract and implementation."""

    model_config = ConfigDict(extra="forbid")

    issue: (
        str  # "missing", "renamed", "type_mismatch", "extra_field", "required_missing"
    )
    contract_field: str = ""
    contract_type: str = ""
    implementation_field: str = ""
    implementation_type: str = ""
    severity: str = "error"  # "error" or "warning"
    source_file: str = ""
    source_line: int = 0


class AlignmentReport(BaseModel):
    """Full alignment result between contract and implementation."""

    model_config = ConfigDict(extra="forbid")

    fields_expected: int = 0
    fields_matched: int = 0
    findings: tuple[AlignmentFinding, ...] = ()
    passed: bool = False
    unsupported_languages: tuple[
        str, ...
    ] = ()  # non-empty → gate downgrades to warning
    generated_at: str = ""


class TraceabilityEntry(BaseModel):
    """One field traced across layers."""

    model_config = ConfigDict(extra="forbid")

    field_name: str
    contract_ref: str = ""  # contract file + line
    architecture_ref: str = ""
    adr_ref: str = ""
    implementation_ref: str = ""  # source file + line
    verification_ref: str = ""  # test file + line


class TraceabilityMatrix(BaseModel):
    """Cross-layer field traceability matrix."""

    model_config = ConfigDict(extra="forbid")

    session_id: str = ""
    entries: tuple[TraceabilityEntry, ...] = ()
    fields_total: int = 0
    fields_traced: int = 0
    generated_at: str = ""


# ---------------------------------------------------------------------------
# v0.8.0 Gap 5 — Skill chain tracing
# ---------------------------------------------------------------------------


class SkillInvocation(BaseModel):
    """One skill invocation record in the call tree."""

    model_config = ConfigDict(extra="forbid")

    call_id: str  # UUID hex
    parent_call_id: str | None = None  # None = root node
    parent_skill: str = ""
    child_skill: str = ""
    role: str = ""
    session_id: str = ""
    layer: str = ""
    round_index: int = 0
    files_passed: tuple[str, ...] = ()
    files_returned: tuple[str, ...] = ()
    started_at: str = ""
    finished_at: str = ""
    duration_seconds: float = 0.0
    exit_code: int = 0
    verdict: str = ""  # "success", "failure", "timeout"
    trace_depth: int = 0  # 0 = root


class InvocationTreeNode(BaseModel):
    """Recursive node in a skill invocation tree."""

    model_config = ConfigDict(extra="forbid")

    call_id: str
    skill: str
    role: str = ""
    duration_s: float = 0.0
    verdict: str = ""
    children: tuple["InvocationTreeNode", ...] = ()


class SkillChainReport(BaseModel):
    """Aggregate report of a session's skill invocation chain."""

    model_config = ConfigDict(extra="forbid")

    total_invocations: int = 0
    max_depth: int = 0
    unique_skills: tuple[str, ...] = ()
    longest_chain: tuple[str, ...] = ()  # call_ids along the longest path
    orphan_invocations: tuple[str, ...] = ()  # call_ids with no parent record
    tree: InvocationTreeNode | None = None
    generated_at: str = ""
