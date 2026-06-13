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