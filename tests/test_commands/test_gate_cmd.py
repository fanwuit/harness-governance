"""Tests for ``harness gate`` CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from harness_governance.cli import cli
from harness_governance.commands.gate_failure import format_gate_failure_guidance
from harness_governance.models.schemas import GateStatus
from harness_governance.session import SessionState, create_session
from harness_governance.state_machine.classification import RoutingPath
from harness_governance.state_machine.layers import HarnessLayer


_INTAKE_QA: tuple[dict[str, str], ...] = (
    {
        "layer": "intake-orientation",
        "question": "Q1",
        "answer": "A1",
        "timestamp": "2026-06-16T10:00:00Z",
    },
    {
        "layer": "intake-orientation",
        "question": "Q2",
        "answer": "A2",
        "timestamp": "2026-06-16T10:00:01Z",
    },
    {
        "layer": "intake-orientation",
        "question": "Q3",
        "answer": "A3",
        "timestamp": "2026-06-16T10:00:02Z",
    },
    {
        "layer": "intake-orientation",
        "question": "Q4",
        "answer": "A4",
        "timestamp": "2026-06-16T10:00:03Z",
    },
)


def _seed_gate_session(tmp_path: Path, **overrides) -> str:
    kwargs = dict(
        session_id="gate-test-session",
        created_at="2026-06-16T10:00:00+00:00",
        description="Gate test",
        routing_path=RoutingPath.GOVERNED_PATH,
        current_layer=HarnessLayer.INTAKE_ORIENTATION,
        layer_qa=_INTAKE_QA,
    )
    kwargs.update(overrides)
    state = SessionState(**kwargs)
    create_session(tmp_path, state)
    return kwargs["session_id"]


class TestGateCheck:
    def test_check_passes_with_sufficient_qa(self, tmp_path: Path) -> None:
        _seed_gate_session(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "gate", "check", "intake-orientation"],
        )
        assert result.exit_code == 0, result.output
        assert "PASSED" in result.output or "通过" in result.output

    def test_check_fails_without_qa(self, tmp_path: Path) -> None:
        _seed_gate_session(tmp_path, layer_qa=())
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "gate", "check", "intake-orientation"],
        )
        assert result.exit_code == 1, result.output
        assert "FAILED" in result.output or "失败" in result.output
        assert "0/4 问题已答" in result.output or "Questions answered: 0/4" in result.output
        assert "Red flags we do not accept" in result.output
        assert "Required actions" in result.output
        assert "harness layer guide intake-orientation" in result.output
        assert "harness gate check intake-orientation" in result.output
        assert "Choices:" in result.output

    def test_check_no_session(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "gate", "check", "intake-orientation"],
        )
        assert result.exit_code == 1

    def test_check_invalid_layer(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "gate", "check", "not-a-layer"],
        )
        assert result.exit_code != 0

    def test_check_json_output(self, tmp_path: Path) -> None:
        _seed_gate_session(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root",
                str(tmp_path),
                "--json",
                "gate",
                "check",
                "intake-orientation",
            ],
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["passed"] is True
        assert data["layer"] == "intake-orientation"

    def test_check_failed_json_output_has_no_prose_guidance(
        self, tmp_path: Path
    ) -> None:
        _seed_gate_session(tmp_path, layer_qa=())
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root",
                str(tmp_path),
                "--json",
                "gate",
                "check",
                "intake-orientation",
            ],
        )
        assert result.exit_code == 1, result.output
        data = json.loads(result.output)
        assert data["passed"] is False
        assert data["layer"] == "intake-orientation"
        assert "Red flags we do not accept" not in result.output
        assert "Required actions" not in result.output

    def test_gate_failure_guidance_deduplicates_repeated_items(self) -> None:
        status = GateStatus(
            layer=HarnessLayer.CONTRACT,
            passed=False,
            questions_answered=4,
            questions_required=4,
            artifacts_found=(),
            artifacts_missing=("docs/contracts/*.md", "docs/contracts/*.md"),
            confirmation_items_unmet=("Missing schema", "Missing schema"),
            blocking_artifacts_missing=("contract.lock", "contract.lock"),
        )

        output = "\n".join(format_gate_failure_guidance("contract", status))

        assert output.count("docs/contracts/*.md") == 1
        assert output.count("Missing schema") == 1
        assert output.count("contract.lock") == 1
        assert "Choices:" in output

    def test_check_writes_lock_file(self, tmp_path: Path) -> None:
        _seed_gate_session(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "gate", "check", "intake-orientation"],
        )
        assert result.exit_code == 0
        lock = tmp_path / ".harness" / "gates" / "01-intake-orientation.lock"
        assert lock.is_file()


class TestGateStatus:
    def test_status_shows_all_layers(self, tmp_path: Path) -> None:
        _seed_gate_session(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "gate", "status"],
        )
        assert result.exit_code == 0, result.output
        # Should show OPEN for all layers initially
        assert "OPEN" in result.output or "开放" in result.output

    def test_status_shows_locked_layer(self, tmp_path: Path) -> None:
        _seed_gate_session(tmp_path)
        runner = CliRunner()
        # First pass the gate check to create a lock
        runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "gate", "check", "intake-orientation"],
        )
        # Now check status
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "gate", "status", "intake-orientation"],
        )
        assert result.exit_code == 0
        assert "LOCKED" in result.output or "已锁定" in result.output

    def test_status_specific_layer(self, tmp_path: Path) -> None:
        _seed_gate_session(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "gate", "status", "idea"],
        )
        assert result.exit_code == 0

    def test_status_json_output(self, tmp_path: Path) -> None:
        _seed_gate_session(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root",
                str(tmp_path),
                "--json",
                "gate",
                "status",
                "intake-orientation",
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert data[0]["layer"] == "intake-orientation"


class TestGateReset:
    def test_reset_requires_confirmed(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "gate", "reset", "intake-orientation"],
        )
        assert result.exit_code != 0

    def test_reset_removes_lock(self, tmp_path: Path) -> None:
        _seed_gate_session(tmp_path)
        runner = CliRunner()
        # Create a lock first
        runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "gate", "check", "intake-orientation"],
        )
        lock = tmp_path / ".harness" / "gates" / "01-intake-orientation.lock"
        assert lock.is_file()

        # Reset
        result = runner.invoke(
            cli,
            [
                "--project-root",
                str(tmp_path),
                "gate",
                "reset",
                "intake-orientation",
                "--confirmed",
            ],
        )
        assert result.exit_code == 0, result.output
        assert not lock.is_file()

    def test_reset_all(self, tmp_path: Path) -> None:
        _seed_gate_session(tmp_path)
        runner = CliRunner()
        # Create locks
        from harness_governance.state_machine.gates import LockFileManager
        from harness_governance.session import find_active_session
        from harness_governance.models.schemas import GateStatus

        session = find_active_session(tmp_path)
        locks = LockFileManager(tmp_path)
        status = GateStatus(layer="test", passed=True)
        locks.write_lock(HarnessLayer.INTAKE_ORIENTATION, status, session)
        locks.write_lock(HarnessLayer.IDEA, status, session)

        result = runner.invoke(
            cli,
            [
                "--project-root",
                str(tmp_path),
                "gate",
                "reset",
                "x",
                "--confirmed",
                "--all",
            ],
        )
        assert result.exit_code == 0
        assert not locks.exists(HarnessLayer.INTAKE_ORIENTATION)
        assert not locks.exists(HarnessLayer.IDEA)

    def test_reset_nonexistent(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "gate", "reset", "idea", "--confirmed"],
        )
        assert result.exit_code == 0
        assert "no lock found" in result.output.lower() or "未找到" in result.output
