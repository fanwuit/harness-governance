"""Tests for ``harness drift`` CLI commands (check / scope / boundary).

Uses :class:`click.testing.CliRunner` to invoke the CLI in-process.
Git interactions (``_run_git_diff`` and ``resolve_diff_base``) are always
mocked so the suite is fully deterministic.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner, Result

from harness_governance.cli import cli
from harness_governance.models.schemas import (
    ScopeBoundary,
    ScopeDeclaration,
)
from harness_governance.state_machine.drift import DriftDetectionEngine
from tests.conftest import write_permissive_config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PATCH_DIFF = "harness_governance.state_machine.drift._run_git_diff"
PATCH_BASE = "harness_governance.state_machine.drift.resolve_diff_base"
PATCH_BASE_CMD = "harness_governance.commands.drift.resolve_diff_base"


def _invoke(args: list[str], *, project_root: Path) -> Result:
    """Invoke the CLI with ``--project-root`` prepended."""
    runner = CliRunner()
    return runner.invoke(cli, ["--project-root", str(project_root), *args])


def _seed_scope(
    project_root: Path,
    change_id: str,
    *,
    files: tuple[str, ...] = (),
    max_files: int = 0,
    max_total_lines: int = 0,
    forbidden_paths: tuple[str, ...] = (),
) -> Path:
    """Write a scope declaration to disk and return the file path."""
    engine = DriftDetectionEngine(project_root)
    scope = ScopeDeclaration(
        change_id=change_id,
        session_id="test",
        declared_files=files,
        boundary=ScopeBoundary(
            max_files=max_files,
            max_total_lines=max_total_lines,
            forbidden_paths=forbidden_paths,
        ),
    )
    return engine.declare_scope(scope)


# =========================================================================
# drift check
# =========================================================================


class TestDriftCheck:
    """Tests for ``harness drift check --change-id X``."""

    @patch(PATCH_BASE_CMD, return_value="abc12345")
    @patch(PATCH_BASE, return_value="abc12345")
    @patch(PATCH_DIFF, return_value=(["src/a.py"], 20, 5))
    def test_check_no_drift_passes(
        self, _diff: MagicMock, _base: MagicMock, _base_cmd: MagicMock, tmp_path: Path
    ) -> None:
        """No drift -> exit code 0 and success message."""
        write_permissive_config(tmp_path)
        _seed_scope(tmp_path, "chg-clean", files=("src/a.py",))

        result = _invoke(
            ["drift", "check", "--change-id", "chg-clean"],
            project_root=tmp_path,
        )
        assert result.exit_code == 0, result.output
        assert "No scope drift" in result.output or "drift" in result.output.lower()

    @patch(PATCH_BASE_CMD, return_value="abc12345")
    @patch(PATCH_BASE, return_value="abc12345")
    @patch(PATCH_DIFF, return_value=(["src/rogue.py"], 20, 5))
    def test_check_with_drift_fails(
        self, _diff: MagicMock, _base: MagicMock, _base_cmd: MagicMock, tmp_path: Path
    ) -> None:
        """Drift detected -> exit code 1."""
        write_permissive_config(tmp_path)
        _seed_scope(tmp_path, "chg-drift", files=("src/a.py",))

        result = _invoke(
            ["drift", "check", "--change-id", "chg-drift"],
            project_root=tmp_path,
        )
        assert result.exit_code != 0

    @patch(PATCH_BASE_CMD, return_value="abc12345")
    @patch(PATCH_BASE, return_value="abc12345")
    @patch(PATCH_DIFF, return_value=(["src/a.py", "src/b.py"], 20, 5))
    def test_check_no_scope_declared_passes(
        self, _diff: MagicMock, _base: MagicMock, _base_cmd: MagicMock, tmp_path: Path
    ) -> None:
        """Without a scope declaration drift check is advisory -- passes."""
        write_permissive_config(tmp_path)
        result = _invoke(
            ["drift", "check", "--change-id", "unknown"],
            project_root=tmp_path,
        )
        assert result.exit_code == 0, result.output

    @patch(PATCH_BASE_CMD, return_value="abc12345")
    @patch(PATCH_BASE, return_value="abc12345")
    @patch(PATCH_DIFF, return_value=(["secrets/key.pem"], 5, 0))
    def test_check_forbidden_paths_fail(
        self, _diff: MagicMock, _base: MagicMock, _base_cmd: MagicMock, tmp_path: Path
    ) -> None:
        """Touching forbidden paths triggers drift failure."""
        write_permissive_config(tmp_path)
        _seed_scope(
            tmp_path,
            "chg-forbid",
            files=("secrets/key.pem",),
            forbidden_paths=("secrets/*",),
        )
        result = _invoke(
            ["drift", "check", "--change-id", "chg-forbid"],
            project_root=tmp_path,
        )
        assert result.exit_code != 0

    @patch(PATCH_BASE_CMD, return_value="abc12345")
    @patch(PATCH_BASE, return_value="abc12345")
    @patch(
        PATCH_DIFF,
        return_value=(
            [f"src/f{i}.py" for i in range(15)],
            100,
            10,
        ),
    )
    def test_check_decomposition_trigger_fails(
        self, _diff: MagicMock, _base: MagicMock, _base_cmd: MagicMock, tmp_path: Path
    ) -> None:
        """Exceeding max_files decomposition threshold triggers drift."""
        write_permissive_config(tmp_path)
        _seed_scope(
            tmp_path,
            "chg-big",
            files=tuple(f"src/f{i}.py" for i in range(15)),
            max_files=5,
        )
        result = _invoke(
            ["drift", "check", "--change-id", "chg-big"],
            project_root=tmp_path,
        )
        assert result.exit_code != 0

    @patch(PATCH_BASE_CMD, return_value="abc12345")
    @patch(PATCH_BASE, return_value="abc12345")
    @patch(PATCH_DIFF, return_value=(["src/a.py"], 10, 5))
    def test_check_shows_base_ref_and_stats(
        self, _diff: MagicMock, _base: MagicMock, _base_cmd: MagicMock, tmp_path: Path
    ) -> None:
        """Output includes base ref, file count, and line stats."""
        write_permissive_config(tmp_path)
        result = _invoke(
            ["drift", "check", "--change-id", "any"],
            project_root=tmp_path,
        )
        assert result.exit_code == 0, result.output
        # Base ref is shown (first 8 chars).
        assert "abc12345" in result.output
        # File count.
        assert "1" in result.output
        # Line stats.
        assert "10" in result.output  # added
        assert "5" in result.output  # deleted

    @patch(PATCH_BASE_CMD, return_value="abc12345")
    @patch(PATCH_BASE, return_value="abc12345")
    @patch(PATCH_DIFF, return_value=(["src/a.py"], 10, 5))
    def test_check_with_base_ref_option(
        self, _diff: MagicMock, _base: MagicMock, _base_cmd: MagicMock, tmp_path: Path
    ) -> None:
        """``--base-ref`` is forwarded correctly."""
        write_permissive_config(tmp_path)
        result = _invoke(
            ["drift", "check", "--change-id", "x", "--base-ref", "v1.0"],
            project_root=tmp_path,
        )
        # The mock always returns "abc12345", so the command should succeed.
        assert result.exit_code == 0, result.output

    @patch(PATCH_BASE_CMD, return_value="abc12345")
    @patch(PATCH_BASE, return_value="abc12345")
    @patch(PATCH_DIFF, return_value=([], 0, 0))
    def test_check_empty_diff_no_drift(
        self, _diff: MagicMock, _base: MagicMock, _base_cmd: MagicMock, tmp_path: Path
    ) -> None:
        """No changes at all -- clean."""
        write_permissive_config(tmp_path)
        _seed_scope(tmp_path, "chg-empty", files=("src/a.py",))
        result = _invoke(
            ["drift", "check", "--change-id", "chg-empty"],
            project_root=tmp_path,
        )
        assert result.exit_code == 0, result.output


# =========================================================================
# drift scope
# =========================================================================


class TestDriftScope:
    """Tests for ``harness drift scope``."""

    def test_scope_creates_declaration(self, tmp_path: Path) -> None:
        """``drift scope`` writes a scope file."""
        write_permissive_config(tmp_path)
        result = _invoke(
            [
                "drift",
                "scope",
                "--change-id",
                "chg-s1",
                "--file",
                "src/a.py",
                "--file",
                "src/b.py",
                "--max-files",
                "10",
            ],
            project_root=tmp_path,
        )
        assert result.exit_code == 0, result.output
        # File should exist on disk.
        scope_file = tmp_path / ".harness" / "scopes" / "chg-s1.json"
        assert scope_file.is_file()

        data = json.loads(scope_file.read_text(encoding="utf-8"))
        assert data["change_id"] == "chg-s1"
        assert "src/a.py" in data["declared_files"]
        assert "src/b.py" in data["declared_files"]
        assert data["boundary"]["max_files"] == 10

    def test_scope_with_forbidden_paths(self, tmp_path: Path) -> None:
        """``--forbidden`` patterns are persisted."""
        write_permissive_config(tmp_path)
        result = _invoke(
            [
                "drift",
                "scope",
                "--change-id",
                "chg-f1",
                "--file",
                "src/a.py",
                "--forbidden",
                "secrets/*",
                "--forbidden",
                "vendor/**",
            ],
            project_root=tmp_path,
        )
        assert result.exit_code == 0, result.output
        scope_file = tmp_path / ".harness" / "scopes" / "chg-f1.json"
        data = json.loads(scope_file.read_text(encoding="utf-8"))
        assert "secrets/*" in data["boundary"]["forbidden_paths"]
        assert "vendor/**" in data["boundary"]["forbidden_paths"]

    def test_scope_with_tier_strict(self, tmp_path: Path) -> None:
        """``--tier strict`` applies strict defaults."""
        write_permissive_config(tmp_path)
        result = _invoke(
            [
                "drift",
                "scope",
                "--change-id",
                "chg-strict",
                "--tier",
                "strict",
            ],
            project_root=tmp_path,
        )
        assert result.exit_code == 0, result.output
        scope_file = tmp_path / ".harness" / "scopes" / "chg-strict.json"
        data = json.loads(scope_file.read_text(encoding="utf-8"))
        assert data["boundary"]["max_files"] == 8
        assert data["boundary"]["max_total_lines"] == 500

    def test_scope_with_tier_light(self, tmp_path: Path) -> None:
        """``--tier light`` applies light defaults."""
        write_permissive_config(tmp_path)
        result = _invoke(
            [
                "drift",
                "scope",
                "--change-id",
                "chg-light",
                "--tier",
                "light",
            ],
            project_root=tmp_path,
        )
        assert result.exit_code == 0, result.output
        scope_file = tmp_path / ".harness" / "scopes" / "chg-light.json"
        data = json.loads(scope_file.read_text(encoding="utf-8"))
        assert data["boundary"]["max_files"] == 25

    def test_scope_updates_existing(self, tmp_path: Path) -> None:
        """Re-running ``drift scope`` merges with existing declaration."""
        write_permissive_config(tmp_path)

        # First declaration.
        _invoke(
            [
                "drift",
                "scope",
                "--change-id",
                "chg-upd",
                "--file",
                "src/a.py",
                "--max-files",
                "10",
            ],
            project_root=tmp_path,
        )

        # Update with additional files.
        result = _invoke(
            [
                "drift",
                "scope",
                "--change-id",
                "chg-upd",
                "--file",
                "src/b.py",
            ],
            project_root=tmp_path,
        )
        assert result.exit_code == 0, result.output

        scope_file = tmp_path / ".harness" / "scopes" / "chg-upd.json"
        data = json.loads(scope_file.read_text(encoding="utf-8"))
        assert "src/a.py" in data["declared_files"]
        assert "src/b.py" in data["declared_files"]

    def test_scope_with_max_lines(self, tmp_path: Path) -> None:
        """``--max-lines`` overrides the boundary threshold."""
        write_permissive_config(tmp_path)
        result = _invoke(
            [
                "drift",
                "scope",
                "--change-id",
                "chg-ml",
                "--max-lines",
                "300",
            ],
            project_root=tmp_path,
        )
        assert result.exit_code == 0, result.output
        scope_file = tmp_path / ".harness" / "scopes" / "chg-ml.json"
        data = json.loads(scope_file.read_text(encoding="utf-8"))
        assert data["boundary"]["max_total_lines"] == 300

    def test_scope_output_mentions_change_id(self, tmp_path: Path) -> None:
        """Output message references the change ID."""
        write_permissive_config(tmp_path)
        result = _invoke(
            [
                "drift",
                "scope",
                "--change-id",
                "chg-msg",
                "--file",
                "src/a.py",
            ],
            project_root=tmp_path,
        )
        assert result.exit_code == 0, result.output
        assert "chg-msg" in result.output

    def test_scope_with_session_id(self, tmp_path: Path) -> None:
        """``--session-id`` is persisted in the declaration."""
        write_permissive_config(tmp_path)
        result = _invoke(
            [
                "drift",
                "scope",
                "--change-id",
                "chg-sess",
                "--session-id",
                "my-session",
                "--file",
                "src/a.py",
            ],
            project_root=tmp_path,
        )
        assert result.exit_code == 0, result.output
        scope_file = tmp_path / ".harness" / "scopes" / "chg-sess.json"
        data = json.loads(scope_file.read_text(encoding="utf-8"))
        assert data["session_id"] == "my-session"


# =========================================================================
# drift boundary
# =========================================================================


class TestDriftBoundary:
    """Tests for ``harness drift boundary``."""

    def test_boundary_shows_info(self, tmp_path: Path) -> None:
        """``drift boundary`` displays scope details when a declaration exists."""
        write_permissive_config(tmp_path)
        _seed_scope(
            tmp_path,
            "chg-b1",
            files=("src/a.py", "src/b.py"),
            max_files=10,
            max_total_lines=500,
        )
        result = _invoke(
            ["drift", "boundary", "--change-id", "chg-b1"],
            project_root=tmp_path,
        )
        assert result.exit_code == 0, result.output
        assert "chg-b1" in result.output
        assert "10" in result.output  # max_files
        assert "500" in result.output  # max_total_lines
        assert "src/a.py" in result.output
        assert "src/b.py" in result.output

    def test_boundary_no_scope_fails(self, tmp_path: Path) -> None:
        """``drift boundary`` fails when no scope declaration exists."""
        write_permissive_config(tmp_path)
        result = _invoke(
            ["drift", "boundary", "--change-id", "nonexistent"],
            project_root=tmp_path,
        )
        assert result.exit_code != 0

    def test_boundary_shows_forbidden_paths(self, tmp_path: Path) -> None:
        """Forbidden paths are listed in the output."""
        write_permissive_config(tmp_path)
        _seed_scope(
            tmp_path,
            "chg-fb",
            files=("src/a.py",),
            forbidden_paths=("secrets/*", "vendor/**"),
        )
        result = _invoke(
            ["drift", "boundary", "--change-id", "chg-fb"],
            project_root=tmp_path,
        )
        assert result.exit_code == 0, result.output
        assert "secrets/*" in result.output
        assert "vendor/**" in result.output

    def test_boundary_shows_infinity_for_zero_thresholds(self, tmp_path: Path) -> None:
        """Zero thresholds display as infinity symbol."""
        write_permissive_config(tmp_path)
        _seed_scope(tmp_path, "chg-inf", files=("src/a.py",))
        result = _invoke(
            ["drift", "boundary", "--change-id", "chg-inf"],
            project_root=tmp_path,
        )
        assert result.exit_code == 0, result.output
        # max_files=0 should show as infinity.
        assert "\u221e" in result.output  # ∞

    def test_boundary_shows_declared_file_count(self, tmp_path: Path) -> None:
        """The declared-files count is shown."""
        write_permissive_config(tmp_path)
        _seed_scope(
            tmp_path,
            "chg-cnt",
            files=("src/a.py", "src/b.py", "src/c.py"),
        )
        result = _invoke(
            ["drift", "boundary", "--change-id", "chg-cnt"],
            project_root=tmp_path,
        )
        assert result.exit_code == 0, result.output
        assert "3" in result.output  # 3 declared files


# =========================================================================
# --project-root option
# =========================================================================


class TestProjectRoot:
    """Ensure ``--project-root`` correctly directs operations."""

    @patch(PATCH_BASE, return_value="abc12345")
    @patch(PATCH_DIFF, return_value=(["src/a.py"], 10, 5))
    def test_project_root_scopes_written_to_correct_dir(
        self, _diff: MagicMock, _base: MagicMock, tmp_path: Path
    ) -> None:
        """Scope files are written under the specified project root."""
        write_permissive_config(tmp_path)
        result = _invoke(
            [
                "drift",
                "scope",
                "--change-id",
                "chg-root",
                "--file",
                "src/a.py",
            ],
            project_root=tmp_path,
        )
        assert result.exit_code == 0, result.output
        assert (tmp_path / ".harness" / "scopes" / "chg-root.json").is_file()

    @patch(PATCH_BASE_CMD, return_value="abc12345")
    @patch(PATCH_BASE, return_value="abc12345")
    @patch(PATCH_DIFF, return_value=(["src/a.py"], 10, 5))
    def test_project_root_check_reads_from_correct_dir(
        self, _diff: MagicMock, _base: MagicMock, _base_cmd: MagicMock, tmp_path: Path
    ) -> None:
        """``drift check`` reads scope from the specified project root."""
        write_permissive_config(tmp_path)
        _seed_scope(tmp_path, "chg-pr", files=("src/a.py",))

        result = _invoke(
            ["drift", "check", "--change-id", "chg-pr"],
            project_root=tmp_path,
        )
        assert result.exit_code == 0, result.output

    def test_project_root_boundary_reads_from_correct_dir(self, tmp_path: Path) -> None:
        """``drift boundary`` reads scope from the specified project root."""
        write_permissive_config(tmp_path)
        _seed_scope(tmp_path, "chg-prb", files=("src/x.py",), max_files=7)

        result = _invoke(
            ["drift", "boundary", "--change-id", "chg-prb"],
            project_root=tmp_path,
        )
        assert result.exit_code == 0, result.output
        assert "7" in result.output
