"""Tests for the autonomous runner."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness_governance.runner.adapters.generic import SubprocessAgentExecutor
from harness_governance.runner.base import (
    AUTONOMOUS_BOUNDARY_REACHED,
    AUTONOMOUS_READY_DONE,
    detect_marker,
    detect_verification_summary,
)
from harness_governance.runner.loop import AutonomousReadyLoop


@pytest.fixture
def runner_repo(tmp_path: Path) -> Path:
    (tmp_path / "NEXT.md").write_text(
        "[ready] Sample task\n- Layer: implementation\n- Change: sample-change\n",
        encoding="utf-8",
    )
    return tmp_path


def test_detect_marker_finds_boundary() -> None:
    assert detect_marker("worker output\nAUTONOMOUS_BOUNDARY_REACHED\n") == AUTONOMOUS_BOUNDARY_REACHED


def test_detect_marker_finds_ready_done() -> None:
    assert detect_marker("ok\nAUTONOMOUS_READY_DONE\n") == AUTONOMOUS_READY_DONE


def test_detect_marker_returns_none_when_missing() -> None:
    assert detect_marker("just plain output") is None


def test_detect_verification_summary_picks_pytest_line() -> None:
    text = "logs\n- pytest -q -> 42 passed\n"
    assert detect_verification_summary(text) == "pytest -q -> 42 passed"


def test_subprocess_executor_runs_command(runner_repo: Path) -> None:
    executor = SubprocessAgentExecutor(
        command_template=f'python -c "print(\\"AUTONOMOUS_READY_DONE\\")"',
        prompt_as_arg=False,
        workdir=runner_repo,
    )
    result = executor.execute("ignored", timeout_seconds=10, round_label="1")
    assert result.exit_code == 0
    assert result.marker == AUTONOMOUS_READY_DONE


def test_subprocess_executor_records_failure_exit_code(runner_repo: Path) -> None:
    executor = SubprocessAgentExecutor(
        command_template='python -c "import sys; sys.exit(2)"',
        prompt_as_arg=False,
        workdir=runner_repo,
    )
    result = executor.execute("ignored", timeout_seconds=10, round_label="1")
    assert result.exit_code == 2


def test_loop_runs_one_round_and_writes_checkpoint(runner_repo: Path) -> None:
    executor = SubprocessAgentExecutor(
        command_template='python -c "print(\\"AUTONOMOUS_READY_DONE\\")"',
        workdir=runner_repo,
    )
    loop = AutonomousReadyLoop(
        executor=executor,
        project_root=runner_repo,
        queue_file=Path("NEXT.md"),
        checkpoint_file=Path(".harness/run-checkpoint.md"),
        invocation_log=Path(".harness/codex-exec-invocations.ndjson"),
        prompt_builder=lambda item: "PROMPT",
    )
    result = loop.run(mode="bounded", max_rounds=1)
    assert result.rounds == 1
    assert result.stopped_for == "max_rounds"
    assert (runner_repo / ".harness" / "run-checkpoint.md").is_file()
    log_lines = (runner_repo / ".harness" / "codex-exec-invocations.ndjson").read_text(encoding="utf-8").splitlines()
    assert len(log_lines) == 1
    record = json.loads(log_lines[0])
    assert record["marker"] == AUTONOMOUS_READY_DONE


def test_loop_stops_on_boundary_marker(runner_repo: Path) -> None:
    executor = SubprocessAgentExecutor(
        command_template='python -c "print(\\"AUTONOMOUS_BOUNDARY_REACHED\\")"',
        workdir=runner_repo,
    )
    loop = AutonomousReadyLoop(
        executor=executor,
        project_root=runner_repo,
        queue_file=Path("NEXT.md"),
        checkpoint_file=Path(".harness/run-checkpoint.md"),
        invocation_log=Path(".harness/codex-exec-invocations.ndjson"),
        prompt_builder=lambda item: "PROMPT",
    )
    result = loop.run(mode="boundary", max_rounds=10)
    assert result.rounds == 1
    assert result.stopped_for == "boundary"


def test_loop_reports_no_ready_when_queue_empty(tmp_path: Path) -> None:
    executor = SubprocessAgentExecutor(
        command_template='python -c "print(1)"',
        workdir=tmp_path,
    )
    loop = AutonomousReadyLoop(
        executor=executor,
        project_root=tmp_path,
        queue_file=Path("NEXT.md"),
        checkpoint_file=Path(".harness/run-checkpoint.md"),
        invocation_log=Path(".harness/codex-exec-invocations.ndjson"),
        prompt_builder=lambda item: "PROMPT",
    )
    result = loop.run(mode="bounded", max_rounds=5)
    assert result.rounds == 0
    assert result.stopped_for == "no_ready"


def test_runner_start_cli_dry_run(tmp_repo: Path) -> None:
    from click.testing import CliRunner
    from harness_governance.cli import cli

    (tmp_repo / "NEXT.md").write_text(
        "[ready] Test\n- Layer: implementation\n", encoding="utf-8"
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "runner",
            "start",
            "--executor",
            "subprocess",
            "--command",
            'echo "{prompt}"',
            "--dry-run",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Test" in result.output


# ---------------------------------------------------------------------------
# Retry mechanism
# ---------------------------------------------------------------------------


def test_loop_retries_on_failure_and_succeeds(runner_repo: Path) -> None:
    """Executor fails first attempt, succeeds on retry."""
    call_count = 0

    class FlakyExecutor:
        name = "flaky"

        def execute(self, prompt, *, timeout_seconds, round_label):
            nonlocal call_count
            call_count += 1
            from harness_governance.runner.base import ExecutionResult

            if call_count == 1:
                return ExecutionResult(
                    exit_code=1, stdout="fail", stderr="", marker=None,
                    duration_seconds=0.01,
                )
            return ExecutionResult(
                exit_code=0, stdout=AUTONOMOUS_READY_DONE, stderr="",
                marker=AUTONOMOUS_READY_DONE, duration_seconds=0.01,
            )

    loop = AutonomousReadyLoop(
        executor=FlakyExecutor(),
        project_root=runner_repo,
        queue_file=Path("NEXT.md"),
        checkpoint_file=Path(".harness/run-checkpoint.md"),
        invocation_log=Path(".harness/invocations.ndjson"),
        prompt_builder=lambda item: "PROMPT",
        max_retries=2,
    )
    result = loop.run(mode="bounded", max_rounds=1)
    assert result.stopped_for == "max_rounds"
    assert call_count == 2  # first fail + retry success


def test_loop_retries_exhausted_marks_failed(runner_repo: Path) -> None:
    """All retries fail; loop reports 'failed'."""
    from harness_governance.runner.base import ExecutionResult

    class AlwaysFailExecutor:
        name = "fail"

        def execute(self, prompt, *, timeout_seconds, round_label):
            return ExecutionResult(
                exit_code=1, stdout="error", stderr="", marker=None,
                duration_seconds=0.01,
            )

    loop = AutonomousReadyLoop(
        executor=AlwaysFailExecutor(),
        project_root=runner_repo,
        queue_file=Path("NEXT.md"),
        checkpoint_file=Path(".harness/run-checkpoint.md"),
        invocation_log=Path(".harness/invocations.ndjson"),
        prompt_builder=lambda item: "PROMPT",
        max_retries=2,
    )
    result = loop.run(mode="bounded", max_rounds=1)
    assert result.stopped_for == "failed"
    assert result.rounds == 1  # only 1 invocation logged (final result)


# ---------------------------------------------------------------------------
# Total timeout
# ---------------------------------------------------------------------------


def test_loop_respects_total_timeout(runner_repo: Path) -> None:
    """Total timeout stops the loop even if max_rounds allows more."""
    from harness_governance.runner.base import ExecutionResult

    class SlowExecutor:
        name = "slow"

        def execute(self, prompt, *, timeout_seconds, round_label):
            return ExecutionResult(
                exit_code=0, stdout=AUTONOMOUS_READY_DONE, stderr="",
                marker=AUTONOMOUS_READY_DONE, duration_seconds=0.1,
            )

    loop = AutonomousReadyLoop(
        executor=SlowExecutor(),
        project_root=runner_repo,
        queue_file=Path("NEXT.md"),
        checkpoint_file=Path(".harness/run-checkpoint.md"),
        invocation_log=Path(".harness/invocations.ndjson"),
        prompt_builder=lambda item: "PROMPT",
        total_timeout_seconds=0,  # immediately exceeded
    )
    result = loop.run(mode="boundary", max_rounds=100)
    assert result.stopped_for == "error"
    assert result.rounds == 0  # no rounds completed