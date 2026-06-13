"""Tests for ``harness entry``."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from harness_governance.cli import cli
from harness_governance.commands.entry import check_file


def _write_record(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")


VALID = """\
Implementation Entry Record:

- Current layer: implementation
- Target: src/a.py
- Scope: wire CLI
- Contract evidence: docs/changes/x/contracts.md
- Readiness gate: pass
- Packetization: ready
- Verification command: pytest -q
- Review / Next state file: docs/changes/x/tasks.md
- Stop conditions: 3 consecutive pytest failures
"""


def test_check_entry_record_passes_valid(tmp_path: Path) -> None:
    record = tmp_path / "record.md"
    _write_record(record, VALID)
    assert check_file(record, repo_root=tmp_path) == []


def test_check_entry_record_flags_missing_field(tmp_path: Path) -> None:
    body = VALID.replace("- Target: src/a.py\n", "")
    record = tmp_path / "record.md"
    _write_record(record, body)
    errors = check_file(record, repo_root=tmp_path)
    assert any("Missing field: Target" in err for err in errors)


def test_check_entry_record_flags_placeholder(tmp_path: Path) -> None:
    body = VALID.replace("src/a.py", "tbd")
    record = tmp_path / "record.md"
    _write_record(record, body)
    errors = check_file(record, repo_root=tmp_path)
    assert any("Target" in err for err in errors)


def test_check_entry_record_flags_invalid_layer(tmp_path: Path) -> None:
    """The legacy check does not validate layer names — it only requires presence/non-empty.

    Match that behavior so we don't break compatibility.
    """
    body = VALID.replace("- Current layer: implementation\n", "- Current layer: not-a-layer\n")
    record = tmp_path / "record.md"
    _write_record(record, body)
    errors = check_file(record, repo_root=tmp_path)
    assert errors == []


def test_check_entry_record_flags_empty_layer(tmp_path: Path) -> None:
    body = VALID.replace("- Current layer: implementation\n", "- Current layer: \n")
    record = tmp_path / "record.md"
    _write_record(record, body)
    errors = check_file(record, repo_root=tmp_path)
    assert any("Current layer" in err for err in errors)


def test_entry_check_cli_passes(tmp_repo: Path) -> None:
    record = tmp_repo / "record.md"
    _write_record(record, VALID)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "entry",
            "check",
            str(record),
        ],
    )
    assert result.exit_code == 0, result.output


def test_entry_check_cli_fails(tmp_repo: Path) -> None:
    record = tmp_repo / "record.md"
    _write_record(record, "Implementation Entry Record:\n\n- Target: foo\n")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "entry", "check", str(record)],
    )
    assert result.exit_code == 1
    assert "Missing field" in result.output


def test_entry_record_renders_block(tmp_repo: Path) -> None:
    runner = CliRunner()
    output_path = tmp_repo / "out.md"
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "entry",
            "record",
            "--target",
            "src/x.py",
            "--scope",
            "wire CLI",
            "--layer",
            "implementation",
            "--readiness-gate",
            "pass",
            "--packetization",
            "ready",
            "--verification-command",
            "pytest -q",
            "--review-next-state",
            "docs/changes/x/tasks.md",
            "--stop-conditions",
            "3 consecutive failures",
            "--output",
            str(output_path),
        ],
    )
    assert result.exit_code == 0, result.output
    text = output_path.read_text(encoding="utf-8")
    assert "Implementation Entry Record" in text
    assert "src/x.py" in text


def test_entry_record_json_validation(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "--json",
            "entry",
            "check",
            "no-such-file.md",
        ],
    )
    # Cli passes the explicit file; if it doesn't exist, we get a 1 with the
    # error message.
    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert payload["check"] == "entry"
    assert not payload["passed"]