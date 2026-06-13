"""Tests for ``harness check``."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from harness_governance.cli import cli
from harness_governance.commands.check import check_inventory, check_routing


def test_check_routing_flags_missing_precondition(tmp_repo: Path) -> None:
    skill_dir = tmp_repo / "demo-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "# Demo Skill\n\nNo Harness Precondition block here.\n", encoding="utf-8"
    )
    result = check_routing(tmp_repo)
    assert not result.passed
    assert any("Harness Precondition" in f.message for f in result.findings)


def test_check_inventory_passes_when_readme_matches(tmp_repo: Path) -> None:
    skill_dir = tmp_repo / "demo-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: demo-skill\ndescription: x\n---\n\n## Harness Precondition\n\nx.\n",
        encoding="utf-8",
    )
    (tmp_repo / "README.md").write_text(
        "# README\n\n| x | x | `demo-skill` | x | 是 | x |\n",
        encoding="utf-8",
    )
    result = check_inventory(tmp_repo)
    assert result.passed, [f.message for f in result.findings]


def test_check_inventory_flags_missing_readme(tmp_repo: Path) -> None:
    result = check_inventory(tmp_repo)
    assert not result.passed
    assert any("README.md" in f.message for f in result.findings)


def test_check_routing_cli(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--project-root", str(tmp_repo), "check", "routing"])
    # No skills → no precondition errors → passes.
    assert result.exit_code == 0, result.output


def test_check_packets_cli(tmp_repo: Path) -> None:
    runner = CliRunner()
    runner.invoke(cli, ["--project-root", str(tmp_repo), "packet", "init", "x"])
    result = runner.invoke(cli, ["--project-root", str(tmp_repo), "check", "packets"])
    assert result.exit_code == 1
    assert "packets check failed" in result.output


def test_check_all_cli(tmp_repo: Path) -> None:
    # Provide a README matching on-disk skills so inventory check passes.
    (tmp_repo / "README.md").write_text(
        "# README\n\n| x | x | x | x | 是 | x |\n\n启用的非 system skills：0 个\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "--json", "check", "all"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["check"] == "all"


def test_check_inventory_handles_count_drift(tmp_repo: Path) -> None:
    skill_dir = tmp_repo / "demo-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: demo-skill\ndescription: x\n---\n\n## Harness Precondition\n\nx.\n",
        encoding="utf-8",
    )
    (tmp_repo / "README.md").write_text(
        "# README\n\n| x | x | `demo-skill` | x | 是 | x |\n\n启用的非 system skills：99 个\n",
        encoding="utf-8",
    )
    result = check_inventory(tmp_repo)
    assert not result.passed
    assert any("count" in f.message for f in result.findings)