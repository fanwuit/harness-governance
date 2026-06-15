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

    agent_platform: Literal["claude-code", "codex", "cline", "cursor", "qoderwork", "generic"] = "claude-code"
    project_root: Path = Field(default_factory=Path.cwd)
    queue_file: Path = Path("NEXT.md")
    changes_root: Path = Path("docs/changes")
    planning_root: Path = Path(".planning")
    harness_dir: Path = Path(".harness")
    entry_block_marker: str = "Implementation Entry Record"
    blocked_statuses: tuple[str, ...] = ("blocked", "archived")
    check_frequency: Literal["targeted", "phase-closeout", "always"] = "targeted"

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


class RoutingResult(BaseModel):
    """Output of ``harness governed-start``."""

    model_config = ConfigDict(extra="forbid")

    path: RoutingPath
    rationale: str
    current_layer: HarnessLayer | None = None
    primary_skill: str | None = None
    disclosure: str
    recommended_next_command: str


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
