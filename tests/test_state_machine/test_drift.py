"""Tests for :mod:`harness_governance.state_machine.drift`.

Covers ``resolve_diff_base``, ``DriftDetectionEngine`` (declare, load,
check_boundary, detect_decomposition_trigger), ``ScopeBoundary.for_tier``,
and the ``_gate_hook_drift`` registration hook.

All git interactions are mocked via ``unittest.mock.patch`` so that the
test suite does not depend on a real git repository.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch


from harness_governance.models.schemas import (
    ScopeBoundary,
    ScopeDeclaration,
)
from harness_governance.state_machine.drift import (
    DriftDetectionEngine,
    _EMPTY_TREE,
    _gate_hook_drift,
    resolve_diff_base,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _completed_process(stdout: str = "", returncode: int = 0) -> MagicMock:
    """Return a mock ``subprocess.CompletedProcess``."""
    proc = MagicMock()
    proc.stdout = stdout
    proc.returncode = returncode
    return proc


def _make_scope(
    change_id: str = "chg-001",
    *,
    files: tuple[str, ...] = (),
    max_files: int = 0,
    max_total_lines: int = 0,
    forbidden_paths: tuple[str, ...] = (),
) -> ScopeDeclaration:
    """Build a minimal ``ScopeDeclaration`` for tests."""
    return ScopeDeclaration(
        change_id=change_id,
        session_id="test-session",
        declared_files=files,
        boundary=ScopeBoundary(
            max_files=max_files,
            max_total_lines=max_total_lines,
            forbidden_paths=forbidden_paths,
        ),
    )


# =========================================================================
# resolve_diff_base
# =========================================================================


class TestResolveDiffBase:
    """Tests for :func:`resolve_diff_base`."""

    def test_override_ref_returned_directly(self, tmp_path: Path) -> None:
        """When *override_ref* is provided it is returned without any git call."""
        result = resolve_diff_base(tmp_path, override_ref="abc123")
        assert result == "abc123"

    @patch("harness_governance.state_machine.drift.subprocess.run")
    def test_merge_base_success(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """merge-base returning 0 should be used."""
        mock_run.return_value = _completed_process(stdout="deadbeef\n")
        result = resolve_diff_base(tmp_path)
        assert result == "deadbeef"
        mock_run.assert_called_once()

    @patch("harness_governance.state_machine.drift.subprocess.run")
    def test_merge_base_fails_falls_to_head_minus_1(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """If merge-base fails, fallback to HEAD~1."""
        mock_run.side_effect = [
            _completed_process(returncode=1),  # merge-base fails
            _completed_process(stdout="cafebabe\n"),  # HEAD~1 succeeds
        ]
        result = resolve_diff_base(tmp_path)
        assert result == "cafebabe"
        assert mock_run.call_count == 2

    @patch("harness_governance.state_machine.drift.subprocess.run")
    def test_both_fail_falls_to_empty_tree(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """If both git calls fail, fall back to the empty-tree hash."""
        mock_run.return_value = _completed_process(returncode=128)
        result = resolve_diff_base(tmp_path)
        assert result == _EMPTY_TREE

    @patch("harness_governance.state_machine.drift.subprocess.run")
    def test_merge_base_exception_falls_to_head_minus_1(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """If merge-base raises an exception, fall through to HEAD~1."""
        mock_run.side_effect = [
            OSError("git not found"),  # merge-base raises
            _completed_process(stdout="face0ff\n"),  # HEAD~1 succeeds
        ]
        result = resolve_diff_base(tmp_path)
        assert result == "face0ff"

    @patch("harness_governance.state_machine.drift.subprocess.run")
    def test_both_raise_exceptions(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """If both calls raise, fall back to the empty-tree hash."""
        mock_run.side_effect = OSError("no git")
        result = resolve_diff_base(tmp_path)
        assert result == _EMPTY_TREE

    @patch("harness_governance.state_machine.drift.subprocess.run")
    def test_merge_base_empty_stdout_falls_through(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """merge-base returning empty stdout should fall through."""
        mock_run.side_effect = [
            _completed_process(stdout=""),  # merge-base empty
            _completed_process(stdout="head1\n"),  # HEAD~1
        ]
        result = resolve_diff_base(tmp_path)
        assert result == "head1"

    @patch("harness_governance.state_machine.drift.subprocess.run")
    def test_override_ref_short_circuits_no_git_call(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """With override_ref set, subprocess.run must never be called."""
        resolve_diff_base(tmp_path, override_ref="v1.0")
        mock_run.assert_not_called()


# =========================================================================
# DriftDetectionEngine.declare_scope / load_scope
# =========================================================================


class TestDeclareAndLoadScope:
    """Round-trip persistence tests for ``declare_scope`` and ``load_scope``."""

    def test_declare_scope_writes_json(self, tmp_path: Path) -> None:
        engine = DriftDetectionEngine(tmp_path)
        scope = _make_scope("chg-010", files=("src/a.py", "src/b.py"))
        path = engine.declare_scope(scope)

        assert path.is_file()
        assert path.parent == tmp_path / ".harness" / "scopes"
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["change_id"] == "chg-010"
        assert "src/a.py" in data["declared_files"]

    def test_load_scope_round_trip(self, tmp_path: Path) -> None:
        engine = DriftDetectionEngine(tmp_path)
        scope = _make_scope(
            "chg-020",
            files=("src/x.py",),
            max_files=10,
            max_total_lines=500,
        )
        engine.declare_scope(scope)

        loaded = engine.load_scope("chg-020")
        assert loaded is not None
        assert loaded.change_id == "chg-020"
        assert loaded.declared_files == ("src/x.py",)
        assert loaded.boundary.max_files == 10
        assert loaded.boundary.max_total_lines == 500

    def test_load_scope_missing_returns_none(self, tmp_path: Path) -> None:
        engine = DriftDetectionEngine(tmp_path)
        assert engine.load_scope("nonexistent") is None

    def test_load_scope_corrupted_file_returns_none(self, tmp_path: Path) -> None:
        """A corrupt JSON file should return None, not raise."""
        engine = DriftDetectionEngine(tmp_path)
        scopes_dir = tmp_path / ".harness" / "scopes"
        scopes_dir.mkdir(parents=True)
        (scopes_dir / "bad.json").write_text("{not valid json", encoding="utf-8")
        assert engine.load_scope("bad") is None

    def test_declare_scope_creates_parent_dirs(self, tmp_path: Path) -> None:
        engine = DriftDetectionEngine(tmp_path)
        scope = _make_scope("chg-new")
        path = engine.declare_scope(scope)
        assert path.is_file()
        # The directory should have been auto-created.
        assert (tmp_path / ".harness" / "scopes").is_dir()


# =========================================================================
# DriftDetectionEngine.check_boundary
# =========================================================================


class TestCheckBoundary:
    """Tests for :meth:`DriftDetectionEngine.check_boundary`.

    ``_run_git_diff`` is always mocked so that we control the diff output
    deterministically.
    """

    PATCH_DIFF = "harness_governance.state_machine.drift._run_git_diff"
    PATCH_BASE = "harness_governance.state_machine.drift.resolve_diff_base"

    @patch(PATCH_BASE, return_value="abc12345")
    @patch(PATCH_DIFF, return_value=(["src/a.py", "src/b.py"], 50, 10))
    def test_no_scope_all_in_scope(
        self, _diff: MagicMock, _base: MagicMock, tmp_path: Path
    ) -> None:
        """Without a declared scope, all changes are in-scope (advisory)."""
        engine = DriftDetectionEngine(tmp_path)
        drift = engine.check_boundary("no-such-change")

        assert drift.drift_detected is False
        assert drift.actual_files_changed == ("src/a.py", "src/b.py")
        assert drift.files_out_of_scope == ()

    @patch(PATCH_BASE, return_value="abc12345")
    @patch(PATCH_DIFF, return_value=(["src/a.py", "src/b.py"], 50, 10))
    def test_all_files_in_scope(
        self, _diff: MagicMock, _base: MagicMock, tmp_path: Path
    ) -> None:
        """All changed files match declared scope — no drift."""
        engine = DriftDetectionEngine(tmp_path)
        engine.declare_scope(_make_scope("chg-ok", files=("src/a.py", "src/b.py")))
        drift = engine.check_boundary("chg-ok")
        assert drift.drift_detected is False
        assert drift.files_out_of_scope == ()

    @patch(PATCH_BASE, return_value="abc12345")
    @patch(PATCH_DIFF, return_value=(["src/a.py", "src/rogue.py"], 50, 10))
    def test_out_of_scope_file_detected(
        self, _diff: MagicMock, _base: MagicMock, tmp_path: Path
    ) -> None:
        """A file not in declared_files triggers drift."""
        engine = DriftDetectionEngine(tmp_path)
        engine.declare_scope(_make_scope("chg-drift", files=("src/a.py",)))
        drift = engine.check_boundary("chg-drift")

        assert drift.drift_detected is True
        assert "src/rogue.py" in drift.files_out_of_scope

    @patch(PATCH_BASE, return_value="abc12345")
    @patch(PATCH_DIFF, return_value=(["secrets/keys.pem"], 5, 0))
    def test_forbidden_path_detected(
        self, _diff: MagicMock, _base: MagicMock, tmp_path: Path
    ) -> None:
        """Files matching a forbidden glob are flagged."""
        engine = DriftDetectionEngine(tmp_path)
        engine.declare_scope(
            _make_scope(
                "chg-forbid",
                files=("secrets/keys.pem",),
                forbidden_paths=("secrets/*",),
            )
        )
        drift = engine.check_boundary("chg-forbid")
        assert drift.drift_detected is True
        assert "secrets/keys.pem" in drift.files_in_forbidden_paths

    @patch(PATCH_BASE, return_value="abc12345")
    @patch(PATCH_DIFF, return_value=(["src/a.py"], 50, 10))
    def test_no_drift_when_files_match_and_no_thresholds(
        self, _diff: MagicMock, _base: MagicMock, tmp_path: Path
    ) -> None:
        """No thresholds set, all files declared — clean."""
        engine = DriftDetectionEngine(tmp_path)
        engine.declare_scope(_make_scope("chg-clean", files=("src/a.py",)))
        drift = engine.check_boundary("chg-clean")
        assert drift.drift_detected is False
        assert drift.triggers_decomposition == ()

    @patch(PATCH_BASE, return_value="abc12345")
    @patch(
        PATCH_DIFF,
        return_value=(
            [f"src/file_{i}.py" for i in range(20)],
            100,
            20,
        ),
    )
    def test_decomposition_trigger_via_max_files(
        self, _diff: MagicMock, _base: MagicMock, tmp_path: Path
    ) -> None:
        """Exceeding max_files triggers decomposition."""
        engine = DriftDetectionEngine(tmp_path)
        engine.declare_scope(
            _make_scope(
                "chg-big",
                files=tuple(f"src/file_{i}.py" for i in range(20)),
                max_files=5,
            )
        )
        drift = engine.check_boundary("chg-big")
        assert drift.drift_detected is True
        trigger_names = [t.triggered_by for t in drift.triggers_decomposition]
        assert "max_files" in trigger_names

    @patch(PATCH_BASE, return_value="abc12345")
    @patch(PATCH_DIFF, return_value=(["src/a.py"], 5000, 10))
    def test_decomposition_trigger_via_max_total_lines(
        self, _diff: MagicMock, _base: MagicMock, tmp_path: Path
    ) -> None:
        """Exceeding max_total_lines triggers decomposition."""
        engine = DriftDetectionEngine(tmp_path)
        engine.declare_scope(
            _make_scope(
                "chg-lines",
                files=("src/a.py",),
                max_total_lines=200,
            )
        )
        drift = engine.check_boundary("chg-lines")
        assert drift.drift_detected is True
        trigger_names = [t.triggered_by for t in drift.triggers_decomposition]
        assert "max_total_lines" in trigger_names

    @patch(PATCH_BASE, return_value="abc12345")
    @patch(PATCH_DIFF, return_value=([], 0, 0))
    def test_empty_diff_no_drift(
        self, _diff: MagicMock, _base: MagicMock, tmp_path: Path
    ) -> None:
        """No changes at all — no drift."""
        engine = DriftDetectionEngine(tmp_path)
        engine.declare_scope(_make_scope("chg-empty", files=("src/a.py",)))
        drift = engine.check_boundary("chg-empty")
        assert drift.drift_detected is False

    @patch(PATCH_BASE, return_value="abc12345")
    @patch(PATCH_DIFF, return_value=(["src/a.py"], 10, 5))
    def test_line_stats_propagated(
        self, _diff: MagicMock, _base: MagicMock, tmp_path: Path
    ) -> None:
        """lines_added / lines_deleted come from the diff."""
        engine = DriftDetectionEngine(tmp_path)
        drift = engine.check_boundary("any")
        assert drift.lines_added == 10
        assert drift.lines_deleted == 5

    @patch(PATCH_BASE, return_value="abc12345")
    @patch(PATCH_DIFF, return_value=(["src/a.py"], 10, 5))
    def test_check_boundary_with_base_ref_override(
        self, _diff: MagicMock, _base: MagicMock, tmp_path: Path
    ) -> None:
        """Passing *base_ref* is forwarded to ``resolve_diff_base``."""
        engine = DriftDetectionEngine(tmp_path)
        engine.check_boundary("x", base_ref="v2.0")
        _base.assert_called_once_with(
            tmp_path, default_branch="main", override_ref="v2.0"
        )


# =========================================================================
# DriftDetectionEngine.detect_decomposition_trigger
# =========================================================================


class TestDetectDecompositionTrigger:
    """Tests for the static ``detect_decomposition_trigger`` method."""

    def test_no_triggers_when_within_thresholds(self) -> None:
        boundary = ScopeBoundary(max_files=10, max_total_lines=500)
        triggers = DriftDetectionEngine.detect_decomposition_trigger(
            files_changed=["a.py", "b.py"],
            lines_added=100,
            boundary=boundary,
        )
        assert triggers == []

    def test_max_files_trigger(self) -> None:
        boundary = ScopeBoundary(max_files=3, max_total_lines=0)
        triggers = DriftDetectionEngine.detect_decomposition_trigger(
            files_changed=[f"f{i}.py" for i in range(5)],
            lines_added=10,
            boundary=boundary,
        )
        assert len(triggers) == 1
        assert triggers[0].triggered_by == "max_files"
        assert triggers[0].threshold == 3
        assert triggers[0].actual == 5

    def test_max_total_lines_trigger(self) -> None:
        boundary = ScopeBoundary(max_files=0, max_total_lines=100)
        triggers = DriftDetectionEngine.detect_decomposition_trigger(
            files_changed=["a.py"],
            lines_added=500,
            boundary=boundary,
        )
        assert len(triggers) == 1
        assert triggers[0].triggered_by == "max_total_lines"
        assert triggers[0].threshold == 100
        assert triggers[0].actual == 500

    def test_both_triggers_fire(self) -> None:
        boundary = ScopeBoundary(max_files=2, max_total_lines=50)
        triggers = DriftDetectionEngine.detect_decomposition_trigger(
            files_changed=["a.py", "b.py", "c.py"],
            lines_added=200,
            boundary=boundary,
        )
        names = {t.triggered_by for t in triggers}
        assert names == {"max_files", "max_total_lines"}

    def test_zero_thresholds_never_trigger(self) -> None:
        """A threshold of 0 means 'no limit' — should never fire."""
        boundary = ScopeBoundary(max_files=0, max_total_lines=0)
        triggers = DriftDetectionEngine.detect_decomposition_trigger(
            files_changed=[f"f{i}.py" for i in range(100)],
            lines_added=99_999,
            boundary=boundary,
        )
        assert triggers == []

    def test_exactly_at_threshold_no_trigger(self) -> None:
        """The trigger fires only when *exceeding* the threshold, not at it."""
        boundary = ScopeBoundary(max_files=5, max_total_lines=100)
        triggers = DriftDetectionEngine.detect_decomposition_trigger(
            files_changed=[f"f{i}.py" for i in range(5)],
            lines_added=100,
            boundary=boundary,
        )
        assert triggers == []

    def test_recommendation_text_contains_useful_info(self) -> None:
        boundary = ScopeBoundary(max_files=3, max_total_lines=0)
        triggers = DriftDetectionEngine.detect_decomposition_trigger(
            files_changed=[f"f{i}.py" for i in range(5)],
            lines_added=10,
            boundary=boundary,
        )
        rec = triggers[0].recommendation
        assert "5" in rec  # actual count
        assert "3" in rec  # threshold


# =========================================================================
# ScopeBoundary.for_tier
# =========================================================================


class TestScopeBoundaryForTier:
    """Tests for :meth:`ScopeBoundary.for_tier`."""

    def test_strict_tier(self) -> None:
        b = ScopeBoundary.for_tier("strict")
        assert b.max_files == 8
        assert b.max_lines_per_file == 120
        assert b.max_total_lines == 500

    def test_standard_tier(self) -> None:
        b = ScopeBoundary.for_tier("standard")
        assert b.max_files == 15
        assert b.max_lines_per_file == 200
        assert b.max_total_lines == 1000

    def test_light_tier(self) -> None:
        b = ScopeBoundary.for_tier("light")
        assert b.max_files == 25
        assert b.max_lines_per_file == 300
        assert b.max_total_lines == 2000

    def test_unknown_tier_defaults_to_light(self) -> None:
        """An unknown tier string falls through to the light/default branch."""
        b = ScopeBoundary.for_tier("unknown")
        assert b.max_files == 25

    def test_strict_is_stricter_than_standard(self) -> None:
        strict = ScopeBoundary.for_tier("strict")
        standard = ScopeBoundary.for_tier("standard")
        assert strict.max_files < standard.max_files
        assert strict.max_total_lines < standard.max_total_lines

    def test_standard_is_stricter_than_light(self) -> None:
        standard = ScopeBoundary.for_tier("standard")
        light = ScopeBoundary.for_tier("light")
        assert standard.max_files < light.max_files
        assert standard.max_total_lines < light.max_total_lines


# =========================================================================
# _gate_hook_drift
# =========================================================================


class TestGateHookDrift:
    """Tests for the gate hook ``_gate_hook_drift``."""

    PATCH_DIFF = "harness_governance.state_machine.drift._run_git_diff"
    PATCH_BASE = "harness_governance.state_machine.drift.resolve_diff_base"

    def test_no_change_id_returns_empty(self, tmp_path: Path) -> None:
        """Without a change_id the hook returns no failures."""
        session = MagicMock()
        session.change_id = ""
        session.session_id = ""
        failures = _gate_hook_drift(session, tmp_path)
        assert failures == []

    @patch(PATCH_BASE, return_value="abc12345")
    @patch(PATCH_DIFF, return_value=(["src/a.py"], 10, 5))
    def test_no_drift_no_failures(
        self, _diff: MagicMock, _base: MagicMock, tmp_path: Path
    ) -> None:
        """No drift detected — hook returns empty list."""
        engine = DriftDetectionEngine(tmp_path)
        engine.declare_scope(_make_scope("chg-clean", files=("src/a.py",)))
        session = MagicMock()
        session.change_id = "chg-clean"
        session.session_id = "sess-1"
        failures = _gate_hook_drift(session, tmp_path)
        assert failures == []

    @patch(PATCH_BASE, return_value="abc12345")
    @patch(PATCH_DIFF, return_value=(["src/rogue.py"], 10, 5))
    def test_drift_detected_returns_failures(
        self, _diff: MagicMock, _base: MagicMock, tmp_path: Path
    ) -> None:
        """Out-of-scope files produce failure messages."""
        engine = DriftDetectionEngine(tmp_path)
        engine.declare_scope(_make_scope("chg-drift", files=("src/a.py",)))
        session = MagicMock()
        session.change_id = "chg-drift"
        session.session_id = "sess-2"
        failures = _gate_hook_drift(session, tmp_path)
        assert len(failures) >= 1
        assert any("drift" in f.lower() or "scope" in f.lower() for f in failures)

    @patch(PATCH_BASE, return_value="abc12345")
    @patch(PATCH_DIFF, return_value=(["secrets/key.pem"], 5, 0))
    def test_forbidden_paths_in_hook(
        self, _diff: MagicMock, _base: MagicMock, tmp_path: Path
    ) -> None:
        """Touching forbidden paths generates a failure message."""
        engine = DriftDetectionEngine(tmp_path)
        engine.declare_scope(
            _make_scope(
                "chg-forbidden",
                files=("secrets/key.pem",),
                forbidden_paths=("secrets/*",),
            )
        )
        session = MagicMock()
        session.change_id = "chg-forbidden"
        session.session_id = "sess-3"
        failures = _gate_hook_drift(session, tmp_path)
        assert any("forbidden" in f.lower() for f in failures)

    @patch(PATCH_BASE, return_value="abc12345")
    @patch(
        PATCH_DIFF,
        return_value=(
            [f"src/f{i}.py" for i in range(20)],
            100,
            10,
        ),
    )
    def test_decomposition_trigger_in_hook(
        self, _diff: MagicMock, _base: MagicMock, tmp_path: Path
    ) -> None:
        """Decomposition triggers produce failure messages."""
        engine = DriftDetectionEngine(tmp_path)
        engine.declare_scope(
            _make_scope(
                "chg-big",
                files=tuple(f"src/f{i}.py" for i in range(20)),
                max_files=5,
            )
        )
        session = MagicMock()
        session.change_id = "chg-big"
        session.session_id = "sess-4"
        failures = _gate_hook_drift(session, tmp_path)
        assert any(
            "decomposition" in f.lower() or "split" in f.lower() for f in failures
        )

    def test_no_change_id_no_scopes_dir_returns_empty(self, tmp_path: Path) -> None:
        """No change_id and no scopes dir — advisory, returns empty."""
        session = MagicMock()
        session.change_id = ""
        session.session_id = ""
        failures = _gate_hook_drift(session, tmp_path)
        assert failures == []

    def test_no_change_id_with_scopes_dir_returns_empty(self, tmp_path: Path) -> None:
        """No change_id even with scope files — returns empty (advisory)."""
        scopes_dir = tmp_path / ".harness" / "scopes"
        scopes_dir.mkdir(parents=True)
        (scopes_dir / "other.json").write_text("{}", encoding="utf-8")

        session = MagicMock()
        session.change_id = ""
        session.session_id = ""
        failures = _gate_hook_drift(session, tmp_path)
        assert failures == []

    @patch(PATCH_BASE, return_value="abc12345")
    @patch(PATCH_DIFF, return_value=(["src/a.py"], 10, 5))
    def test_uses_session_id_as_fallback_change_id(
        self, _diff: MagicMock, _base: MagicMock, tmp_path: Path
    ) -> None:
        """When change_id is empty, session_id is used as fallback."""
        engine = DriftDetectionEngine(tmp_path)
        engine.declare_scope(_make_scope("sess-fallback", files=("src/a.py",)))
        session = MagicMock()
        session.change_id = ""
        session.session_id = "sess-fallback"
        failures = _gate_hook_drift(session, tmp_path)
        assert failures == []
