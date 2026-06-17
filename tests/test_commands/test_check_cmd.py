"""Tests for ``harness check``."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from harness_governance.cli import cli
from harness_governance.commands.check import (
    _check_self_docs,
    check_inventory,
    check_routing,
)
from harness_governance import __version__ as _current_version


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
    from tests.conftest import seed_session

    seed_session(tmp_repo)
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


# ---------------------------------------------------------------------------
# check docs --self tests
# ---------------------------------------------------------------------------


def test_self_check_catches_changelog_version_mismatch(tmp_repo: Path) -> None:
    """--self flags when CHANGELOG version doesn't match __version__."""
    (tmp_repo / "CHANGELOG.md").write_text(
        "## [0.0.1] - 2020-01-01\n\nOld version.\n",
        encoding="utf-8",
    )
    findings = _check_self_docs(tmp_repo, "0.7.1")
    assert any("CHANGELOG" in f.target for f in findings)


def test_self_check_catches_missing_i18n_key(tmp_repo: Path) -> None:
    """--self flags when bilingual() key is not in messages.py catalog."""
    messages_dir = tmp_repo / "src" / "harness_governance"
    messages_dir.mkdir(parents=True, exist_ok=True)
    (messages_dir / "messages.py").write_text(
        "_MESSAGES = {}\n",
        encoding="utf-8",
    )
    src_file = messages_dir / "fake_cmd.py"
    src_file.write_text(
        'bilingual("missing.key", x=1)\n',
        encoding="utf-8",
    )
    findings = _check_self_docs(tmp_repo, "0.7.1")
    assert any("missing.key" in f.message for f in findings)


def test_self_check_catches_skill_version_mismatch(tmp_repo: Path) -> None:
    """--self flags when skill version sentinel doesn't match package version."""
    skills_dir = tmp_repo / "src" / "harness_governance" / "data" / "skills" / "strict"
    skills_dir.mkdir(parents=True, exist_ok=True)
    (skills_dir / "claude-code.md").write_text(
        "<!-- harness-skill-version: 0.6.0 -->\n\n# Skill\n",
        encoding="utf-8",
    )
    findings = _check_self_docs(tmp_repo, "0.7.1")
    assert any("0.6.0" in f.message and "0.7.1" in f.message for f in findings)


def test_self_check_passes_on_clean_project(tmp_repo: Path) -> None:
    """--self passes when docs are in sync."""
    (tmp_repo / "CHANGELOG.md").write_text(
        f"## [{_current_version}] - 2026-06-16\n\nStuff.\n",
        encoding="utf-8",
    )
    findings = _check_self_docs(tmp_repo, _current_version)
    errors = [f for f in findings if f.level == "error"]
    assert not errors, [f.message for f in errors]


def test_docs_self_cli_flag(tmp_repo: Path) -> None:
    """harness check docs --self exits 0 on clean project."""
    (tmp_repo / "CHANGELOG.md").write_text(
        f"## [{_current_version}] - 2026-06-16\n\nStuff.\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "check", "docs", "--self"],
    )
    assert result.exit_code == 0, result.output
