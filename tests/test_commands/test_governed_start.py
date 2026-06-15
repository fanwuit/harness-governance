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