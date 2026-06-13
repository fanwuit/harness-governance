"""Abstract AgentExecutor for the autonomous runner."""

from __future__ import annotations

import abc
from dataclasses import dataclass, field


# Markers the runner looks for in worker output to decide what to do.
AUTONOMOUS_READY_DONE = "AUTONOMOUS_READY_DONE"
AUTONOMOUS_BLOCKED = "AUTONOMOUS_BLOCKED"
AUTONOMOUS_BOUNDARY_REACHED = "AUTONOMOUS_BOUNDARY_REACHED"
AUTONOMOUS_FAILED = "AUTONOMOUS_FAILED"
AUTONOMOUS_CONTEXT_HANDOFF = "AUTONOMOUS_CONTEXT_HANDOFF"


@dataclass(slots=True)
class ExecutionResult:
    """Outcome of one agent turn."""

    exit_code: int
    stdout: str = ""
    stderr: str = ""
    marker: str | None = None
    duration_seconds: float = 0.0
    verification_summary: str | None = None
    metadata: dict[str, str] = field(default_factory=dict)

    @property
    def succeeded(self) -> bool:
        return self.exit_code == 0


class AgentExecutor(abc.ABC):
    """Pluggable interface for running one agent turn."""

    @abc.abstractmethod
    def execute(
        self,
        prompt: str,
        *,
        timeout_seconds: int = 1800,
        round_label: str = "",
    ) -> ExecutionResult:
        """Run ``prompt`` against the agent and return the outcome."""
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """A short identifier (e.g., ``subprocess``, ``codex``)."""
        raise NotImplementedError


def detect_marker(output: str) -> str | None:
    """Scan worker output for one of the AUTONOMOUS_* markers."""
    for marker in (
        AUTONOMOUS_BOUNDARY_REACHED,
        AUTONOMOUS_BLOCKED,
        AUTONOMOUS_FAILED,
        AUTONOMOUS_READY_DONE,
        AUTONOMOUS_CONTEXT_HANDOFF,
    ):
        if marker in output:
            return marker
    return None


def detect_verification_summary(output: str) -> str | None:
    """Pull a ``- pytest: …`` / ``pytest -> pass`` style line if present."""
    for line in output.splitlines():
        stripped = line.strip().lstrip("-").strip()
        if any(stripped.startswith(prefix) for prefix in ("pytest", "npm test", "python -m pytest", "go test", "cargo test")):
            return stripped[:200]
    return None


__all__ = [
    "AgentExecutor",
    "ExecutionResult",
    "detect_marker",
    "detect_verification_summary",
    "AUTONOMOUS_READY_DONE",
    "AUTONOMOUS_BLOCKED",
    "AUTONOMOUS_BOUNDARY_REACHED",
    "AUTONOMOUS_FAILED",
    "AUTONOMOUS_CONTEXT_HANDOFF",
]