"""Tests for runner/adapters/codex_cli.py — CodexCliExecutor.

Since the executor was refactored from ``subprocess.run`` to
``subprocess.Popen`` (for streaming + heartbeat support), the mock
target is now ``subprocess.Popen``.
"""

from __future__ import annotations

import io
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from harness_governance.runner.adapters.codex_cli import CodexCliExecutor
from harness_governance.runner.base import ExecutionResult


PATCH_POPEN = "harness_governance.runner.adapters.codex_cli.subprocess.Popen"

# Capture the real Popen class before any @patch replaces it.
_REAL_POPEN = subprocess.Popen


def _make_mock_popen(
    stdout: str = "",
    stderr: str = "",
    returncode: int = 0,
    raise_fn: Exception | None = None,
) -> MagicMock:
    """Create a MagicMock that behaves like a completed Popen."""
    mock = MagicMock(spec=_REAL_POPEN)
    if raise_fn is not None:
        mock.side_effect = raise_fn
        return mock

    mock.returncode = returncode
    mock.pid = 12345
    mock.stdout = io.StringIO(stdout)
    mock.stderr = io.StringIO(stderr)
    mock.poll.return_value = returncode
    mock.wait.return_value = returncode
    return mock


@pytest.fixture
def executor() -> CodexCliExecutor:
    return CodexCliExecutor(heartbeat_interval_seconds=0)


class TestNameProperty:
    def test_name_returns_codex(self, executor: CodexCliExecutor) -> None:
        assert executor.name == "codex"


class TestExecuteSuccess:
    @patch(PATCH_POPEN)
    def test_basic_success(
        self, mock_popen_cls: MagicMock, executor: CodexCliExecutor
    ) -> None:
        mock_popen_cls.return_value = _make_mock_popen(
            stdout="AUTONOMOUS_READY_DONE\nAll tasks completed.",
        )

        result = executor.execute("do stuff")

        assert isinstance(result, ExecutionResult)
        assert result.exit_code == 0
        assert result.succeeded is True
        assert result.marker == "AUTONOMOUS_READY_DONE"
        assert "AUTONOMOUS_READY_DONE" in result.stdout
        assert result.duration_seconds >= 0.0

    @patch(PATCH_POPEN)
    def test_metadata_contains_round_and_command(
        self, mock_popen_cls: MagicMock, executor: CodexCliExecutor
    ) -> None:
        mock_popen_cls.return_value = _make_mock_popen(stdout="done")

        result = executor.execute("do stuff", round_label="R3")

        assert result.metadata["round"] == "R3"
        assert "codex exec" in result.metadata["command"]


class TestExecuteWithModel:
    @patch(PATCH_POPEN)
    def test_model_flag_in_command(self, mock_popen_cls: MagicMock) -> None:
        mock_popen_cls.return_value = _make_mock_popen(stdout="ok")
        executor = CodexCliExecutor(model="o4-mini", heartbeat_interval_seconds=0)

        executor.execute("fix bug")

        cmd = mock_popen_cls.call_args[0][0]
        assert "--model" in cmd
        model_idx = cmd.index("--model")
        assert cmd[model_idx + 1] == "o4-mini"

    @patch(PATCH_POPEN)
    def test_model_appears_in_metadata(self, mock_popen_cls: MagicMock) -> None:
        mock_popen_cls.return_value = _make_mock_popen(stdout="ok")
        executor = CodexCliExecutor(model="o4-mini", heartbeat_interval_seconds=0)

        result = executor.execute("fix bug")

        assert "o4-mini" in result.metadata["command"]


class TestExecuteWithExtraArgs:
    @patch(PATCH_POPEN)
    def test_extra_args_in_command(self, mock_popen_cls: MagicMock) -> None:
        mock_popen_cls.return_value = _make_mock_popen(stdout="ok")
        executor = CodexCliExecutor(
            extra_args=("--sandbox", "strict", "--verbose"),
            heartbeat_interval_seconds=0,
        )

        executor.execute("refactor")

        cmd = mock_popen_cls.call_args[0][0]
        assert "--sandbox" in cmd
        assert "strict" in cmd
        assert "--verbose" in cmd

    @patch(PATCH_POPEN)
    def test_extra_args_before_prompt(self, mock_popen_cls: MagicMock) -> None:
        mock_popen_cls.return_value = _make_mock_popen(stdout="ok")
        executor = CodexCliExecutor(
            extra_args=("--flag",), heartbeat_interval_seconds=0
        )

        executor.execute("my prompt")

        cmd = mock_popen_cls.call_args[0][0]
        prompt_idx = cmd.index("my prompt")
        flag_idx = cmd.index("--flag")
        assert flag_idx < prompt_idx


