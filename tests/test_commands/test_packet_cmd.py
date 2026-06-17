"""Tests for ``harness packet {init,check}``."""

from __future__ import annotations

from pathlib import Path

import json

from click.testing import CliRunner

from harness_governance.cli import cli
from tests.conftest import seed_session


def _fill_valid_packet(packet_dir: Path) -> None:
    """Fill the verification/contracts files so the packet passes check."""
    (packet_dir / "contracts.md").write_text(
        "# Contracts\n\n- Artifact: schema\n- Path: schema.json\n",
        encoding="utf-8",
    )
    (packet_dir / "verification.md").write_text(
        "# Verification\n\n## Commands\n\n- pytest -q\n\n## Results\n\n- pass\n",
        encoding="utf-8",
    )


def test_packet_init_creates_files(tmp_repo: Path) -> None:
    seed_session(tmp_repo)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "packet", "init", "demo-change"],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_repo / "docs" / "changes" / "demo-change").is_dir()


def test_packet_init_rejects_unsafe_id(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "packet", "init", "../escape"],
    )
    assert result.exit_code != 0


def test_packet_init_rejects_archive_id(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "packet", "init", "archive"],
    )
    assert result.exit_code != 0


def test_packet_check_rejects_fresh_packet(tmp_repo: Path) -> None:
    """A freshly-initialized packet must fail until contracts/verification are filled.

    This matches the legacy ``change-packet.test.mjs`` behavior.
    """
    seed_session(tmp_repo)
    runner = CliRunner()
    runner.invoke(cli, ["--project-root", str(tmp_repo), "packet", "init", "draft"])
    result = runner.invoke(cli, ["--project-root", str(tmp_repo), "packet", "check"])
    assert result.exit_code == 1
    assert "contracts.md" in result.output or "verification.md" in result.output


def test_packet_check_passes_when_filled(tmp_repo: Path) -> None:
    seed_session(tmp_repo)
    runner = CliRunner()
    runner.invoke(cli, ["--project-root", str(tmp_repo), "packet", "init", "ok"])
    _fill_valid_packet(tmp_repo / "docs" / "changes" / "ok")
    result = runner.invoke(cli, ["--project-root", str(tmp_repo), "packet", "check"])
    assert result.exit_code == 0, result.output


def test_packet_check_fails_invalid(tmp_repo: Path) -> None:
    seed_session(tmp_repo)
    runner = CliRunner()
    runner.invoke(cli, ["--project-root", str(tmp_repo), "packet", "init", "broken"])
    (tmp_repo / "docs" / "changes" / "broken" / "tasks.md").write_text(
        "# Tasks\nNo checklist items here.\n", encoding="utf-8"
    )
    result = runner.invoke(cli, ["--project-root", str(tmp_repo), "packet", "check"])
    assert result.exit_code == 1
    assert "checkbox" in result.output


def test_packet_check_json(tmp_repo: Path) -> None:
    seed_session(tmp_repo)
    runner = CliRunner()
    runner.invoke(cli, ["--project-root", str(tmp_repo), "packet", "init", "ok2"])
    _fill_valid_packet(tmp_repo / "docs" / "changes" / "ok2")
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "--json",
            "packet",
            "check",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["passed"] is True
    assert payload["inspected"] == 1


def test_packet_check_handles_no_packets(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--project-root", str(tmp_repo), "packet", "check"])
    assert result.exit_code == 0
    assert "no change packets" in result.output


def test_packet_init_json(tmp_repo: Path) -> None:
    seed_session(tmp_repo)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "--json",
            "packet",
            "init",
            "json-change",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["change_id"] == "json-change"
    assert set(payload["created_files"]) == {
        "proposal.md",
        "design.md",
        "tasks.md",
        "contracts.md",
        "verification.md",
    }
