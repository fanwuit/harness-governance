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

    agent_platform: Literal["claude-code", "codex", "cline", "generic"] = "claude-code"
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


class StatusView(BaseModel):
    """Aggregate dashboard view emitted by ``harness status``."""

    model_config = ConfigDict(extra="forbid")

    project_root: Path
    queue_path: Path | None
    queue_items: tuple["QueueItem", ...] = ()
    packets: tuple[ChangePacketSummary, ...] = ()
    active_plan: PlanningSession | None = None
    checkpoint_present: bool = False


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


StatusView.model_rebuild()