class TestExecuteWithWorkdir:
    @patch(PATCH_POPEN)
    def test_workdir_sets_cwd(self, mock_popen_cls: MagicMock) -> None:
        mock_popen_cls.return_value = _make_mock_popen(stdout="ok")
        work_path = Path("/tmp/my-project")
        executor = CodexCliExecutor(workdir=work_path, heartbeat_interval_seconds=0)

        executor.execute("build")

        cwd = mock_popen_cls.call_args[1]["cwd"]
        assert cwd == str(work_path)

    @patch(PATCH_POPEN)
    def test_no_workdir_cwd_is_none(
        self, mock_popen_cls: MagicMock, executor: CodexCliExecutor
    ) -> None:
        mock_popen_cls.return_value = _make_mock_popen(stdout="ok")

        executor.execute("build")

        cwd = mock_popen_cls.call_args[1]["cwd"]
        assert cwd is None


class TestExecuteFileNotFoundError:
    @patch(PATCH_POPEN)
    def test_file_not_found_returns_127(
        self, mock_popen_cls: MagicMock, executor: CodexCliExecutor
    ) -> None:
        mock_popen_cls.side_effect = FileNotFoundError("codex not found")

        result = executor.execute("anything")

        assert result.exit_code == 127
        assert result.stdout == ""
        assert "codex CLI not found" in result.stderr
        assert result.marker is None
        assert result.duration_seconds >= 0.0

    @patch(PATCH_POPEN)
    def test_file_not_found_not_succeeded(
        self, mock_popen_cls: MagicMock, executor: CodexCliExecutor
    ) -> None:
        mock_popen_cls.side_effect = FileNotFoundError()

        result = executor.execute("anything")

        assert result.succeeded is False


class TestExecuteTimeoutExpired:
    @patch(PATCH_POPEN)
    def test_timeout_returns_124(
        self, mock_popen_cls: MagicMock, executor: CodexCliExecutor
    ) -> None:
        mock_proc = _make_mock_popen(stdout="partial", stderr="")
        # First wait(timeout=...) raises TimeoutExpired; second wait() (after kill) returns normally.
        mock_proc.wait.side_effect = [
            subprocess.TimeoutExpired(cmd=["codex", "exec"], timeout=1800),
            0,
        ]
        mock_popen_cls.return_value = mock_proc

        result = executor.execute("long task")

        assert result.exit_code == 124
        assert result.marker is None
        assert result.duration_seconds >= 0.0

    @patch(PATCH_POPEN)
    def test_timeout_stderr_includes_harness_message(
        self, mock_popen_cls: MagicMock, executor: CodexCliExecutor
    ) -> None:
        mock_proc = _make_mock_popen(stdout="", stderr="")
        mock_proc.wait.side_effect = [
            subprocess.TimeoutExpired(cmd=["codex", "exec"], timeout=60),
            0,
        ]
        mock_popen_cls.return_value = mock_proc

        result = executor.execute("long task", timeout_seconds=60)

        assert "[harness runner] timed out" in result.stderr


class TestExecuteMarkerDetection:
    @patch(PATCH_POPEN)
    def test_autonomous_ready_done_marker(
        self, mock_popen_cls: MagicMock, executor: CodexCliExecutor
    ) -> None:
        mock_popen_cls.return_value = _make_mock_popen(stdout="AUTONOMOUS_READY_DONE")

        result = executor.execute("do it")
        assert result.marker == "AUTONOMOUS_READY_DONE"

    @patch(PATCH_POPEN)
    def test_autonomous_blocked_marker(
        self, mock_popen_cls: MagicMock, executor: CodexCliExecutor
    ) -> None:
        mock_popen_cls.return_value = _make_mock_popen(
            stdout="some output\nAUTONOMOUS_BLOCKED\nmore output",
        )

        result = executor.execute("do it")
        assert result.marker == "AUTONOMOUS_BLOCKED"

    @patch(PATCH_POPEN)
    def test_autonomous_failed_marker(
        self, mock_popen_cls: MagicMock, executor: CodexCliExecutor
    ) -> None:
        mock_popen_cls.return_value = _make_mock_popen(
            stdout="",
            stderr="AUTONOMOUS_FAILED: something broke",
            returncode=1,
        )

        result = executor.execute("do it")
        assert result.marker == "AUTONOMOUS_FAILED"

    @patch(PATCH_POPEN)
    def test_no_marker_returns_none(
        self, mock_popen_cls: MagicMock, executor: CodexCliExecutor
    ) -> None:
        mock_popen_cls.return_value = _make_mock_popen(
            stdout="just regular output",
            stderr="no markers here",
        )

        result = executor.execute("do it")
        assert result.marker is None


