"""Tests for ``harness runner`` CLI commands (non-dry-run paths).

Covers runner.py lines 150-404: subprocess execution, orchestrator mode,
render, and parse-result commands.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from click.testing import CliRunner

from harness_governance.cli import cli


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_READY_QUEUE = "[ready] Test task\n- Layer: implementation\n- Change: sample-change\n"


def _write_ready_queue(root: Path) -> None:
    """Write a minimal NEXT.md with one [ready] item."""
    (root / "NEXT.md").write_text(_READY_QUEUE, encoding="utf-8")


# ---------------------------------------------------------------------------
# runner start -- subprocess executor (actual execution, lines 210-233)
# ---------------------------------------------------------------------------


def test_runner_start_subprocess_success(tmp_repo: Path) -> None:
    """Run one round with subprocess executor and verify JSON output structure."""
    _write_ready_queue(tmp_repo)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "--json",
            "runner",
            "start",
            "--executor",
            "subprocess",
            "--command",
            f'"{sys.executable}" -c "print(\\"AUTONOMOUS_READY_DONE\\")"',
            "--max-rounds",
            "1",
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert "rounds" in data
    assert "stopped_for" in data
    assert "invocations" in data
    assert data["rounds"] == 1
    assert data["stopped_for"] == "max_rounds"
    assert isinstance(data["invocations"], list)
    assert len(data["invocations"]) == 1


def test_runner_writes_checkpoint_to_change_dir(tmp_repo: Path) -> None:
    """When packet directory exists, checkpoint/invocation go inside it."""
    _write_ready_queue(tmp_repo)
    # Create the change packet directory
    change_dir = tmp_repo / "docs" / "changes" / "sample-change"
    change_dir.mkdir(parents=True)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "--json",
            "runner",
            "start",
            "--executor",
            "subprocess",
            "--command",
            f'"{sys.executable}" -c "print(\\"AUTONOMOUS_READY_DONE\\")"',
            "--max-rounds",
            "1",
        ],
    )
    assert result.exit_code == 0, result.output
    # Per-change isolation: checkpoint and invocation log inside packet dir
    assert (change_dir / ".checkpoint.md").is_file()
    assert (change_dir / ".invocations.ndjson").is_file()
    # Global paths should NOT have been written
    assert not (tmp_repo / ".harness" / "run-checkpoint.md").exists()
    assert not (tmp_repo / ".harness" / "invocations.ndjson").exists()


def test_runner_falls_back_to_global_when_no_packet_dir(tmp_repo: Path) -> None:
    """Without a packet directory, checkpoint/invocation go to global .harness/."""
    _write_ready_queue(tmp_repo)
    # Do NOT create docs/changes/sample-change/

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "--json",
            "runner",
            "start",
            "--executor",
            "subprocess",
            "--command",
            f'"{sys.executable}" -c "print(\\"AUTONOMOUS_READY_DONE\\")"',
            "--max-rounds",
            "1",
        ],
    )
    assert result.exit_code == 0, result.output
    # Global paths should be used
    assert (tmp_repo / ".harness" / "run-checkpoint.md").is_file()
    assert (tmp_repo / ".harness" / "invocations.ndjson").is_file()


# ---------------------------------------------------------------------------
# runner start -- subprocess without --command (line 191)
# ---------------------------------------------------------------------------


def test_runner_start_subprocess_no_command_raises(tmp_repo: Path) -> None:
    """Subprocess executor without --command should raise ClickException."""
    _write_ready_queue(tmp_repo)
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
        ],
    )
    assert result.exit_code != 0
    assert "--command is required" in result.output


# ---------------------------------------------------------------------------
# runner start -- orchestrator executor (lines 150-185)
# ---------------------------------------------------------------------------


def test_runner_start_orchestrator_stdout(tmp_repo: Path) -> None:
    """Orchestrator mode outputs prompt text to stdout."""
    _write_ready_queue(tmp_repo)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "runner",
            "start",
            "--executor",
            "orchestrator",
        ],
    )
    assert result.exit_code == 0, result.output
    # The orchestrator prompt should reference the queue item
    assert "Test task" in result.output


def test_runner_start_orchestrator_output_file(tmp_repo: Path) -> None:
    """Orchestrator mode with --output writes prompt to a file."""
    _write_ready_queue(tmp_repo)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "runner",
            "start",
            "--executor",
            "orchestrator",
            "--output",
            "orchestrator-prompt.md",
        ],
    )
    assert result.exit_code == 0, result.output
    out_path = tmp_repo / "orchestrator-prompt.md"
    assert out_path.is_file()
    content = out_path.read_text(encoding="utf-8")
    assert "Test task" in content
    assert "Orchestrator prompt written to" in result.output


def test_runner_start_orchestrator_missing_variables(tmp_repo: Path) -> None:
    """Orchestrator mode reports unresolved variables when context is sparse."""
    # Minimal queue item with no change packet -> many template vars unresolved
    (tmp_repo / "NEXT.md").write_text(
        "[ready] Minimal task\n",
        encoding="utf-8",
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
            "orchestrator",
        ],
    )
    assert result.exit_code == 0, result.output
    # Warning about unresolved variables (sent to stderr, mixed into output)
    assert "unresolved variables" in result.output


# ---------------------------------------------------------------------------
# runner start -- exit code 1 on failure (lines 244-245)
# ---------------------------------------------------------------------------


def test_runner_start_exit_code_1_on_failure(tmp_repo: Path) -> None:
    """A command that emits AUTONOMOUS_FAILED should produce exit code 1."""
    _write_ready_queue(tmp_repo)
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
            f'"{sys.executable}" -c "print(\\"AUTONOMOUS_FAILED\\")"',
            "--max-rounds",
            "1",
        ],
    )
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# runner render (lines 251-329)
# ---------------------------------------------------------------------------


def test_runner_render_implementer(tmp_repo: Path) -> None:
    """Render the implementer role with a valid queue item."""
    _write_ready_queue(tmp_repo)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "runner",
            "render",
            "--role",
            "implementer",
        ],
    )
    assert result.exit_code == 0, result.output
    # Should produce rendered template output (non-empty)
    assert len(result.output.strip()) > 0


def test_runner_render_output_file(tmp_repo: Path) -> None:
    """Render with --output writes the rendered prompt to a file."""
    _write_ready_queue(tmp_repo)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "runner",
            "render",
            "--role",
            "implementer",
            "--output",
            "rendered-prompt.md",
        ],
    )
    assert result.exit_code == 0, result.output
    out_path = tmp_repo / "rendered-prompt.md"
    assert out_path.is_file()
    content = out_path.read_text(encoding="utf-8")
    assert len(content) > 0
    assert "Rendered implementer prompt written to" in result.output


def test_runner_render_no_ready_items(tmp_repo: Path) -> None:
    """Render with no ready/active items should raise ClickException."""
    (tmp_repo / "NEXT.md").write_text(
        "[blocked] Nothing to do\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "runner",
            "render",
            "--role",
            "implementer",
        ],
    )
    assert result.exit_code != 0
    assert "No [ready] or [active] item" in result.output


# ---------------------------------------------------------------------------
# runner parse-result (lines 332-404)
# ---------------------------------------------------------------------------

_SUBAGENT_RESULT = {
    "role": "implementer",
    "filesChanged": ["src/main.py"],
    "contractBlocked": False,
    "verdict": "acceptable",
    "verificationPassed": True,
    "findings": [],
}


def test_runner_parse_result_from_file(tmp_repo: Path) -> None:
    """Parse a JSON subagent result from --input file and echo summary."""
    input_file = tmp_repo / "result.json"
    input_file.write_text(json.dumps(_SUBAGENT_RESULT), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "runner",
            "parse-result",
            "--role",
            "implementer",
            "--input",
            "result.json",
        ],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["role"] == "implementer"
    assert data["filesChanged"] == ["src/main.py"]
    assert data["contractBlocked"] is False
    assert data["verdict"] == "acceptable"
    assert data["findingsCount"] == 0


def test_runner_parse_result_appends_invocation_log(tmp_repo: Path) -> None:
    """parse-result should append an NDJSON entry to the invocation log."""
    input_file = tmp_repo / "result.json"
    input_file.write_text(json.dumps(_SUBAGENT_RESULT), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "runner",
            "parse-result",
            "--role",
            "implementer",
            "--input",
            "result.json",
            "--invocation-log",
            ".harness/invocations.ndjson",
            "--round",
            "3",
        ],
    )
    assert result.exit_code == 0, result.output

    log_path = tmp_repo / ".harness" / "invocations.ndjson"
    assert log_path.is_file()
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    record = json.loads(lines[0])
    assert record["role"] == "implementer"
    assert record["round"] == 3
    assert record["filesChanged"] == ["src/main.py"]
