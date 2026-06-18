"""Tests for ergonomic top-level alias commands."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from harness_governance.cli import cli
from harness_governance.session import SessionState, create_session
from harness_governance.state_machine.classification import RoutingPath
from harness_governance.state_machine.layers import HarnessLayer


def test_start_alias_invokes_governed_start(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "--json",
            "start",
            "Expose new /v2/widgets endpoint",
            "--files",
            "src/api.py",
            "--contracts",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["path"] == "governed-path"
    assert payload["current_layer"] == "intake-orientation"
    assert payload["next_layer"] == "idea"


def test_next_alias_reports_active_session(tmp_repo: Path) -> None:
    state = SessionState(
        session_id="alias-next-test",
        created_at="2026-06-18T10:00:00+00:00",
        description="Alias next test",
        routing_path=RoutingPath.GOVERNED_PATH,
        current_layer=HarnessLayer.INTAKE_ORIENTATION,
        rigor_tier="strict",
    )
    create_session(tmp_repo, state)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "--json", "next"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["session_id"] == "alias-next-test"
    assert payload["current_layer"] == "intake-orientation"
    assert payload["next_layer"] == "idea"
    assert payload["gate_passed"] is False
    assert payload["recommended_next_command"] == "harness layer guide intake-orientation"


def test_next_alias_requires_active_session(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--project-root", str(tmp_repo), "next"])
    assert result.exit_code != 0
    assert "No active" in result.output or "没有活跃" in result.output


def test_ship_alias_does_not_publish_and_fails_without_session(tmp_repo: Path) -> None:
    (tmp_repo / "README.md").write_text("# Test repo\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "--json", "ship"],
    )
    assert result.exit_code == 1, result.output
    payload = json.loads(result.output)
    assert payload["published"] is False
    assert payload["session_id"] is None
    assert payload["passed"] is False

