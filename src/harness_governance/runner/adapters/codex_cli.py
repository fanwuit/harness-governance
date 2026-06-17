"""Codex CLI headless executor for CI/CD automation.

Use ``--executor codex`` for unattended runs where the agent is invoked
as an external process. For interactive sessions, prefer ``--executor
orchestrator`` which generates a prompt for native platform subagent
dispatch.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ..base import (
    AgentExecutor,
    ExecutionResult,
    detect_marker,
    detect_verification_summary,
)
from ._heartbeat import (
    HeartbeatCounters,
    format_progress_line,
    start_heartbeat_thread,
)

# Minimum seconds between progress lines on stderr.
_PROGRESS_INTERVAL_S = 60


@dataclass(slots=True)
class CodexCliExecutor(AgentExecutor):
    """Run ``codex exec`` for each round.

    Uses ``subprocess.Popen`` with line-by-line stdout/stderr streaming
    (instead of ``subprocess.run(capture_output=True)``) so that:

    * Output appears in real time on the parent's stderr.
    * A heartbeat thread can report progress during long runs.
    """

    model: str | None = None
    extra_args: tuple[str, ...] = ()
    workdir: Path | None = None
    stream_output: bool = True
    heartbeat_interval_seconds: int = 30
    heartbeat_dir: Path | None = None

    @property
    def name(self) -> str:
        return "codex"

    def execute(
        self,
        prompt: str,
        *,
        timeout_seconds: int = 1800,
        round_label: str = "",
    ) -> ExecutionResult:
        cmd = ["codex", "exec"]
        if self.model:
            cmd.extend(["--model", self.model])
        cmd.extend(self.extra_args)
        cmd.append(prompt)

        env = dict(os.environ)
        cwd = str(self.workdir) if self.workdir else None

        started = time.monotonic()
        counters = HeartbeatCounters()
        stdout_lines: list[str] = []
        stderr_lines: list[str] = []

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                cwd=cwd,
            )

            # --- Heartbeat thread ---
            if self.heartbeat_interval_seconds > 0:
                hb_dir = self.heartbeat_dir or (
                    (self.workdir or Path.cwd()) / ".harness" / "worker-output"
                )
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                hb_path = hb_dir / f"{stamp}-heartbeat.ndjson"
                start_heartbeat_thread(
                    proc,
                    hb_path,
                    counters,
                    self.heartbeat_interval_seconds,
                    started,
                )

            # --- Stream stdout ---
            last_progress = started
            if proc.stdout is not None:
                for line in proc.stdout:
                    counters.stdout_lines += 1
                    if self.stream_output:
                        sys.stderr.write(line)
                        sys.stderr.flush()
                        now = time.monotonic()
                        if now - last_progress >= _PROGRESS_INTERVAL_S:
                            sys.stderr.write(
                                format_progress_line(
                                    now - started,
                                    counters.stdout_lines,
                                    counters.stderr_lines,
                                )
                            )
                            sys.stderr.flush()
                            last_progress = now
                    stdout_lines.append(line)

            # --- Stream stderr ---
            if proc.stderr is not None:
                for line in proc.stderr:
                    counters.stderr_lines += 1
                    if self.stream_output:
                        sys.stderr.write(line)
                        sys.stderr.flush()
                    stderr_lines.append(line)

            proc.wait(timeout=timeout_seconds)

        except FileNotFoundError:
            return ExecutionResult(
                exit_code=127,
                stdout="",
                stderr=(
                    "codex CLI not found on PATH. Install Codex CLI or use "
                    "SubprocessAgentExecutor with a different command."
                ),
                marker=None,
                duration_seconds=time.monotonic() - started,
            )

        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            return ExecutionResult(
                exit_code=124,
                stdout="".join(stdout_lines),
                stderr="".join(stderr_lines)
                + f"\n[harness runner] timed out after {timeout_seconds}s",
                marker=None,
                duration_seconds=time.monotonic() - started,
            )

        stdout = "".join(stdout_lines)
        stderr = "".join(stderr_lines)
        return ExecutionResult(
            exit_code=proc.returncode,
            stdout=stdout,
            stderr=stderr,
            marker=detect_marker(stdout + "\n" + stderr),
            duration_seconds=time.monotonic() - started,
            verification_summary=detect_verification_summary(stdout),
            metadata={
                "round": round_label,
                "command": "codex exec " + (self.model or "<default>") + " ...",
            },
        )


__all__ = ["CodexCliExecutor"]
