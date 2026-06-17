"""Tests for ``harness session {show,list,close}``."""

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
    status: str = "active",
) -> str:
    state = SessionState(
        session_id=session_id,
        created_at="2026-06-16T10:00:00+00:00",
        description="Test session",
        routing_path=RoutingPath.GOVERNED_PATH,
        current_layer=HarnessLayer.INTAKE_ORIENTATION,
        status=status,
    )
    create_session(tmp_path, state)
    return session_id


class TestSessionShow:
    def test_show_active(self, tmp_path: Path) -> None:
        _seed_session(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "session", "show"],
        )
        assert result.exit_code == 0
        assert "20260616-test" in result.output
        assert "active" in result.output

    def test_show_by_id(self, tmp_path: Path) -> None:
        _seed_session(tmp_path, session_id="20260616-specific")
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "session", "show", "20260616-specific"],
        )
        assert result.exit_code == 0
        assert "20260616-specific" in result.output

    def test_show_missing(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "session", "show", "nonexistent"],
        )
        assert result.exit_code != 0

    def test_show_json(self, tmp_path: Path) -> None:
        _seed_session(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "--json", "session", "show"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["session_id"] == "20260616-test"
        assert data["status"] == "active"


class TestSessionList:
    def test_list_empty(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "session", "list"],
        )
        assert result.exit_code == 0
        assert "no sessions" in result.output.lower() or "未找到" in result.output

    def test_list_multiple(self, tmp_path: Path) -> None:
        _seed_session(tmp_path, session_id="20260616-a")
        _seed_session(tmp_path, session_id="20260616-b", status="closed")
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "session", "list"],
        )
        assert result.exit_code == 0
        assert "20260616-a" in result.output
        assert "20260616-b" in result.output


class TestSessionClose:
    def test_close_active(self, tmp_path: Path) -> None:
        _seed_session(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "session", "close", "20260616-test"],
        )
        assert result.exit_code == 0
        assert "closed" in result.output.lower() or "已关闭" in result.output

    def test_close_already_closed(self, tmp_path: Path) -> None:
        _seed_session(tmp_path, status="closed")
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "session", "close", "20260616-test"],
        )
        assert result.exit_code == 0
        assert "already" in result.output.lower() or "已关闭" in result.output

    def test_close_missing(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "session", "close", "nonexistent"],
        )
        assert result.exit_code != 0

    def test_close_json(self, tmp_path: Path) -> None:
        _seed_session(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root",
                str(tmp_path),
                "--json",
                "session",
                "close",
                "20260616-test",
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "closed"
