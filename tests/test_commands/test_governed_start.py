"""Tests for ``harness governed-start``."""

from __future__ import annotations

from pathlib import Path

import json

from click.testing import CliRunner

from harness_governance.cli import cli


def test_governed_start_classifies_qa_as_fast() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--project-root", ".", "governed-start", "What does this skill do?"])
    assert result.exit_code == 0, result.output
    assert "fast-path" in result.output


def test_governed_start_classifies_rename_as_trivial(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "governed-start",
            "Rename local variable foo to bar in src/a.py",
            "--files",
            "src/a.py",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "trivial-safe-change" in result.output


def test_governed_start_classifies_public_api_as_governed(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "governed-start",
            "Expose new /v2/widgets endpoint",
            "--files",
            "src/api.py",
            "--contracts",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "governed-path" in result.output
    assert "Disclosure" in result.output


def test_governed_start_warns_on_stale_skill(tmp_repo: Path, monkeypatch) -> None:
    """When the on-disk skill is older than the installed template,
    governed-start must surface a `skill_version_warning` in both
    text and JSON output so the user (or a wrapping agent) sees the
    staleness at entry time, not after a full Governed run.
    """
    from harness_governance.commands import init as init_mod
    from harness_governance.config.defaults import PLATFORM_SKILL_PATHS

    new_template = (
        "---\nname: harness-governance\ndescription: new\n---\n\n"
        "<!-- harness-skill-version: 9.9.9 -->\nbody"
    )
    monkeypatch.setattr(init_mod, "load_skill_template", lambda p: new_template)

    # Lay down an old (no-sentinel) skill file for codex.
    skill_path = tmp_repo / PLATFORM_SKILL_PATHS["codex"]
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text("---\nname: x\n---\nold\n", encoding="utf-8")

    # Need the .agents/ marker so detect_platform finds codex.
    (tmp_repo / ".agents").mkdir(exist_ok=True)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "--json",
            "governed-start",
            "What does this skill do?",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["skill_version_warning"] is not None
    assert "codex" in payload["skill_version_warning"]
    assert "9.9.9" in payload["skill_version_warning"]


def test_governed_start_includes_companions(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "--json",
            "governed-start",
            "Add new persistence layer",
            "--files",
            "src/db.py",
            "--external",
            "--companion",
            "superpowers:subagent-driven-development",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["path"] == "governed-path"
    assert "superpowers:subagent-driven-development" in payload["disclosure"]


# ---------------------------------------------------------------------------
# Friction reduction: fast-path and trivial lightweight output
# ---------------------------------------------------------------------------


def test_fast_path_minimal_output() -> None:
    """Fast-path produces a one-liner + recommendation, no disclosure block."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--project-root", ".", "governed-start", "What does this skill do?"])
    assert result.exit_code == 0, result.output
    assert "fast-path" in result.output.lower()
    # Should NOT contain the full disclosure block
    assert "Disclosure" not in result.output
    # Should contain the recommendation
    assert "directly" in result.output.lower() or "直接" in result.output


def test_fast_path_verbose_shows_full_disclosure() -> None:
    """--verbose forces full disclosure block even for fast-path."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", ".", "--verbose", "governed-start", "What does this skill do?"],
    )
    assert result.exit_code == 0, result.output
    assert "Disclosure" in result.output


def test_trivial_compact_output(tmp_repo: Path) -> None:
    """Trivial path produces compact output without disclosure block."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "governed-start",
            "Rename local variable foo to bar in src/a.py",
            "--files",
            "src/a.py",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "trivial-safe-change" in result.output
    # Should NOT contain full disclosure block
    assert "Disclosure" not in result.output
    # Recommendation should mention direct action without requiring queue
    assert "directly" in result.output.lower() or "直接" in result.output