class TestExecuteVerificationSummary:
    @patch(PATCH_POPEN)
    def test_pytest_verification_summary(
        self, mock_popen_cls: MagicMock, executor: CodexCliExecutor
    ) -> None:
        mock_popen_cls.return_value = _make_mock_popen(
            stdout="- pytest: 42 passed, 0 failed\nAUTONOMOUS_READY_DONE",
        )

        result = executor.execute("run tests")
        assert result.verification_summary is not None
        assert "pytest" in result.verification_summary

    @patch(PATCH_POPEN)
    def test_no_verification_summary(
        self, mock_popen_cls: MagicMock, executor: CodexCliExecutor
    ) -> None:
        mock_popen_cls.return_value = _make_mock_popen(
            stdout="just some output without test results",
        )

        result = executor.execute("do stuff")
        assert result.verification_summary is None


class TestExecuteDefaultModelMetadata:
    @patch(PATCH_POPEN)
    def test_default_model_in_command(
        self, mock_popen_cls: MagicMock, executor: CodexCliExecutor
    ) -> None:
        mock_popen_cls.return_value = _make_mock_popen(stdout="ok")

        result = executor.execute("task")

        assert "<default>" in result.metadata["command"]


class TestExecutePopenCallArgs:
    @patch(PATCH_POPEN)
    def test_popen_called_with_text_and_pipes(
        self, mock_popen_cls: MagicMock, executor: CodexCliExecutor
    ) -> None:
        mock_popen_cls.return_value = _make_mock_popen(stdout="ok")

        executor.execute("task")

        kwargs = mock_popen_cls.call_args[1]
        assert kwargs["text"] is True
        assert kwargs["stdout"] == subprocess.PIPE
        assert kwargs["stderr"] == subprocess.PIPE

    @patch(PATCH_POPEN)
    def test_prompt_is_last_arg(
        self, mock_popen_cls: MagicMock, executor: CodexCliExecutor
    ) -> None:
        mock_popen_cls.return_value = _make_mock_popen(stdout="ok")

        executor.execute("my specific prompt")

        cmd = mock_popen_cls.call_args[0][0]
        assert cmd[-1] == "my specific prompt"
        assert cmd[0] == "codex"
        assert cmd[1] == "exec"

    @patch(PATCH_POPEN)
    def test_env_is_passed(
        self, mock_popen_cls: MagicMock, executor: CodexCliExecutor
    ) -> None:
        mock_popen_cls.return_value = _make_mock_popen(stdout="ok")

        executor.execute("task")

        kwargs = mock_popen_cls.call_args[1]
        assert "env" in kwargs
        assert isinstance(kwargs["env"], dict)


class TestExecuteNonZeroExit:
    @patch(PATCH_POPEN)
    def test_nonzero_exit_not_succeeded(
        self, mock_popen_cls: MagicMock, executor: CodexCliExecutor
    ) -> None:
        mock_popen_cls.return_value = _make_mock_popen(
            stdout="error output",
            stderr="something failed",
            returncode=1,
        )

        result = executor.execute("task")

        assert result.exit_code == 1
        assert result.succeeded is False

    @patch(PATCH_POPEN)
    def test_empty_stdout_stderr(
        self, mock_popen_cls: MagicMock, executor: CodexCliExecutor
    ) -> None:
        mock_popen_cls.return_value = _make_mock_popen(stdout="", stderr="")

        result = executor.execute("task")

        assert result.stdout == ""
        assert result.stderr == ""


class TestHeartbeat:
    @patch(PATCH_POPEN)
    def test_heartbeat_disabled_when_zero(self, mock_popen_cls: MagicMock) -> None:
        mock_popen_cls.return_value = _make_mock_popen(stdout="ok")
        executor = CodexCliExecutor(heartbeat_interval_seconds=0)

        executor.execute("task")

        # No heartbeat file should be created; no crash either.
        # Just verify the executor completed successfully.

    def test_heartbeat_interval_default(self) -> None:
        executor = CodexCliExecutor()
        assert executor.heartbeat_interval_seconds == 30
