"""Tests for ``harness hook`` commands."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from harness_governance.cli import cli
from harness_governance.commands.hook import _TAG_RELEASE_MARKER


def _init_git_dir(project_root: Path) -> None:
    (project_root / ".git" / "hooks").mkdir(parents=True)


def _mark_harness_governance_repo(project_root: Path) -> None:
    (project_root / "src" / "harness_governance").mkdir(parents=True)
    (project_root / "pyproject.toml").write_text(
        '[project]\nname = "harness-governance"\n',
        encoding="utf-8",
    )


def test_hook_install_tag_release_writes_pre_push(tmp_repo: Path) -> None:
    _mark_harness_governance_repo(tmp_repo)
    _init_git_dir(tmp_repo)
    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "hook", "install", "--tag-release"],
    )

    assert result.exit_code == 0, result.output
    hook = tmp_repo / ".git" / "hooks" / "pre-push"
    text = hook.read_text(encoding="utf-8")
    assert _TAG_RELEASE_MARKER in text
    assert "refs/tags/*" in text
    assert "harness verify local --release" in text


def test_hook_install_tag_release_requires_git_dir(tmp_repo: Path) -> None:
    _mark_harness_governance_repo(tmp_repo)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "hook", "install", "--tag-release"],
    )
    assert result.exit_code != 0
    assert "No .git directory" in result.output


def test_hook_install_tag_release_is_self_repo_only(tmp_repo: Path) -> None:
    _init_git_dir(tmp_repo)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "hook", "install", "--tag-release"],
    )
    assert result.exit_code != 0
    assert "only available in the harness-governance source repository" in result.output


def test_hook_install_does_not_overwrite_existing_hook(tmp_repo: Path) -> None:
    _mark_harness_governance_repo(tmp_repo)
    _init_git_dir(tmp_repo)
    hook = tmp_repo / ".git" / "hooks" / "pre-push"
    hook.write_text("# custom\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "hook", "install", "--tag-release"],
    )
    assert result.exit_code != 0
    assert hook.read_text(encoding="utf-8") == "# custom\n"


def test_hook_install_force_overwrites_existing_hook(tmp_repo: Path) -> None:
    _mark_harness_governance_repo(tmp_repo)
    _init_git_dir(tmp_repo)
    hook = tmp_repo / ".git" / "hooks" / "pre-push"
    hook.write_text("# custom\n", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "hook",
            "install",
            "--tag-release",
            "--force",
        ],
    )
    assert result.exit_code == 0, result.output
    assert _TAG_RELEASE_MARKER in hook.read_text(encoding="utf-8")
