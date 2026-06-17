"""Tests for ``harness plan``."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from harness_governance.cli import cli
from harness_governance.file_ops.plan import resolve_active_plan


def test_plan_init_creates_session(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "plan", "init", "phase-b"],
    )
    assert result.exit_code == 0, result.output
    assert resolve_active_plan(tmp_repo) is not None


def test_plan_init_uses_template(tmp_repo: Path) -> None:
    runner = CliRunner()
    runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "plan",
            "init",
            "phase-b",
            "--template",
            "analytics",
        ],
    )
    session = resolve_active_plan(tmp_repo)
    assert session is not None
    assert session.plan_id.endswith("phase-b")


def test_plan_attest_records_sha256(tmp_repo: Path) -> None:
    runner = CliRunner()
    runner.invoke(cli, ["--project-root", str(tmp_repo), "plan", "init", "p"])
    result = runner.invoke(cli, ["--project-root", str(tmp_repo), "plan", "attest"])
    assert result.exit_code == 0, result.output
    assert "SHA-256" in result.output


def test_plan_show_returns_digest(tmp_repo: Path) -> None:
    runner = CliRunner()
    runner.invoke(cli, ["--project-root", str(tmp_repo), "plan", "init", "p"])
    runner.invoke(cli, ["--project-root", str(tmp_repo), "plan", "attest"])
    result = runner.invoke(cli, ["--project-root", str(tmp_repo), "plan", "show"])
    assert result.exit_code == 0, result.output
    assert "SHA-256" in result.output


def test_plan_clear_removes_attestation(tmp_repo: Path) -> None:
    runner = CliRunner()
    runner.invoke(cli, ["--project-root", str(tmp_repo), "plan", "init", "p"])
    runner.invoke(cli, ["--project-root", str(tmp_repo), "plan", "attest"])
    result = runner.invoke(cli, ["--project-root", str(tmp_repo), "plan", "clear"])
    assert result.exit_code == 0, result.output
    show = runner.invoke(cli, ["--project-root", str(tmp_repo), "plan", "show"])
    assert show.exit_code != 0


def test_plan_complete_reports_incomplete(tmp_repo: Path) -> None:
    runner = CliRunner()
    runner.invoke(cli, ["--project-root", str(tmp_repo), "plan", "init", "p"])
    result = runner.invoke(cli, ["--project-root", str(tmp_repo), "plan", "complete"])
    assert result.exit_code == 1
    assert "not all phases" in result.output


def test_plan_init_json(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "--json",
            "plan",
            "init",
            "json-test",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "plan_id" in result.output
