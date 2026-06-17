"""Pydantic v2 models for governance session state.

Each governed-path invocation of ``harness governed-start`` creates a
:class:`SessionState` persisted as a JSON file under
``.harness/sessions/<session_id>.json``.  Layer transitions are recorded
as :class:`TransitionRecord` entries so the full governance trajectory
is auditable.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from ..state_machine.classification import RoutingPath
from ..state_machine.layers import HarnessLayer


class TransitionRecord(BaseModel):
    """One layer transition attempt (allowed or blocked)."""

    model_config = ConfigDict(extra="forbid")

    from_layer: HarnessLayer
    to_layer: HarnessLayer
    timestamp: str  # ISO 8601 UTC
    context_flags: dict[str, bool] = {}
    engine_verdict: bool
    violations: tuple[str, ...] = ()
    # v0.7.1: wall-clock seconds spent in from_layer before this transition
    duration_seconds: float = 0.0


class SessionState(BaseModel):
    """Governance session persisted to ``.harness/sessions/<id>.json``."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    created_at: str  # ISO 8601 UTC
    description: str
    routing_path: RoutingPath
    current_layer: HarnessLayer | None = None
    change_id: str | None = None
    companion_skills: tuple[str, ...] = ()
    status: Literal["active", "closed"] = "active"
    closed_at: str | None = None
    transitions: tuple[TransitionRecord, ...] = ()
    # v0.7.0: governance depth controls
    rigor_tier: str = "strict"  # RigorTier value, defaults to STRICT
    layer_qa: tuple[dict[str, Any], ...] = ()  # Q&A log: {"layer","question","answer","timestamp"}


__all__ = [
    "SessionState",
    "TransitionRecord",
]
