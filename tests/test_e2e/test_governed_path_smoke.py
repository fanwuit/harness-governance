"""End-to-end smoke tests for the public governed-path CLI flow."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from harness_governance.cli import cli


def test_strict_governed_path_minimum_smoke(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text('print("hello")\n', encoding="utf-8")
    runner = CliRunner()

    start = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_path),
            "governed-start",
            "modify persisted public api contract and deployment behavior",
            "--rigor",
            "strict",
        ],
    )
    assert start.exit_code == 0, start.output
    assert "Session created:" in start.output

    ask = runner.invoke(
        cli,
        ["--project-root", str(tmp_path), "layer", "ask", "intake-orientation"],
        input="Task boundary\nNo queue\nNo extra risks\nNew task\n",
    )
    assert ask.exit_code == 0, ask.output

    capture = runner.invoke(
        cli, ["--project-root", str(tmp_path), "tech-stack", "capture"]
    )
    assert capture.exit_code == 0, capture.output

    lint = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_path),
            "tech-stack",
            "lint",
            "Python",
            "--tool",
            "ruff",
        ],
    )
    assert lint.exit_code == 0, lint.output

    docstyle = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_path),
            "tech-stack",
            "docstyle",
            "Python",
            "--style",
            "Google docstring",
        ],
    )
    assert docstyle.exit_code == 0, docstyle.output

    gate = runner.invoke(
        cli,
        ["--project-root", str(tmp_path), "gate", "check", "intake-orientation"],
    )
    assert gate.exit_code == 0, gate.output

    advance = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_path),
            "layer",
            "advance",
            "idea",
            "--confirmed",
        ],
    )
    assert advance.exit_code == 0, advance.output
