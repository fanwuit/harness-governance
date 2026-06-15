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


# ---------------------------------------------------------------------------
# Phase 1: scaffolding + cursor bug fix
# ---------------------------------------------------------------------------

def test_init_creates_next_md(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--project-root", str(tmp_repo), "init"])
    assert result.exit_code == 0, result.output
    next_file = tmp_repo / "NEXT.md"
    assert next_file.is_file()
    content = next_file.read_text(encoding="utf-8")
    assert "Status labels" in content
    assert "[ready]" in content


def test_init_does_not_overwrite_existing_next_md(tmp_repo: Path) -> None:
    next_file = tmp_repo / "NEXT.md"
    next_file.write_text("[ready] My existing task\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(cli, ["--project-root", str(tmp_repo), "init"])
    assert result.exit_code == 0, result.output
    assert "My existing task" in next_file.read_text(encoding="utf-8")


def test_init_creates_changes_dir(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--project-root", str(tmp_repo), "init"])
    assert result.exit_code == 0, result.output
    assert (tmp_repo / "docs" / "changes").is_dir()


def test_init_cursor_config_valid(tmp_repo: Path) -> None:
    """Cursor config must be loadable by Pydantic without validation error."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "init", "--platform", "cursor"],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_repo / ".cursor" / "rules" / "harness-governance.md").is_file()

    # Config must be parseable — this was the bug: cursor was not in Literal
    from harness_governance.config.settings import load_config
    config = load_config(tmp_repo)
    assert config.agent_platform == "cursor"


def test_init_cursor_skill_has_cursor_content(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "init", "--platform", "cursor"],
    )
    assert result.exit_code == 0, result.output
    skill = tmp_repo / ".cursor" / "rules" / "harness-governance.md"
    content = skill.read_text(encoding="utf-8")
    assert "Cursor" in content
    assert "harness" in content


# ---------------------------------------------------------------------------
# Phase 2: qoderwork platform
# ---------------------------------------------------------------------------

def test_init_detects_qoderwork(tmp_repo: Path) -> None:
    (tmp_repo / ".qoderwork").mkdir()
    assert detect_platform(tmp_repo) == "qoderwork"


def test_init_qoderwork_writes_skill(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "init", "--platform", "qoderwork"],
    )
    assert result.exit_code == 0, result.output
    # qoderwork uses AGENTS.md convention
    skill = tmp_repo / "AGENTS.md"
    assert skill.is_file()
    content = skill.read_text(encoding="utf-8")
    assert "QoderWork" in content
    assert "harness" in content


def test_init_qoderwork_config_valid(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "init", "--platform", "qoderwork"],
    )
    assert result.exit_code == 0, result.output
    from harness_governance.config.settings import load_config
    config = load_config(tmp_repo)
    assert config.agent_platform == "qoderwork"


# ---------------------------------------------------------------------------
# Phase 3: opencode platform
# ---------------------------------------------------------------------------

def test_init_detects_opencode(tmp_repo: Path) -> None:
    (tmp_repo / ".opencode").mkdir()
    assert detect_platform(tmp_repo) == "opencode"


def test_init_opencode_writes_skill(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "init", "--platform", "opencode"],
    )
    assert result.exit_code == 0, result.output
    skill = tmp_repo / ".opencode" / "agents" / "harness-governance.md"
    assert skill.is_file()
    content = skill.read_text(encoding="utf-8")
    assert "OpenCode" in content
    assert "harness" in content


def test_init_opencode_config_valid(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "init", "--platform", "opencode"],
    )
    assert result.exit_code == 0, result.output
    from harness_governance.config.settings import load_config
    config = load_config(tmp_repo)
    assert config.agent_platform == "opencode"


# ---------------------------------------------------------------------------
# --minimal mode (friction reduction)
# ---------------------------------------------------------------------------


def test_init_minimal_creates_only_config(tmp_repo: Path) -> None:
    """--minimal writes only config.toml; no skill adapter, NEXT.md, or scaffolding."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--project-root", str(tmp_repo), "init", "--minimal"])
    assert result.exit_code == 0, result.output
    # Config must exist
    assert (tmp_repo / ".harness" / "config.toml").is_file()
    # Skill adapter must NOT exist
    assert not (tmp_repo / PLATFORM_SKILL_PATHS["claude-code"]).exists()
    # NEXT.md must NOT exist
    assert not (tmp_repo / "NEXT.md").exists()
    # docs/changes/ must NOT exist
    assert not (tmp_repo / "docs" / "changes").exists()
    # Output should mention minimal
    assert "minimal" in result.output.lower() or "最小" in result.output


def test_init_minimal_json_output(tmp_repo: Path) -> None:
    """--minimal with --json produces valid JSON with expected fields."""
    runner = CliRunner()
    result = runner.invoke(
        cli, ["--project-root", str(tmp_repo), "--json", "init", "--minimal"]
    )
    assert result.exit_code == 0, result.output
    import json
    data = json.loads(result.output)
    assert data["config_path"] is not None
    assert data["skill_path"] is None


def test_init_minimal_with_platform(tmp_repo: Path) -> None:
    """--minimal with explicit platform writes only config."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "init", "--minimal", "--platform", "cursor"],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_repo / ".harness" / "config.toml").is_file()
    assert not (tmp_repo / ".cursor" / "rules" / "harness-governance.md").exists()


# ---------------------------------------------------------------------------
# .gitignore: NEXT.md is personal
# ---------------------------------------------------------------------------


def test_init_creates_gitignore_with_next_md(tmp_repo: Path) -> None:
    """harness init adds NEXT.md to .gitignore (personal queue, not shared)."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--project-root", str(tmp_repo), "init"])
    assert result.exit_code == 0, result.output
    gitignore = tmp_repo / ".gitignore"
    assert gitignore.is_file()
    content = gitignore.read_text(encoding="utf-8")
    assert "NEXT.md" in content


def test_init_gitignore_idempotent(tmp_repo: Path) -> None:
    """Running init twice doesn't duplicate NEXT.md in .gitignore."""
    runner = CliRunner()
    runner.invoke(cli, ["--project-root", str(tmp_repo), "init"])
    runner.invoke(cli, ["--project-root", str(tmp_repo), "init", "--force"])
    content = (tmp_repo / ".gitignore").read_text(encoding="utf-8")
    assert content.count("NEXT.md") == 1


def test_init_gitignore_appends_to_existing(tmp_repo: Path) -> None:
    """If .gitignore already has other entries, NEXT.md is appended."""
    gitignore = tmp_repo / ".gitignore"
    gitignore.write_text("*.pyc\n__pycache__/\n", encoding="utf-8")
    runner = CliRunner()
    result = runner.invoke(cli, ["--project-root", str(tmp_repo), "init"])
    assert result.exit_code == 0, result.output
    content = gitignore.read_text(encoding="utf-8")
    assert "*.pyc" in content
    assert "NEXT.md" in content


def test_init_minimal_skips_gitignore(tmp_repo: Path) -> None:
    """--minimal mode does not touch .gitignore (no NEXT.md created either)."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--project-root", str(tmp_repo), "init", "--minimal"])
    assert result.exit_code == 0, result.output
    assert not (tmp_repo / ".gitignore").exists()
