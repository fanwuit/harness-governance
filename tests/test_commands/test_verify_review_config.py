"""Tests for ``harness verify``, ``harness review``, and ``harness config``."""

from __future__ import annotations

import sys
from pathlib import Path

from click.testing import CliRunner

from harness_governance.cli import cli
from harness_governance.commands import verify as verify_module


def test_verify_routing_preset_passes(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "verify", "routing-guardrails"],
    )
    assert result.exit_code == 0, result.output


def test_verify_unknown_preset_fails(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "verify", "no-such-preset"],
    )
    assert result.exit_code != 0
    assert "Unknown preset" in result.output


def test_verify_all_local_checks_passes(tmp_repo: Path) -> None:
    (tmp_repo / "README.md").write_text(
        "# README\n\n| x | x | x | x | 是 | x |\n\n启用的非 system skills：0 个\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "verify", "all-local-checks"],
    )
    assert result.exit_code == 0, result.output


def test_verify_local_release_runs_release_steps(
    tmp_repo: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        verify_module,
        "_RELEASE_COMMANDS",
        ((sys.executable, "-c", "print('release step ok')"),),
    )
    monkeypatch.setattr(verify_module, "_verify_wheel_contents", lambda root: True)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "verify", "local", "--release"],
    )
    assert result.exit_code == 0, result.output
    assert "verify local --release: passed" in result.output


def test_verify_local_release_fails_on_step(
    tmp_repo: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        verify_module,
        "_RELEASE_COMMANDS",
        ((sys.executable, "-c", "raise SystemExit(3)"),),
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "verify", "local", "--release"],
    )
    assert result.exit_code == 1, result.output
    assert "verify local --release: failed" in result.output


def test_review_close_writes_checkpoint(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "review",
            "close",
            "task-1",
            "--evidence",
            "pytest -q",
            "--evidence",
            "all checks green",
            "--risk",
            "scope creep",
            "--next-resume",
            "NEXT.md [ready] task-2",
        ],
    )
    assert result.exit_code == 0, result.output
    checkpoint = (tmp_repo / ".harness" / "run-checkpoint.md").read_text(
        encoding="utf-8"
    )
    assert "task-1" in checkpoint
    assert "pytest -q" in checkpoint
    assert "scope creep" in checkpoint


def test_config_init_writes_file(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "config", "init"],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_repo / ".harness" / "config.toml").is_file()


def test_config_init_force_overwrites(tmp_repo: Path) -> None:
    runner = CliRunner()
    runner.invoke(cli, ["--project-root", str(tmp_repo), "config", "init"])
    (tmp_repo / ".harness" / "config.toml").write_text("# custom\n", encoding="utf-8")
    runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "config", "init", "--force"],
    )
    text = (tmp_repo / ".harness" / "config.toml").read_text(encoding="utf-8")
    assert "# custom" not in text
