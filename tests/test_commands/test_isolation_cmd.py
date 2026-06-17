"""Tests for ``harness isolation`` CLI commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from harness_governance.cli import cli
from harness_governance.state_machine.isolation import (
    _CANONICAL_ROLES,
    IsolationManager,
)
from harness_governance.models.schemas import IsolationRecord
from tests.conftest import write_permissive_config, seed_session


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SESSION_ID = "20260616-iso-test"


def _setup(tmp_path: Path) -> str:
    """Prepare a project root with permissive config and seeded session."""
    write_permissive_config(tmp_path)
    return seed_session(tmp_path, session_id=_SESSION_ID)


# ---------------------------------------------------------------------------
# isolation init
# ---------------------------------------------------------------------------


class TestIsolationInit:
    """Test ``harness isolation init --session-id X``."""

    def test_init_creates_workspaces_for_all_roles(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "init",
                "--session-id", _SESSION_ID,
            ],
        )
        assert result.exit_code == 0, result.output

        session_dir = tmp_path / ".harness" / "isolation" / _SESSION_ID
        for role in _CANONICAL_ROLES:
            assert (session_dir / role).is_dir(), f"Missing directory for {role}"
            assert (session_dir / role / "workspace.json").is_file(), (
                f"Missing workspace.json for {role}"
            )

    def test_init_output_mentions_count(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "init",
                "--session-id", _SESSION_ID,
            ],
        )
        assert result.exit_code == 0, result.output
        assert str(len(_CANONICAL_ROLES)) in result.output

    def test_init_output_mentions_session(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "init",
                "--session-id", _SESSION_ID,
            ],
        )
        assert result.exit_code == 0, result.output
        assert _SESSION_ID in result.output

    def test_init_output_lists_roles(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "init",
                "--session-id", _SESSION_ID,
            ],
        )
        assert result.exit_code == 0, result.output
        for role in _CANONICAL_ROLES:
            assert role in result.output

    def test_init_with_specific_roles(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "init",
                "--session-id", _SESSION_ID,
                "--role", "planner",
                "--role", "reviewer",
            ],
        )
        assert result.exit_code == 0, result.output

        session_dir = tmp_path / ".harness" / "isolation" / _SESSION_ID
        assert (session_dir / "planner").is_dir()
        assert (session_dir / "reviewer").is_dir()
        # Roles not requested should not exist
        assert not (session_dir / "implementer").is_dir()

    def test_init_with_change_id(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "init",
                "--session-id", _SESSION_ID,
                "--change-id", "chg-001",
            ],
        )
        assert result.exit_code == 0, result.output

    def test_init_creates_ndjson_log(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        runner = CliRunner()
        runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "init",
                "--session-id", _SESSION_ID,
            ],
        )

        ndjson_path = (
            tmp_path / ".harness" / "isolation" / _SESSION_ID / ".isolation.ndjson"
        )
        assert ndjson_path.is_file()
        lines = ndjson_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == len(_CANONICAL_ROLES)

    def test_init_requires_session_id(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "init",
            ],
        )
        assert result.exit_code != 0
        assert "session-id" in result.output.lower() or "Missing" in result.output

    def test_init_single_role(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "init",
                "--session-id", _SESSION_ID,
                "--role", "implementer",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "implementer" in result.output
        assert "1" in result.output  # 1 workspace created


# ---------------------------------------------------------------------------
# isolation check
# ---------------------------------------------------------------------------


class TestIsolationCheck:
    """Test ``harness isolation check --session-id X``."""

    def test_check_passes_clean_session(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        runner = CliRunner()

        # First init
        runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "init",
                "--session-id", _SESSION_ID,
            ],
        )

        # Then check
        result = runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "check",
                "--session-id", _SESSION_ID,
            ],
        )
        assert result.exit_code == 0, result.output

    def test_check_reports_roles_isolated(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        runner = CliRunner()

        runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "init",
                "--session-id", _SESSION_ID,
            ],
        )

        result = runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "check",
                "--session-id", _SESSION_ID,
            ],
        )
        assert result.exit_code == 0, result.output
        # Output should mention the roles
        for role in _CANONICAL_ROLES:
            assert role in result.output

    def test_check_fails_with_violations(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        runner = CliRunner()

        # Init
        runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "init",
                "--session-id", _SESSION_ID,
            ],
        )

        # Inject a violation into the NDJSON log
        mgr = IsolationManager(tmp_path)
        mgr.append_event(
            IsolationRecord(
                event="violation_detected",
                role="planner",
                workspace_path=f".harness/isolation/{_SESSION_ID}/planner",
                session_id=_SESSION_ID,
                files_touched=("src/forbidden.py",),
            ),
            session_id=_SESSION_ID,
        )

        result = runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "check",
                "--session-id", _SESSION_ID,
            ],
        )
        assert result.exit_code == 1

    def test_check_output_mentions_validity(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        runner = CliRunner()

        runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "init",
                "--session-id", _SESSION_ID,
            ],
        )

        result = runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "check",
                "--session-id", _SESSION_ID,
            ],
        )
        assert result.exit_code == 0, result.output
        # Should contain validity indicator
        output_lower = result.output.lower()
        assert "valid" in output_lower

    def test_check_empty_session(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        runner = CliRunner()

        result = runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "check",
                "--session-id", "nonexistent-session",
            ],
        )
        # No roles isolated, but no violations either
        # The command should succeed (workspaces_valid=True when no violations)
        assert result.exit_code == 0, result.output
        assert "none" in result.output.lower() or "Roles isolated" in result.output

    def test_check_requires_session_id(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "check",
            ],
        )
        assert result.exit_code != 0

    def test_check_reports_out_of_scope_files(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        runner = CliRunner()

        runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "init",
                "--session-id", _SESSION_ID,
            ],
        )

        # Inject violation with specific file
        mgr = IsolationManager(tmp_path)
        mgr.append_event(
            IsolationRecord(
                event="violation_detected",
                role="planner",
                workspace_path=f".harness/isolation/{_SESSION_ID}/planner",
                session_id=_SESSION_ID,
                files_touched=("src/secret_data.py",),
            ),
            session_id=_SESSION_ID,
        )

        result = runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "check",
                "--session-id", _SESSION_ID,
            ],
        )
        assert result.exit_code == 1
        assert "src/secret_data.py" in result.output

    def test_check_multiple_violations(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        runner = CliRunner()

        runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "init",
                "--session-id", _SESSION_ID,
            ],
        )

        mgr = IsolationManager(tmp_path)
        for role in ("planner", "implementer"):
            mgr.append_event(
                IsolationRecord(
                    event="violation_detected",
                    role=role,
                    workspace_path=f".harness/isolation/{_SESSION_ID}/{role}",
                    session_id=_SESSION_ID,
                    files_touched=(f"etc/{role}_violation.py",),
                ),
                session_id=_SESSION_ID,
            )

        result = runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "check",
                "--session-id", _SESSION_ID,
            ],
        )
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# isolation list
# ---------------------------------------------------------------------------


class TestIsolationList:
    """Test ``harness isolation list --session-id X``."""

    def test_list_after_init(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        runner = CliRunner()

        runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "init",
                "--session-id", _SESSION_ID,
            ],
        )

        result = runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "list",
                "--session-id", _SESSION_ID,
            ],
        )
        assert result.exit_code == 0, result.output
        for role in _CANONICAL_ROLES:
            assert role in result.output

    def test_list_shows_allowed_paths(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        runner = CliRunner()

        runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "init",
                "--session-id", _SESSION_ID,
            ],
        )

        result = runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "list",
                "--session-id", _SESSION_ID,
            ],
        )
        assert result.exit_code == 0, result.output
        # Should show some path patterns
        assert "docs/" in result.output or ".harness/" in result.output

    def test_list_shows_allowed_roles(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        runner = CliRunner()

        runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "init",
                "--session-id", _SESSION_ID,
            ],
        )

        result = runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "list",
                "--session-id", _SESSION_ID,
            ],
        )
        assert result.exit_code == 0, result.output
        # At least one role should have allowed roles listed
        assert "contract-writer" in result.output or "planner" in result.output

    def test_list_not_created_roles(self, tmp_path: Path) -> None:
        """Roles that were not initialized should show 'not created'."""
        _setup(tmp_path)
        runner = CliRunner()

        # Only init planner
        runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "init",
                "--session-id", _SESSION_ID,
                "--role", "planner",
            ],
        )

        result = runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "list",
                "--session-id", _SESSION_ID,
            ],
        )
        assert result.exit_code == 0, result.output
        assert "planner" in result.output
        # Other canonical roles should be listed as "not created"
        assert "not created" in result.output.lower()

    def test_list_empty_session(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        runner = CliRunner()

        result = runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "list",
                "--session-id", "empty-session",
            ],
        )
        assert result.exit_code == 0, result.output
        # All roles should show as not created
        assert "not created" in result.output.lower()

    def test_list_requires_session_id(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "list",
            ],
        )
        assert result.exit_code != 0

    def test_list_truncates_long_paths(self, tmp_path: Path) -> None:
        """Paths display should truncate with '... (+N)' for > 3 patterns."""
        _setup(tmp_path)
        runner = CliRunner()

        runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "init",
                "--session-id", _SESSION_ID,
            ],
        )

        result = runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "list",
                "--session-id", _SESSION_ID,
            ],
        )
        assert result.exit_code == 0, result.output
        # Planner has 7 patterns, so should show "... (+4)"
        assert "+4" in result.output or "+5" in result.output or "+6" in result.output


# ---------------------------------------------------------------------------
# --project-root option
# ---------------------------------------------------------------------------


class TestProjectRootOption:
    """Test that --project-root correctly scopes all isolation commands."""

    def test_init_with_project_root(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        runner = CliRunner()

        result = runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "init",
                "--session-id", _SESSION_ID,
            ],
        )
        assert result.exit_code == 0, result.output

        # Verify files are under the specified project root
        session_dir = tmp_path / ".harness" / "isolation" / _SESSION_ID
        assert session_dir.is_dir()

    def test_check_with_project_root(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        runner = CliRunner()

        runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "init",
                "--session-id", _SESSION_ID,
            ],
        )

        result = runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "check",
                "--session-id", _SESSION_ID,
            ],
        )
        assert result.exit_code == 0, result.output

    def test_list_with_project_root(self, tmp_path: Path) -> None:
        _setup(tmp_path)
        runner = CliRunner()

        runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "init",
                "--session-id", _SESSION_ID,
            ],
        )

        result = runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "list",
                "--session-id", _SESSION_ID,
            ],
        )
        assert result.exit_code == 0, result.output

    def test_different_project_roots_are_isolated(self, tmp_path: Path) -> None:
        """Two different project roots should have independent isolation state."""
        write_permissive_config(tmp_path)
        seed_session(tmp_path, session_id=_SESSION_ID)

        other_root = tmp_path / "other_project"
        other_root.mkdir()
        write_permissive_config(other_root)

        runner = CliRunner()

        # Init in tmp_path
        runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "isolation", "init",
                "--session-id", _SESSION_ID,
            ],
        )

        # List in other_root should show not created
        result = runner.invoke(
            cli,
            [
                "--project-root", str(other_root),
                "isolation", "list",
                "--session-id", _SESSION_ID,
            ],
        )
        assert result.exit_code == 0, result.output
        assert "not created" in result.output.lower()


# ---------------------------------------------------------------------------
# isolation help
# ---------------------------------------------------------------------------


class TestIsolationHelp:
    """Test that isolation subcommand help is well-formed."""

    def test_isolation_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["isolation", "--help"])
        assert result.exit_code == 0
        assert "init" in result.output
        assert "check" in result.output
        assert "list" in result.output

    def test_isolation_init_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["isolation", "init", "--help"])
        assert result.exit_code == 0
        assert "--session-id" in result.output

    def test_isolation_check_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["isolation", "check", "--help"])
        assert result.exit_code == 0
        assert "--session-id" in result.output

    def test_isolation_list_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["isolation", "list", "--help"])
        assert result.exit_code == 0
        assert "--session-id" in result.output
