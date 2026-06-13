"""Codex CLI adapter for the autonomous runner.

Mirrors the legacy ``run-autonomous-ready-loop.sh`` invocation pattern:
``codex exec --prompt <text>`` with stdout/stderr captured and
``AUTONOMOUS_*`` markers parsed.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from ..base import AgentExecutor, ExecutionResult, detect_marker, detect_verification_summary


@dataclass(slots=True)
class CodexCliExecutor(AgentExecutor):
    """Run ``codex exec`` for each round."""

    model: str | None = None
    extra_args: tuple[str, ...] = ()
    workdir: Path | None = None

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
        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                env=env,
                cwd=cwd,
            )
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
        except subprocess.TimeoutExpired as exc:
            return ExecutionResult(
                exit_code=124,
                stdout=exc.stdout or "",
                stderr=(exc.stderr or "") + f"\n[harness runner] timed out after {timeout_seconds}s",
                marker=None,
                duration_seconds=time.monotonic() - started,
            )

        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        return ExecutionResult(
            exit_code=completed.returncode,
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