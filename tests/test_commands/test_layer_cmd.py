"""Tests for ``harness layer advance`` and ``harness layer show``."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from harness_governance.cli import cli
from harness_governance.session import SessionState, create_session
from harness_governance.state_machine.classification import RoutingPath
from harness_governance.state_machine.layers import HarnessLayer


def _seed_session(
    tmp_path: Path,
    *,
    session_id: str = "20260616-test",
    current_layer: HarnessLayer = HarnessLayer.INTAKE_ORIENTATION,
) -> str:
    state = SessionState(
        session_id=session_id,
        created_at="2026-06-16T10:00:00+00:00",
        description="Test",
        routing_path=RoutingPath.GOVERNED_PATH,
        current_layer=current_layer,
    )
    create_session(tmp_path, state)
    return session_id


class TestLayerAdvance:
    def test_advance_allowed(self, tmp_path: Path) -> None:
        _seed_session(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "layer", "advance", "idea"],
        )
        assert result.exit_code == 0, result.output
        assert "idea" in result.output.lower() or "advanced" in result.output.lower()

    def test_advance_blocked(self, tmp_path: Path) -> None:
        _seed_session(tmp_path, current_layer=HarnessLayer.IDEA)
        runner = CliRunner()
        # IDEA -> IMPLEMENTATION should be blocked by T1.
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "layer", "advance", "implementation"],
        )
        assert result.exit_code != 0

    def test_advance_same_layer(self, tmp_path: Path) -> None:
        _seed_session(tmp_path, current_layer=HarnessLayer.IDEA)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "layer", "advance", "idea"],
        )
        assert result.exit_code == 0
        assert "already" in result.output.lower() or "已在" in result.output

    def test_advance_no_session(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "layer", "advance", "idea"],
        )
        assert result.exit_code != 0

    def test_advance_json_output(self, tmp_path: Path) -> None:
        _seed_session(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "--json", "layer", "advance", "idea"],
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["allowed"] is True
        assert data["to_layer"] == "idea"

    def test_advance_with_context_flags(self, tmp_path: Path) -> None:
        _seed_session(tmp_path, current_layer=HarnessLayer.ARCHITECTURE)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "layer", "advance", "contract",
                "--boundary-touch",
            ],
        )
        assert result.exit_code == 0, result.output

    def test_advance_records_transition(self, tmp_path: Path) -> None:
        sid = _seed_session(tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["--project-root", str(tmp_path), "layer", "advance", "idea"])
        # Verify the session file was updated with the transition.
        from harness_governance.session import load_session

        state = load_session(tmp_path, sid)
        assert len(state.transitions) == 1
        assert state.transitions[0].from_layer == HarnessLayer.INTAKE_ORIENTATION
        assert state.transitions[0].to_layer == HarnessLayer.IDEA


class TestLayerShow:
    def test_show_active(self, tmp_path: Path) -> None:
        _seed_session(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "layer", "show"],
        )
        assert result.exit_code == 0
        assert "intake-orientation" in result.output

    def test_show_no_session(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "layer", "show"],
        )
        assert result.exit_code != 0

    def test_show_json(self, tmp_path: Path) -> None:
        _seed_session(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "--json", "layer", "show"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["current_layer"] == "intake-orientation"
