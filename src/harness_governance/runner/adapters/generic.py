"""Subprocess-based AgentExecutor that runs a configurable shell command.

Output is streamed to stderr in real time so long-running agent
sessions are not completely silent while they work.  An optional
heartbeat thread writes NDJSON progress entries so callers can
distinguish "still running" from "hung / crashed".
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from ..base import AgentExecutor, ExecutionResult, detect_marker, detect_verification_summary
from ._heartbeat import (
    HeartbeatCounters,
    format_progress_line,
    start_heartbeat_thread,
)

# Minimum seconds between progress lines on stderr.
_PROGRESS_INTERVAL_S = 60


@dataclass(slots=True)
class SubprocessAgentExecutor(AgentExecutor):
    """Run an agent command via ``subprocess.Popen``.

    The agent is invoked as ``command_prompt_placeholder`` (or via
    positional append when ``prompt_as_arg`` is True). Stdout and stderr
    are streamed to the parent's stderr in real time, then captured for
    marker detection and invocation-log recording.

    When ``heartbeat_interval_seconds > 0``, a daemon thread writes
    NDJSON heartbeat entries to ``heartbeat_dir / <stamp>-heartbeat.ndjson``
    so external monitors can observe progress.
    """

    command_template: str
    prompt_placeholder: str = "{prompt}"
    prompt_as_arg: bool = False
    env_overrides: dict[str, str] | None = None
    workdir: Path | None = None
    stream_output: bool = True
    heartbeat_interval_seconds: int = 30
    heartbeat_dir: Path | None = None

    @property
    def name(self) -> str:
        return f"subprocess:{self.command_template.split()[0]}"

    def execute(
        self,
        prompt: str,
        *,
        timeout_seconds: int = 1800,
        round_label: str = "",
    ) -> ExecutionResult:
        env = dict(os.environ)
        if self.env_overrides:
            env.update(self.env_overrides)

        cwd = str(self.workdir) if self.workdir else None

        if self.prompt_as_arg:
            cmd: Sequence[str] = [*shlex.split(self.command_template), prompt]
        else:
            cmd_str = self.command_template.replace(self.prompt_placeholder, prompt)
            cmd = shlex.split(cmd_str)

        started = time.monotonic()
        counters = HeartbeatCounters()
        stdout_lines: list[str] = []
        stderr_lines: list[str] = []

        try:
            proc = subprocess.Popen(
                list(cmd),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env,
                cwd=cwd,
            )

            # --- Heartbeat thread ---
            hb_thread = None
            if self.heartbeat_interval_seconds > 0:
                hb_dir = self.heartbeat_dir or (
                    (self.workdir or Path.cwd()) / ".harness" / "worker-output"
                )
                stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                hb_path = hb_dir / f"{stamp}-heartbeat.ndjson"
                hb_thread = start_heartbeat_thread(
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
                        # Progress hint every _PROGRESS_INTERVAL_S seconds
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
                stderr=f"[harness runner] command not found: {cmd[0]}",
                marker=None,
                duration_seconds=time.monotonic() - started,
            )

        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
            return ExecutionResult(
                exit_code=124,
                stdout="".join(stdout_lines),
                stderr="".join(stderr_lines) + f"\n[harness runner] timed out after {timeout_seconds}s",
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
            metadata={"round": round_label, "command": " ".join(cmd)},
        )


__all__ = ["SubprocessAgentExecutor"]
