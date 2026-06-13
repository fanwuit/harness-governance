"""Subprocess-based AgentExecutor that runs a configurable shell command."""

from __future__ import annotations

import os
import shlex
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from ..base import AgentExecutor, ExecutionResult, detect_marker, detect_verification_summary


@dataclass(slots=True)
class SubprocessAgentExecutor(AgentExecutor):
    """Run an agent command via ``subprocess.run``.

    The agent is invoked as ``command_prompt_placeholder`` (or via
    positional append when ``prompt_as_arg`` is True). The executor
    records stdout/stderr so the loop can detect markers, capture
    verification summaries, and write an invocation log entry.
    """

    command_template: str
    prompt_placeholder: str = "{prompt}"
    prompt_as_arg: bool = False
    env_overrides: dict[str, str] | None = None
    workdir: Path | None = None

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
        try:
            completed = subprocess.run(
                list(cmd),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                env=env,
                cwd=cwd,
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
            metadata={"round": round_label, "command": " ".join(cmd)},
        )


__all__ = ["SubprocessAgentExecutor"]