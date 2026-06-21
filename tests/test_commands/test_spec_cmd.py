"""Tests for ``harness spec``."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from harness_governance.cli import cli
from harness_governance.file_ops.spec import (
    SPECS_DIR,
    _slug_from_description,
    init_spec,
    list_specs,
    read_spec,
)


def test_spec_quick_creates_file(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "spec", "quick", "add dark mode toggle"],
    )
    assert result.exit_code == 0, result.output
    assert ".harness/specs/add-dark-mode-toggle.md" in result.output
    spec_file = tmp_repo / SPECS_DIR / "add-dark-mode-toggle.md"
    assert spec_file.is_file()
    content = spec_file.read_text(encoding="utf-8")
    assert "# Spec: add dark mode toggle" in content
    assert "## Goal" in content
    assert "## Tasks" in content
    assert "## Verification" in content


def test_spec_quick_with_custom_slug(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "spec",
            "quick",
            "fix login bug",
            "--slug",
            "login-fix",
        ],
    )
    assert result.exit_code == 0, result.output
    spec_file = tmp_repo / SPECS_DIR / "login-fix.md"
    assert spec_file.is_file()


def test_spec_quick_json_output(tmp_repo: Path) -> None:
    import json

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "--json",
            "spec",
            "quick",
            "update config",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert "path" in payload
    assert payload["slug"] == "update-config"


def test_spec_quick_duplicate_raises_error(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "spec", "quick", "duplicate test"],
    )
    assert result.exit_code == 0, result.output
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "spec", "quick", "duplicate test"],
    )
    assert result.exit_code != 0
    assert "already exists" in result.output


def test_spec_list_empty(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "spec", "list"],
    )
    assert result.exit_code == 0, result.output
    assert "No spec files found" in result.output


def test_spec_list_with_specs(tmp_repo: Path) -> None:
    init_spec(tmp_repo, "first spec")
    init_spec(tmp_repo, "second spec")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "spec", "list"],
    )
    assert result.exit_code == 0, result.output
    assert "first-spec" in result.output or "first spec" in result.output
    assert "second-spec" in result.output or "second spec" in result.output


def test_spec_list_json(tmp_repo: Path) -> None:
    import json

    init_spec(tmp_repo, "list-test")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "--json", "spec", "list"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["count"] == 1
    assert "list-test" in payload["specs"][0]["slug"]


def test_slug_from_description() -> None:
    assert _slug_from_description("Add dark mode toggle") == "add-dark-mode-toggle"
    assert _slug_from_description("Fix 登录 bug") == "fix-bug"
    assert _slug_from_description("  Spaces   and  CAPS  ") == "spaces-and-caps"
    assert _slug_from_description("") == "spec"


def test_read_spec_returns_sections(tmp_repo: Path) -> None:
    path = init_spec(tmp_repo, "read test")
    sections = read_spec(path)
    assert sections.get("title") == "read test"
    assert "goal" in sections
    assert "tasks" in sections
    assert "verification" in sections


def test_init_spec_creates_specs_dir(tmp_repo: Path) -> None:
    assert not (tmp_repo / SPECS_DIR).exists()
    init_spec(tmp_repo, "create dir test")
    assert (tmp_repo / SPECS_DIR).is_dir()


def test_list_specs_returns_sorted(tmp_repo: Path) -> None:
    init_spec(tmp_repo, "beta")
    init_spec(tmp_repo, "alpha")
    specs = list_specs(tmp_repo)
    assert len(specs) == 2
    assert "alpha" in specs[0].stem


def test_spec_upgrade_creates_change_packet(tmp_repo: Path) -> None:
    spec_path = init_spec(tmp_repo, "add audit log")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "spec",
            "upgrade",
            str(spec_path.relative_to(tmp_repo)),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "docs/changes/add-audit-log" in result.output
    packet_dir = tmp_repo / "docs/changes/add-audit-log"
    assert (packet_dir / "proposal.md").is_file()
    assert (packet_dir / "design.md").is_file()
    assert (packet_dir / "tasks.md").is_file()
    assert (packet_dir / "contracts.md").is_file()
    assert (packet_dir / "verification.md").is_file()
    assert "add audit log." in (packet_dir / "proposal.md").read_text(
        encoding="utf-8"
    )
    assert "- [ ] Implement add audit log" in (packet_dir / "tasks.md").read_text(
        encoding="utf-8"
    )


def test_spec_upgrade_with_custom_change_id(tmp_repo: Path) -> None:
    spec_path = init_spec(tmp_repo, "custom packet")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "spec",
            "upgrade",
            str(spec_path),
            "--change-id",
            "custom-change",
        ],
    )

    assert result.exit_code == 0, result.output
    assert (tmp_repo / "docs/changes/custom-change/proposal.md").is_file()


def test_spec_upgrade_json_output(tmp_repo: Path) -> None:
    import json

    spec_path = init_spec(tmp_repo, "json upgrade")

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "--json",
            "spec",
            "upgrade",
            str(spec_path),
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["change_id"] == "json-upgrade"
    assert payload["path"] == "docs/changes/json-upgrade"


def test_spec_upgrade_missing_spec_fails(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "spec", "upgrade", "missing"],
    )

    assert result.exit_code != 0
    assert "Spec not found" in result.output


def test_spec_upgrade_existing_packet_fails(tmp_repo: Path) -> None:
    spec_path = init_spec(tmp_repo, "duplicate packet")

    runner = CliRunner()
    first = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "spec", "upgrade", str(spec_path)],
    )
    assert first.exit_code == 0, first.output

    second = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "spec", "upgrade", str(spec_path)],
    )

    assert second.exit_code != 0
    assert "already exists" in second.output
