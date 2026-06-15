"""Tests for runner/adapters/codex_cli.py — CodexCliExecutor."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from harness_governance.runner.adapters.codex_cli import CodexCliExecutor
from harness_governance.runner.base import ExecutionResult


PATCH_RUN = "harness_governance.runner.adapters.codex_cli.subprocess.run"


@pytest.fixture
def executor() -> CodexCliExecutor:
    return CodexCliExecutor()


class TestNameProperty:
    def test_name_returns_codex(self, executor: CodexCliExecutor) -> None:
        assert executor.name == "codex"


class TestExecuteSuccess:
    @patch(PATCH_RUN)
    def test_basic_success(self, mock_run: MagicMock, executor: CodexCliExecutor) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=["codex", "exec", "do stuff"],
            returncode=0,
            stdout="AUTONOMOUS_READY_DONE\nAll tasks completed.",
            stderr="",
        )

        result = executor.execute("do stuff")

        assert isinstance(result, ExecutionResult)
        assert result.exit_code == 0
        assert result.succeeded is True
        assert result.marker == "AUTONOMOUS_READY_DONE"
        assert result.stdout == "AUTONOMOUS_READY_DONE\nAll tasks completed."
        assert result.stderr == ""
        assert result.duration_seconds >= 0.0

    @patch(PATCH_RUN)
    def test_metadata_contains_round_and_command(self, mock_run: MagicMock, executor: CodexCliExecutor) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="done", stderr="",
        )

        result = executor.execute("do stuff", round_label="R3")

        assert result.metadata["round"] == "R3"
        assert "codex exec" in result.metadata["command"]


class TestExecuteWithModel:
    @patch(PATCH_RUN)
    def test_model_flag_in_command(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ok", stderr="",
        )
        executor = CodexCliExecutor(model="o4-mini")

        executor.execute("fix bug")

        call_args = mock_run.call_args
        cmd = call_args[0][0] if call_args[0] else call_args[1]["args"]
        assert "--model" in cmd
        model_idx = cmd.index("--model")
        assert cmd[model_idx + 1] == "o4-mini"

    @patch(PATCH_RUN)
    def test_model_appears_in_metadata(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ok", stderr="",
        )
        executor = CodexCliExecutor(model="o4-mini")

        result = executor.execute("fix bug")

        assert "o4-mini" in result.metadata["command"]


class TestExecuteWithExtraArgs:
    @patch(PATCH_RUN)
    def test_extra_args_in_command(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ok", stderr="",
        )
        executor = CodexCliExecutor(extra_args=("--sandbox", "strict", "--verbose"))

        executor.execute("refactor")

        cmd = mock_run.call_args[0][0]
        assert "--sandbox" in cmd
        assert "strict" in cmd
        assert "--verbose" in cmd

    @patch(PATCH_RUN)
    def test_extra_args_before_prompt(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ok", stderr="",
        )
        executor = CodexCliExecutor(extra_args=("--flag",))

        executor.execute("my prompt")

        cmd = mock_run.call_args[0][0]
        prompt_idx = cmd.index("my prompt")
        flag_idx = cmd.index("--flag")
        assert flag_idx < prompt_idx


class TestExecuteWithWorkdir:
    @patch(PATCH_RUN)
    def test_workdir_sets_cwd(self, mock_run: MagicMock) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ok", stderr="",
        )
        work_path = Path("/tmp/my-project")
        executor = CodexCliExecutor(workdir=work_path)

        executor.execute("build")

        cwd = mock_run.call_args[1]["cwd"]
        assert cwd == str(work_path)

    @patch(PATCH_RUN)
    def test_no_workdir_cwd_is_none(self, mock_run: MagicMock, executor: CodexCliExecutor) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ok", stderr="",
        )

        executor.execute("build")

        cwd = mock_run.call_args[1]["cwd"]
        assert cwd is None


class TestExecuteFileNotFoundError:
    @patch(PATCH_RUN)
    def test_file_not_found_returns_127(self, mock_run: MagicMock, executor: CodexCliExecutor) -> None:
        mock_run.side_effect = FileNotFoundError("codex not found")

        result = executor.execute("anything")

        assert result.exit_code == 127
        assert result.stdout == ""
        assert "codex CLI not found" in result.stderr
        assert result.marker is None
        assert result.duration_seconds >= 0.0

    @patch(PATCH_RUN)
    def test_file_not_found_not_succeeded(self, mock_run: MagicMock, executor: CodexCliExecutor) -> None:
        mock_run.side_effect = FileNotFoundError()

        result = executor.execute("anything")

        assert result.succeeded is False


class TestExecuteTimeoutExpired:
    @patch(PATCH_RUN)
    def test_timeout_returns_124(self, mock_run: MagicMock, executor: CodexCliExecutor) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=["codex", "exec"],
            timeout=1800,
            output="partial output",
            stderr="still running",
        )

        result = executor.execute("long task")

        assert result.exit_code == 124
        assert result.marker is None
        assert result.duration_seconds >= 0.0

    @patch(PATCH_RUN)
    def test_timeout_stderr_includes_harness_message(self, mock_run: MagicMock, executor: CodexCliExecutor) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=["codex", "exec"],
            timeout=60,
        )

        result = executor.execute("long task", timeout_seconds=60)

        assert "[harness runner] timed out" in result.stderr

    @patch(PATCH_RUN)
    def test_timeout_preserves_partial_stdout(self, mock_run: MagicMock, executor: CodexCliExecutor) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=["codex", "exec"],
            timeout=10,
            output="partial work done",
            stderr="",
        )

        result = executor.execute("task", timeout_seconds=10)

        assert result.stdout == "partial work done"

    @patch(PATCH_RUN)
    def test_timeout_none_stdout_stderr(self, mock_run: MagicMock, executor: CodexCliExecutor) -> None:
        mock_run.side_effect = subprocess.TimeoutExpired(
            cmd=["codex", "exec"],
            timeout=10,
            output=None,
            stderr=None,
        )

        result = executor.execute("task", timeout_seconds=10)

        assert result.stdout == ""
        assert "[harness runner] timed out" in result.stderr


class TestExecuteMarkerDetection:
    @patch(PATCH_RUN)
    def test_autonomous_ready_done_marker(self, mock_run: MagicMock, executor: CodexCliExecutor) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout="AUTONOMOUS_READY_DONE",
            stderr="",
        )

        result = executor.execute("do it")
        assert result.marker == "AUTONOMOUS_READY_DONE"

    @patch(PATCH_RUN)
    def test_autonomous_blocked_marker(self, mock_run: MagicMock, executor: CodexCliExecutor) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout="some output\nAUTONOMOUS_BLOCKED\nmore output",
            stderr="",
        )

        result = executor.execute("do it")
        assert result.marker == "AUTONOMOUS_BLOCKED"

    @patch(PATCH_RUN)
    def test_autonomous_failed_marker(self, mock_run: MagicMock, executor: CodexCliExecutor) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1,
            stdout="",
            stderr="AUTONOMOUS_FAILED: something broke",
        )

        result = executor.execute("do it")
        assert result.marker == "AUTONOMOUS_FAILED"

    @patch(PATCH_RUN)
    def test_autonomous_boundary_reached_marker(self, mock_run: MagicMock, executor: CodexCliExecutor) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout="AUTONOMOUS_BOUNDARY_REACHED",
            stderr="",
        )

        result = executor.execute("do it")
        assert result.marker == "AUTONOMOUS_BOUNDARY_REACHED"

    @patch(PATCH_RUN)
    def test_autonomous_context_handoff_marker(self, mock_run: MagicMock, executor: CodexCliExecutor) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout="AUTONOMOUS_CONTEXT_HANDOFF",
            stderr="",
        )

        result = executor.execute("do it")
        assert result.marker == "AUTONOMOUS_CONTEXT_HANDOFF"

    @patch(PATCH_RUN)
    def test_no_marker_returns_none(self, mock_run: MagicMock, executor: CodexCliExecutor) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout="just regular output",
            stderr="no markers here",
        )

        result = executor.execute("do it")
        assert result.marker is None


class TestExecuteVerificationSummary:
    @patch(PATCH_RUN)
    def test_pytest_verification_summary(self, mock_run: MagicMock, executor: CodexCliExecutor) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout="- pytest: 42 passed, 0 failed\nAUTONOMOUS_READY_DONE",
            stderr="",
        )

        result = executor.execute("run tests")

        assert result.verification_summary is not None
        assert "pytest" in result.verification_summary

    @patch(PATCH_RUN)
    def test_npm_test_verification_summary(self, mock_run: MagicMock, executor: CodexCliExecutor) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout="- npm test: all 15 tests passed\n",
            stderr="",
        )

        result = executor.execute("run tests")

        assert result.verification_summary is not None
        assert "npm test" in result.verification_summary

    @patch(PATCH_RUN)
    def test_no_verification_summary(self, mock_run: MagicMock, executor: CodexCliExecutor) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0,
            stdout="just some output without test results",
            stderr="",
        )

        result = executor.execute("do stuff")

        assert result.verification_summary is None


class TestExecuteDefaultModelMetadata:
    @patch(PATCH_RUN)
    def test_default_model_in_command(self, mock_run: MagicMock, executor: CodexCliExecutor) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ok", stderr="",
        )

        result = executor.execute("task")

        assert "<default>" in result.metadata["command"]
        assert result.metadata["command"] == "codex exec <default> ..."

    @patch(PATCH_RUN)
    def test_no_model_flag_when_none(self, mock_run: MagicMock, executor: CodexCliExecutor) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ok", stderr="",
        )

        executor.execute("task")

        cmd = mock_run.call_args[0][0]
        assert "--model" not in cmd


class TestExecuteSubprocessCallArgs:
    @patch(PATCH_RUN)
    def test_capture_output_and_text(self, mock_run: MagicMock, executor: CodexCliExecutor) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ok", stderr="",
        )

        executor.execute("task")

        kwargs = mock_run.call_args[1]
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True

    @patch(PATCH_RUN)
    def test_timeout_passed_through(self, mock_run: MagicMock, executor: CodexCliExecutor) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ok", stderr="",
        )

        executor.execute("task", timeout_seconds=300)

        kwargs = mock_run.call_args[1]
        assert kwargs["timeout"] == 300

    @patch(PATCH_RUN)
    def test_prompt_is_last_arg(self, mock_run: MagicMock, executor: CodexCliExecutor) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ok", stderr="",
        )

        executor.execute("my specific prompt")

        cmd = mock_run.call_args[0][0]
        assert cmd[-1] == "my specific prompt"
        assert cmd[0] == "codex"
        assert cmd[1] == "exec"

    @patch(PATCH_RUN)
    def test_env_is_passed(self, mock_run: MagicMock, executor: CodexCliExecutor) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="ok", stderr="",
        )

        executor.execute("task")

        kwargs = mock_run.call_args[1]
        assert "env" in kwargs
        assert isinstance(kwargs["env"], dict)


class TestExecuteNonZeroExit:
    @patch(PATCH_RUN)
    def test_nonzero_exit_not_succeeded(self, mock_run: MagicMock, executor: CodexCliExecutor) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="error output", stderr="something failed",
        )

        result = executor.execute("task")

        assert result.exit_code == 1
        assert result.succeeded is False

    @patch(PATCH_RUN)
    def test_empty_stdout_stderr(self, mock_run: MagicMock, executor: CodexCliExecutor) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout=None, stderr=None,
        )

        result = executor.execute("task")

        assert result.stdout == ""
        assert result.stderr == ""
