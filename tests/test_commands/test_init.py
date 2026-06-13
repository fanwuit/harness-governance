"""Tests for ``harness init``."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from harness_governance.cli import cli
from harness_governance.commands.init import detect_platform
from harness_governance.config.defaults import PLATFORM_SKILL_PATHS


def test_init_writes_config_and_skill(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--project-root", str(tmp_repo), "init"])
    assert result.exit_code == 0, result.output
    assert (tmp_repo / ".harness" / "config.toml").is_file()
    skill_path = tmp_repo / PLATFORM_SKILL_PATHS["claude-code"]
    assert skill_path.is_file()


def test_init_is_idempotent(tmp_repo: Path) -> None:
    runner = CliRunner()
    runner.invoke(cli, ["--project-root", str(tmp_repo), "init"])
    second = runner.invoke(cli, ["--project-root", str(tmp_repo), "init"])
    assert second.exit_code == 0
    assert "already exists" in second.output or "Done." in second.output


def test_init_force_overwrites_skill(tmp_repo: Path) -> None:
    runner = CliRunner()
    runner.invoke(cli, ["--project-root", str(tmp_repo), "init"])
    skill = tmp_repo / PLATFORM_SKILL_PATHS["claude-code"]
    skill.write_text("# custom\n", encoding="utf-8")
    result = runner.invoke(cli, ["--project-root", str(tmp_repo), "init", "--force"])
    assert result.exit_code == 0
    assert "custom" not in skill.read_text(encoding="utf-8")


def test_init_detects_claude_code(tmp_repo: Path) -> None:
    (tmp_repo / ".claude").mkdir()
    assert detect_platform(tmp_repo) == "claude-code"


def test_init_detects_codex(tmp_repo: Path) -> None:
    (tmp_repo / ".codex").mkdir()
    assert detect_platform(tmp_repo) == "codex"


def test_init_detects_cline(tmp_repo: Path) -> None:
    (tmp_repo / ".clinerules").mkdir()
    assert detect_platform(tmp_repo) == "cline"


def test_init_detects_cursor(tmp_repo: Path) -> None:
    (tmp_repo / ".cursor").mkdir()
    assert detect_platform(tmp_repo) == "cursor"


def test_init_detects_via_env(monkeypatch, tmp_repo: Path) -> None:
    monkeypatch.setenv("CLAUDE_CODE", "1")
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.delenv("CLINE_SESSION", raising=False)
    monkeypatch.delenv("CURSOR_TRACE_ID", raising=False)
    assert detect_platform(tmp_repo) == "claude-code"

    monkeypatch.delenv("CLAUDE_CODE", raising=False)
    monkeypatch.setenv("CODEX_HOME", "C:/codex")
    assert detect_platform(tmp_repo) == "codex"


def test_init_env_overrides_dotfiles(tmp_repo: Path, monkeypatch) -> None:
    (tmp_repo / ".claude").mkdir()
    monkeypatch.setenv("CODEX_HOME", "C:/codex")
    assert detect_platform(tmp_repo) == "codex"


def test_init_no_detect_requires_platform(tmp_repo: Path) -> None:
    from click.testing import CliRunner
    from harness_governance.cli import cli

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "init",
            "--no-detect",
        ],
    )
    assert result.exit_code != 0
    assert "--no-detect requires --platform" in result.output


def test_init_no_detect_with_platform(tmp_repo: Path) -> None:
    from click.testing import CliRunner
    from harness_governance.cli import cli

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "init",
            "--no-detect",
            "--platform",
            "codex",
        ],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_repo / ".codex" / "skills" / "harness-governance" / "SKILL.md").is_file()


def test_init_json_output(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--project-root", str(tmp_repo), "--json", "init"])
    assert result.exit_code == 0, result.output
    assert '"detected_platform"' in result.output
    assert '"config_path"' in result.output


def test_init_skip_skill(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "init", "--skip-skill"],
    )
    assert result.exit_code == 0
    assert not (tmp_repo / PLATFORM_SKILL_PATHS["claude-code"]).exists()