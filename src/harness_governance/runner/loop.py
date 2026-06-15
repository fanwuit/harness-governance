"""AutonomousReadyLoop: orchestrates bounded rounds of agent execution.

Mirrors the legacy ``run-autonomous-ready-loop.sh`` semantics:

* Read queue, pick first ``[ready]`` item (or ``[active]`` if no ready).
* Invoke the :class:`AgentExecutor` with the prepared prompt.
* Capture ``AUTONOMOUS_*`` marker from worker output.
* Append an invocation-log entry.
* Write the run checkpoint.
* Stop on boundary, failure, blocked, or after ``max_rounds``.

Two execution modes are supported:

* ``bounded`` (default): ``max_rounds`` is the hard cap (start at 1).
* ``boundary``: ``max_rounds`` is a fuse; the runner stops only when a
  worker emits ``AUTONOMOUS_BOUNDARY_REACHED``, a non-zero exit, or the
  fuse trips. Defaults to 50 rounds.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Literal

from ..logging_setup import get_logger
from ..file_ops.checkpoint import Checkpoint
from ..file_ops.queue import read_queue
from .base import (
    AgentExecutor,
    AUTONOMOUS_BLOCKED,
    AUTONOMOUS_BOUNDARY_REACHED,
    AUTONOMOUS_CONTEXT_HANDOFF,
    AUTONOMOUS_FAILED,
    AUTONOMOUS_READY_DONE,
    ExecutionResult,
)

logger = get_logger("runner.loop")

DEFAULT_MAX_ROUNDS_BOUNDED = 1
DEFAULT_MAX_ROUNDS_BOUNDARY = 50

_RUN_STOP_MARKERS = {
    AUTONOMOUS_BOUNDARY_REACHED,
    AUTONOMOUS_BLOCKED,
    AUTONOMOUS_FAILED,
}


@dataclass(slots=True)
class RoundSummary:
    """One round of execution, persisted to the invocation log."""

    round: int
    queue_item: str
    started_at: str
    finished_at: str
    exit_code: int
    marker: str | None
    command: str
    verification_summary: str | None = None
    duration_seconds: float = 0.0
    stdout_path: str | None = None
    stderr_path: str | None = None

    def to_ndjson(self) -> str:
        return json.dumps(
            {
                "round": self.round,
                "queueItem": self.queue_item,
                "startedAt": self.started_at,
                "finishedAt": self.finished_at,
                "exitCode": self.exit_code,
                "marker": self.marker,
                "command": self.command,
                "verificationSummary": self.verification_summary,
                "durationSeconds": self.duration_seconds,
                "stdoutPath": self.stdout_path,
                "stderrPath": self.stderr_path,
            },
            ensure_ascii=False,
        )


@dataclass(slots=True)
class LoopResult:
    """Final result of :meth:`AutonomousReadyLoop.run`."""

    rounds: int
    stopped_for: Literal["max_rounds", "boundary", "blocked", "failed", "no_ready", "error"]
    invocations: list[RoundSummary] = field(default_factory=list)


class AutonomousReadyLoop:
    """Run bounded/boundary rounds of agent execution."""

    def __init__(
        self,
        *,
        executor: AgentExecutor,
        project_root: Path,
        queue_file: Path,
        checkpoint_file: Path,
        invocation_log: Path,
        prompt_builder,
        timeout_seconds: int = 1800,
        max_retries: int = 0,
        total_timeout_seconds: int | None = None,
    ) -> None:
        self.executor = executor
        self.project_root = project_root.resolve()
        self.queue_file = (self.project_root / queue_file).resolve()
        self.checkpoint_file = (self.project_root / checkpoint_file).resolve()
        self.invocation_log = (self.project_root / invocation_log).resolve()
        self.prompt_builder = prompt_builder
        self.timeout_seconds = timeout_seconds
        self.max_retries = max(0, max_retries)
        self.total_timeout_seconds = total_timeout_seconds

    def run(self, *, mode: Literal["bounded", "boundary"], max_rounds: int) -> LoopResult:
        max_rounds = self._resolve_max_rounds(mode, max_rounds)
        invocations: list[RoundSummary] = []
        stop_for: LoopResult.__annotations__["stopped_for"] = "max_rounds"
        run_started = time.monotonic()

        for round_index in range(1, max_rounds + 1):
            # Total timeout check before starting a new round.
            if self.total_timeout_seconds is not None:
                elapsed = time.monotonic() - run_started
                remaining = self.total_timeout_seconds - elapsed
                if remaining <= 0:
                    logger.warning("total timeout reached after %.1fs (%d round(s))",
                                   elapsed, round_index - 1)
                    stop_for = "error"
                    break

            queue_items = read_queue(self.queue_file)
            ready = next((i for i in queue_items if i.ready), None)
            active = next((i for i in queue_items if i.active), None)
            target = ready or active
            if target is None:
                stop_for = "no_ready"
                break

            started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            started = time.monotonic()
            result: ExecutionResult | None = None
            retry_error: Exception | None = None

            for attempt in range(1, self.max_retries + 2):  # +2 because attempt 1 = first try
                # Per-attempt timeout: respect total budget.
                effective_timeout = self.timeout_seconds
                if self.total_timeout_seconds is not None:
                    remaining = self.total_timeout_seconds - (time.monotonic() - run_started)
                    effective_timeout = max(1, min(int(remaining), self.timeout_seconds))

                try:
                    result = self.executor.execute(
                        self.prompt_builder(target),
                        timeout_seconds=effective_timeout,
                        round_label=f"{round_index}.a{attempt}",
                    )
                except Exception as exc:
                    logger.warning("round %d attempt %d raised %s", round_index, attempt, exc)
                    retry_error = exc
                    if attempt <= self.max_retries:
                        logger.info("retrying round %d (attempt %d/%d)",
                                    round_index, attempt + 1, self.max_retries + 1)
                        continue
                    # All retries exhausted — record as error.
                    stop_for = "error"
                    finished = datetime.now(timezone.utc).isoformat(timespec="seconds")
                    summary = RoundSummary(
                        round=round_index,
                        queue_item=target.raw,
                        started_at=started_at,
                        finished_at=finished,
                        exit_code=1,
                        marker=None,
                        command="<exception>",
                        verification_summary=None,
                        duration_seconds=time.monotonic() - started,
                    )
                    invocations.append(summary)
                    self._append_invocation(summary)
                    self._write_checkpoint(target, result=None, round_index=round_index,
                                           stop_reason=f"error: {exc}")
                    return LoopResult(rounds=len(invocations), stopped_for=stop_for,
                                      invocations=invocations)

                # Success or marker-based stop: no retry needed.
                if result.succeeded or result.marker in _RUN_STOP_MARKERS:
                    break

                # Failed — retry if budget remains.
                if attempt <= self.max_retries:
                    logger.warning("round %d attempt %d failed (exit=%d), retrying (%d/%d)",
                                   round_index, attempt, result.exit_code,
                                   attempt + 1, self.max_retries + 1)
                    continue

                # All retries exhausted.
                logger.warning("round %d failed after %d attempt(s) (exit=%d)",
                               round_index, self.max_retries + 1, result.exit_code)

            # At this point, result is either a successful ExecutionResult,
            # a failed one (all retries exhausted), or a stop-marker result.
            assert result is not None

            finished_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
            stdout_path, stderr_path = self._dump_outputs(round_index, result)
            summary = RoundSummary(
                round=round_index,
                queue_item=target.raw,
                started_at=started_at,
                finished_at=finished_at,
                exit_code=result.exit_code,
                marker=result.marker,
                command=result.metadata.get("command", ""),
                verification_summary=result.verification_summary,
                duration_seconds=result.duration_seconds or (time.monotonic() - started),
                stdout_path=str(stdout_path) if stdout_path else None,
                stderr_path=str(stderr_path) if stderr_path else None,
            )
            invocations.append(summary)
            self._append_invocation(summary)
            self._write_checkpoint(target, result, round_index, stop_reason=None)

            if not result.succeeded:
                stop_for = "failed"
                break
            if result.marker in _RUN_STOP_MARKERS:
                stop_for = {
                    AUTONOMOUS_BOUNDARY_REACHED: "boundary",
                    AUTONOMOUS_BLOCKED: "blocked",
                    AUTONOMOUS_FAILED: "failed",
                }[result.marker]
                break
            if result.marker == AUTONOMOUS_READY_DONE:
                # Worker is done with this ready item; loop again.
                continue
            if result.marker == AUTONOMOUS_CONTEXT_HANDOFF:
                # Worker hands off to next; continue.
                continue
            # No explicit marker and exit 0: treat as one-shot success.
            continue

        total_elapsed = time.monotonic() - run_started
        logger.info("loop finished: %d round(s) in %.1fs, stopped_for=%s",
                     len(invocations), total_elapsed, stop_for)
        return LoopResult(rounds=len(invocations), stopped_for=stop_for, invocations=invocations)

    # Internal helpers ----------------------------------------------------

    @staticmethod
    def _resolve_max_rounds(mode: str, requested: int) -> int:
        if mode == "boundary":
            return max(requested, DEFAULT_MAX_ROUNDS_BOUNDARY) if requested <= 1 else requested
        return max(1, requested)

    def _append_invocation(self, summary: RoundSummary) -> None:
        self.invocation_log.parent.mkdir(parents=True, exist_ok=True)
        with self.invocation_log.open("a", encoding="utf-8") as handle:
            handle.write(summary.to_ndjson() + "\n")

    def _dump_outputs(
        self,
        round_index: int,
        result: ExecutionResult,
    ) -> tuple[Path | None, Path | None]:
        if not result.stdout and not result.stderr:
            return None, None
        out_dir = self.project_root / ".harness" / "worker-output"
        out_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        stdout_path = out_dir / f"{stamp}-round{round_index}-stdout.txt"
        stderr_path = out_dir / f"{stamp}-round{round_index}-stderr.txt"
        if result.stdout:
            stdout_path.write_text(result.stdout, encoding="utf-8")
        if result.stderr:
            stderr_path.write_text(result.stderr, encoding="utf-8")
        return stdout_path, stderr_path

    def _write_checkpoint(
        self,
        queue_item,
        result: ExecutionResult | None,
        round_index: int,
        stop_reason: str | None,
    ) -> None:
        cp = Checkpoint()
        cp.last_worker = f"round {round_index}: {queue_item.raw.splitlines()[0]}"
        if result is not None:
            cp.verification = (
                f"- command: {result.metadata.get('command', '')}\n"
                f"- exit_code: {result.exit_code}\n"
                f"- marker: {result.marker or 'none'}\n"
                f"- summary: {result.verification_summary or 'n/a'}"
            )
            cp.stop_reason = stop_reason or (
                f"marker={result.marker}" if result.marker and result.marker in _RUN_STOP_MARKERS else ""
            )
        else:
            cp.verification = "- runner terminated by error"
            cp.stop_reason = stop_reason or "error"
        cp.next_resume_source = str(self.queue_file)
        cp.durable_state_updated = (
            f"- queue item: {queue_item.raw.splitlines()[0]}\n"
            f"- invocation log: {self.invocation_log}"
        )
        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        cp.dump(self.checkpoint_file)


__all__ = ["AutonomousReadyLoop", "LoopResult", "RoundSummary"]