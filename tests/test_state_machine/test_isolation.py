"""Tests for role and subagent isolation — IsolationManager and gate hook."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from harness_governance.state_machine.isolation import (
    _CANONICAL_ROLES,
    _DEFAULT_ROLE_PATHS,
    _DEFAULT_ROLE_ALLOWANCES,
    _gate_hook_isolation,
    IsolationManager,
)
from harness_governance.models.schemas import (
    IsolationRecord,
    IsolationSummary,
    IsolationWorkspace,
)
from tests.conftest import write_permissive_config, seed_session


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    """Verify module-level constants exist and are well-formed."""

    def test_canonical_roles_is_tuple_of_strings(self) -> None:
        assert isinstance(_CANONICAL_ROLES, tuple)
        assert len(_CANONICAL_ROLES) >= 4
        for role in _CANONICAL_ROLES:
            assert isinstance(role, str)

    def test_canonical_roles_contains_expected_members(self) -> None:
        for expected in ("planner", "contract-writer", "implementer", "reviewer"):
            assert expected in _CANONICAL_ROLES

    def test_default_role_paths_covers_all_canonical_roles(self) -> None:
        for role in _CANONICAL_ROLES:
            assert role in _DEFAULT_ROLE_PATHS, f"Missing paths for role: {role}"

    def test_default_role_paths_values_are_glob_lists(self) -> None:
        for role, patterns in _DEFAULT_ROLE_PATHS.items():
            assert isinstance(patterns, list)
            assert len(patterns) > 0, f"Empty glob list for role: {role}"
            for pat in patterns:
                assert isinstance(pat, str)

    def test_default_role_allowances_covers_all_canonical_roles(self) -> None:
        for role in _CANONICAL_ROLES:
            assert role in _DEFAULT_ROLE_ALLOWANCES, f"Missing allowances for role: {role}"

    def test_default_role_allowances_values_are_lists(self) -> None:
        for role, allowed in _DEFAULT_ROLE_ALLOWANCES.items():
            assert isinstance(allowed, list)
            for r in allowed:
                assert isinstance(r, str)

    def test_planner_allowed_paths_include_docs(self) -> None:
        planner_paths = _DEFAULT_ROLE_PATHS["planner"]
        joined = " ".join(planner_paths)
        assert "docs/" in joined

    def test_implementer_allowed_paths_include_src(self) -> None:
        impl_paths = _DEFAULT_ROLE_PATHS["implementer"]
        assert any("src" in p for p in impl_paths)

    def test_all_roles_allow_harness_dir(self) -> None:
        for role, patterns in _DEFAULT_ROLE_PATHS.items():
            assert any(".harness" in p for p in patterns), (
                f"Role {role} missing .harness/** in allowed_paths"
            )


# ---------------------------------------------------------------------------
# create_workspace
# ---------------------------------------------------------------------------


class TestCreateWorkspace:
    """Test IsolationManager.create_workspace()."""

    def test_creates_role_directory(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        ws = mgr.create_workspace("planner", "sess-001")

        role_dir = tmp_path / ".harness" / "isolation" / "sess-001" / "planner"
        assert role_dir.is_dir()

    def test_returns_isolation_workspace(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        ws = mgr.create_workspace("planner", "sess-001")

        assert isinstance(ws, IsolationWorkspace)
        assert ws.role == "planner"
        assert ws.session_id == "sess-001"
        assert ws.isolation_kind == "directory"

    def test_workspace_path_is_relative(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        ws = mgr.create_workspace("implementer", "sess-001")

        # workspace_path should be relative, not absolute
        assert not Path(ws.workspace_path).is_absolute()
        assert "implementer" in ws.workspace_path

    def test_writes_workspace_json(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        mgr.create_workspace("reviewer", "sess-002")

        config_path = (
            tmp_path / ".harness" / "isolation" / "sess-002" / "reviewer" / "workspace.json"
        )
        assert config_path.is_file()
        data = json.loads(config_path.read_text(encoding="utf-8"))
        assert data["role"] == "reviewer"
        assert data["session_id"] == "sess-002"

    def test_appends_ndjson_event(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        mgr.create_workspace("planner", "sess-003")

        ndjson_path = (
            tmp_path / ".harness" / "isolation" / "sess-003" / ".isolation.ndjson"
        )
        assert ndjson_path.is_file()
        lines = ndjson_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) >= 1
        event = json.loads(lines[0])
        assert event["event"] == "workspace_created"
        assert event["role"] == "planner"

    def test_uses_default_paths_for_known_role(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        ws = mgr.create_workspace("planner", "sess-004")

        expected = _DEFAULT_ROLE_PATHS["planner"]
        assert list(ws.allowed_paths) == expected

    def test_uses_default_allowances_for_known_role(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        ws = mgr.create_workspace("implementer", "sess-005")

        expected = _DEFAULT_ROLE_ALLOWANCES["implementer"]
        assert list(ws.allowed_roles) == expected

    def test_custom_allowed_paths_override_defaults(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        custom = ["custom/**", "other/**"]
        ws = mgr.create_workspace("planner", "sess-006", allowed_paths=custom)

        assert list(ws.allowed_paths) == custom

    def test_custom_allowed_roles_override_defaults(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        custom_roles = ["reviewer", "planner"]
        ws = mgr.create_workspace(
            "implementer", "sess-007", allowed_roles=custom_roles
        )

        assert list(ws.allowed_roles) == custom_roles

    def test_unknown_role_gets_harness_default(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        ws = mgr.create_workspace("unknown-role", "sess-008")

        # Unknown role falls back to [".harness/**"]
        assert list(ws.allowed_paths) == [".harness/**"]
        assert list(ws.allowed_roles) == []

    def test_change_id_is_accepted(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        ws = mgr.create_workspace("planner", "sess-009", change_id="chg-001")
        assert ws.role == "planner"

    def test_creates_multiple_roles_in_same_session(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        for role in _CANONICAL_ROLES:
            ws = mgr.create_workspace(role, "sess-010")
            assert ws.role == role

        session_dir = tmp_path / ".harness" / "isolation" / "sess-010"
        for role in _CANONICAL_ROLES:
            assert (session_dir / role).is_dir()
            assert (session_dir / role / "workspace.json").is_file()

    def test_ndjson_log_has_multiple_events(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        for role in ("planner", "implementer"):
            mgr.create_workspace(role, "sess-011")

        ndjson_path = (
            tmp_path / ".harness" / "isolation" / "sess-011" / ".isolation.ndjson"
        )
        lines = ndjson_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2

    def test_created_at_is_populated(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        ws = mgr.create_workspace("planner", "sess-012")
        assert ws.created_at != ""


# ---------------------------------------------------------------------------
# check_violations
# ---------------------------------------------------------------------------


class TestCheckViolations:
    """Test IsolationManager.check_violations()."""

    def test_no_violations_for_allowed_paths(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        mgr.create_workspace("planner", "sess-100")

        violations = mgr.check_violations(
            "planner",
            ["docs/briefs/overview.md", ".harness/config.toml"],
            session_id="sess-100",
        )
        assert violations == []

    def test_violation_for_out_of_scope_file(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        mgr.create_workspace("planner", "sess-101")

        violations = mgr.check_violations(
            "planner",
            ["src/main.py"],
            session_id="sess-101",
        )
        assert "src/main.py" in violations

    def test_multiple_violations(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        mgr.create_workspace("planner", "sess-102")

        violations = mgr.check_violations(
            "planner",
            ["src/main.py", "tests/test_main.py", "docs/briefs/ok.md"],
            session_id="sess-102",
        )
        assert "src/main.py" in violations
        assert "tests/test_main.py" in violations
        assert "docs/briefs/ok.md" not in violations

    def test_cross_role_violation_detected(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        mgr.create_workspace("planner", "sess-103")

        # planner is only allowed to collaborate with contract-writer
        violations = mgr.check_violations(
            "planner",
            [],
            session_id="sess-103",
            cross_role_accesses=["implementer"],
        )
        assert "cross-role:implementer" in violations

    def test_cross_role_access_to_allowed_role_is_fine(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        mgr.create_workspace("planner", "sess-104")

        # planner is allowed to collaborate with contract-writer
        violations = mgr.check_violations(
            "planner",
            [],
            session_id="sess-104",
            cross_role_accesses=["contract-writer"],
        )
        assert violations == []

    def test_cross_role_access_to_self_is_fine(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        mgr.create_workspace("planner", "sess-105")

        violations = mgr.check_violations(
            "planner",
            [],
            session_id="sess-105",
            cross_role_accesses=["planner"],
        )
        assert violations == []

    def test_no_session_id_uses_default_paths(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)

        # Without session_id, falls back to _DEFAULT_ROLE_PATHS
        violations = mgr.check_violations(
            "planner",
            ["src/main.py"],
        )
        assert "src/main.py" in violations

    def test_no_session_id_allowed_path_passes(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)

        violations = mgr.check_violations(
            "planner",
            ["docs/briefs/overview.md"],
        )
        assert violations == []

    def test_implementer_src_is_allowed(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        mgr.create_workspace("implementer", "sess-106")

        violations = mgr.check_violations(
            "implementer",
            ["src/app.py", "tests/test_app.py"],
            session_id="sess-106",
        )
        assert violations == []

    def test_reviewer_docs_is_allowed(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        mgr.create_workspace("reviewer", "sess-107")

        violations = mgr.check_violations(
            "reviewer",
            ["docs/architecture/overview.md"],
            session_id="sess-107",
        )
        assert violations == []

    def test_combined_file_and_cross_role_violations(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        mgr.create_workspace("planner", "sess-108")

        violations = mgr.check_violations(
            "planner",
            ["src/main.py"],
            session_id="sess-108",
            cross_role_accesses=["reviewer"],
        )
        assert "src/main.py" in violations
        assert "cross-role:reviewer" in violations

    def test_cross_role_without_workspace_config_ignored(self, tmp_path: Path) -> None:
        """Cross-role checks require a persisted workspace; without one, skip."""
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)

        # No workspace created -> ws is None -> cross_role_accesses check skipped
        violations = mgr.check_violations(
            "planner",
            ["docs/briefs/ok.md"],
            session_id="nonexistent",
            cross_role_accesses=["implementer"],
        )
        # file passes (default paths), cross-role is skipped because ws is None
        assert violations == []


# ---------------------------------------------------------------------------
# verify_workspace
# ---------------------------------------------------------------------------


class TestVerifyWorkspace:
    """Test IsolationManager.verify_workspace()."""

    def test_returns_isolation_summary(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        mgr.create_workspace("planner", "sess-200")

        summary = mgr.verify_workspace("sess-200")
        assert isinstance(summary, IsolationSummary)

    def test_roles_isolated_includes_created_role(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        mgr.create_workspace("planner", "sess-201")

        summary = mgr.verify_workspace("sess-201")
        assert "planner" in summary.roles_isolated

    def test_roles_isolated_includes_all_created_roles(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        for role in ("planner", "implementer", "reviewer"):
            mgr.create_workspace(role, "sess-202")

        summary = mgr.verify_workspace("sess-202")
        for role in ("planner", "implementer", "reviewer"):
            assert role in summary.roles_isolated

    def test_roles_isolated_is_sorted(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        for role in ("reviewer", "planner", "implementer"):
            mgr.create_workspace(role, "sess-203")

        summary = mgr.verify_workspace("sess-203")
        assert list(summary.roles_isolated) == sorted(summary.roles_isolated)

    def test_no_violations_when_clean(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        mgr.create_workspace("planner", "sess-204")

        summary = mgr.verify_workspace("sess-204")
        assert summary.cross_role_violations == ()
        assert summary.files_outside_scope == ()
        assert summary.workspaces_valid is True

    def test_violation_detected_in_log(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        mgr.create_workspace("planner", "sess-205")

        # Manually append a violation event
        mgr.append_event(
            IsolationRecord(
                event="violation_detected",
                role="planner",
                workspace_path=".harness/isolation/sess-205/planner",
                session_id="sess-205",
                files_touched=("src/main.py",),
            ),
            session_id="sess-205",
        )

        summary = mgr.verify_workspace("sess-205")
        assert len(summary.cross_role_violations) == 1
        assert summary.cross_role_violations[0].role == "planner"
        assert "src/main.py" in summary.files_outside_scope
        assert summary.workspaces_valid is False

    def test_multiple_violations_in_log(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        mgr.create_workspace("planner", "sess-206")

        for f in ("src/a.py", "src/b.py"):
            mgr.append_event(
                IsolationRecord(
                    event="violation_detected",
                    role="planner",
                    workspace_path=".harness/isolation/sess-206/planner",
                    session_id="sess-206",
                    files_touched=(f,),
                ),
                session_id="sess-206",
            )

        summary = mgr.verify_workspace("sess-206")
        assert len(summary.cross_role_violations) == 2
        assert "src/a.py" in summary.files_outside_scope
        assert "src/b.py" in summary.files_outside_scope

    def test_enforcement_level_is_detective(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        mgr.create_workspace("planner", "sess-207")

        summary = mgr.verify_workspace("sess-207")
        assert summary.enforcement_level == "detective"

    def test_empty_session_has_no_roles(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)

        summary = mgr.verify_workspace("nonexistent-session")
        assert summary.roles_isolated == ()
        assert summary.workspaces_valid is True  # no violations = valid

    def test_workspace_json_roles_discovered(self, tmp_path: Path) -> None:
        """Roles from workspace.json are discovered even without NDJSON events."""
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)

        # Create workspace directories and configs manually without NDJSON events
        session_dir = tmp_path / ".harness" / "isolation" / "sess-208"
        role_dir = session_dir / "contract-writer"
        role_dir.mkdir(parents=True, exist_ok=True)
        ws = IsolationWorkspace(
            role="contract-writer",
            workspace_path=str(role_dir.relative_to(tmp_path)),
            session_id="sess-208",
        )
        (role_dir / "workspace.json").write_text(
            ws.model_dump_json(indent=2), encoding="utf-8"
        )

        summary = mgr.verify_workspace("sess-208")
        assert "contract-writer" in summary.roles_isolated

    def test_files_outside_scope_is_sorted(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        mgr.create_workspace("planner", "sess-209")

        for f in ("z_file.py", "a_file.py", "m_file.py"):
            mgr.append_event(
                IsolationRecord(
                    event="violation_detected",
                    role="planner",
                    workspace_path=".harness/isolation/sess-209/planner",
                    session_id="sess-209",
                    files_touched=(f,),
                ),
                session_id="sess-209",
            )

        summary = mgr.verify_workspace("sess-209")
        assert list(summary.files_outside_scope) == sorted(
            summary.files_outside_scope
        )


# ---------------------------------------------------------------------------
# load_workspace
# ---------------------------------------------------------------------------


class TestLoadWorkspace:
    """Test IsolationManager.load_workspace()."""

    def test_load_existing_workspace(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        mgr.create_workspace("planner", "sess-300")

        ws = mgr.load_workspace("sess-300", "planner")
        assert ws is not None
        assert ws.role == "planner"
        assert ws.session_id == "sess-300"

    def test_load_nonexistent_workspace_returns_none(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)

        ws = mgr.load_workspace("nonexistent", "planner")
        assert ws is None

    def test_load_workspace_preserves_allowed_paths(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        custom_paths = ["custom/**", "other/**"]
        mgr.create_workspace("planner", "sess-301", allowed_paths=custom_paths)

        ws = mgr.load_workspace("sess-301", "planner")
        assert ws is not None
        assert list(ws.allowed_paths) == custom_paths

    def test_load_workspace_preserves_allowed_roles(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        custom_roles = ["reviewer"]
        mgr.create_workspace("implementer", "sess-302", allowed_roles=custom_roles)

        ws = mgr.load_workspace("sess-302", "implementer")
        assert ws is not None
        assert list(ws.allowed_roles) == custom_roles

    def test_load_workspace_with_corrupted_json(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        mgr.create_workspace("planner", "sess-303")

        # Corrupt the workspace.json
        config_path = (
            tmp_path / ".harness" / "isolation" / "sess-303" / "planner" / "workspace.json"
        )
        config_path.write_text("not valid json {{{", encoding="utf-8")

        ws = mgr.load_workspace("sess-303", "planner")
        assert ws is None  # Graceful degradation


# ---------------------------------------------------------------------------
# _matches_any_glob (static method)
# ---------------------------------------------------------------------------


class TestMatchesAnyGlob:
    """Test IsolationManager._matches_any_glob()."""

    def test_exact_match(self) -> None:
        assert IsolationManager._matches_any_glob("README.md", ["README.md"]) is True

    def test_wildcard_match(self) -> None:
        assert IsolationManager._matches_any_glob("README.md", ["*.md"]) is True

    def test_recursive_glob_match(self) -> None:
        assert IsolationManager._matches_any_glob(
            "src/app/main.py", ["src/**"]
        ) is True

    def test_no_match(self) -> None:
        assert IsolationManager._matches_any_glob("src/main.py", ["docs/**"]) is False

    def test_empty_patterns(self) -> None:
        assert IsolationManager._matches_any_glob("any/file.py", []) is False

    def test_multiple_patterns_one_matches(self) -> None:
        assert IsolationManager._matches_any_glob(
            "tests/test_main.py",
            ["src/**", "tests/**", "docs/**"],
        ) is True

    def test_harness_glob(self) -> None:
        assert IsolationManager._matches_any_glob(
            ".harness/config.toml", [".harness/**"]
        ) is True

    def test_fnmatch_style_double_star(self) -> None:
        # fnmatch treats ** same as * (no recursive semantics)
        assert IsolationManager._matches_any_glob(
            "docs/briefs/overview.md", ["docs/briefs/**"]
        ) is True

    def test_star_matches_extension(self) -> None:
        assert IsolationManager._matches_any_glob("CHANGELOG.md", ["*.md"]) is True

    def test_no_match_different_extension(self) -> None:
        assert IsolationManager._matches_any_glob("main.py", ["*.md"]) is False


# ---------------------------------------------------------------------------
# append_event
# ---------------------------------------------------------------------------


class TestAppendEvent:
    """Test IsolationManager.append_event()."""

    def test_append_creates_ndjson_file(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)

        record = IsolationRecord(
            event="file_accessed",
            role="planner",
            workspace_path=".harness/isolation/sess-400/planner",
            session_id="sess-400",
            files_touched=("docs/briefs/overview.md",),
        )
        result = mgr.append_event(record, session_id="sess-400")
        assert result is True

        ndjson_path = (
            tmp_path / ".harness" / "isolation" / "sess-400" / ".isolation.ndjson"
        )
        assert ndjson_path.is_file()

    def test_append_multiple_events(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)

        for i in range(3):
            record = IsolationRecord(
                event="file_accessed",
                role="planner",
                workspace_path=".harness/isolation/sess-401/planner",
                session_id="sess-401",
                files_touched=(f"docs/file_{i}.md",),
            )
            mgr.append_event(record, session_id="sess-401")

        ndjson_path = (
            tmp_path / ".harness" / "isolation" / "sess-401" / ".isolation.ndjson"
        )
        lines = ndjson_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 3

    def test_appended_record_is_valid_json(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)

        record = IsolationRecord(
            event="workspace_created",
            role="implementer",
            workspace_path=".harness/isolation/sess-402/implementer",
            session_id="sess-402",
        )
        mgr.append_event(record, session_id="sess-402")

        ndjson_path = (
            tmp_path / ".harness" / "isolation" / "sess-402" / ".isolation.ndjson"
        )
        line = ndjson_path.read_text(encoding="utf-8").strip()
        data = json.loads(line)
        assert data["event"] == "workspace_created"
        assert data["role"] == "implementer"


# ---------------------------------------------------------------------------
# _gate_hook_isolation
# ---------------------------------------------------------------------------


class TestGateHookIsolation:
    """Test the _gate_hook_isolation READINESS gate hook."""

    def test_no_session_id_returns_empty(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        session = SimpleNamespace(session_id="")
        failures = _gate_hook_isolation(session, tmp_path)
        assert failures == []

    def test_missing_session_id_attribute_returns_empty(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        session = SimpleNamespace()  # no session_id attribute
        failures = _gate_hook_isolation(session, tmp_path)
        assert failures == []

    def test_no_workspaces_reports_failure(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        session = SimpleNamespace(session_id="sess-500")
        failures = _gate_hook_isolation(session, tmp_path)

        assert len(failures) >= 1
        assert any("No isolation workspaces" in f for f in failures)

    def test_clean_workspace_passes(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        mgr.create_workspace("planner", "sess-501")

        session = SimpleNamespace(session_id="sess-501")
        failures = _gate_hook_isolation(session, tmp_path)
        assert failures == []

    def test_violation_is_reported(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        mgr.create_workspace("planner", "sess-502")

        # Append a violation
        mgr.append_event(
            IsolationRecord(
                event="violation_detected",
                role="planner",
                workspace_path=".harness/isolation/sess-502/planner",
                session_id="sess-502",
                files_touched=("src/secret.py",),
            ),
            session_id="sess-502",
        )

        session = SimpleNamespace(session_id="sess-502")
        failures = _gate_hook_isolation(session, tmp_path)

        assert len(failures) >= 1
        # Should mention the violation or out-of-scope files
        combined = " ".join(failures)
        assert "planner" in combined or "src/secret.py" in combined

    def test_violations_capped_at_five(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        mgr.create_workspace("planner", "sess-503")

        # Append many violations
        for i in range(10):
            mgr.append_event(
                IsolationRecord(
                    event="violation_detected",
                    role="planner",
                    workspace_path=".harness/isolation/sess-503/planner",
                    session_id="sess-503",
                    files_touched=(f"src/file_{i}.py",),
                ),
                session_id="sess-503",
            )

        session = SimpleNamespace(session_id="sess-503")
        failures = _gate_hook_isolation(session, tmp_path)

        # Count violation-specific failures (exclude "files outside scope" line)
        violation_failures = [f for f in failures if "Isolation violation" in f]
        assert len(violation_failures) <= 5

    def test_out_of_scope_files_reported(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        mgr.create_workspace("planner", "sess-504")

        mgr.append_event(
            IsolationRecord(
                event="violation_detected",
                role="planner",
                workspace_path=".harness/isolation/sess-504/planner",
                session_id="sess-504",
                files_touched=("src/out_of_scope.py",),
            ),
            session_id="sess-504",
        )

        session = SimpleNamespace(session_id="sess-504")
        failures = _gate_hook_isolation(session, tmp_path)

        combined = " ".join(failures)
        assert "src/out_of_scope.py" in combined

    def test_multiple_roles_all_clean(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        for role in ("planner", "implementer"):
            mgr.create_workspace(role, "sess-505")

        session = SimpleNamespace(session_id="sess-505")
        failures = _gate_hook_isolation(session, tmp_path)
        assert failures == []


# ---------------------------------------------------------------------------
# Integration: create -> check -> verify round-trip
# ---------------------------------------------------------------------------


class TestIsolationRoundTrip:
    """End-to-end test: create workspace, check files, verify summary."""

    def test_clean_round_trip(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)

        # Create workspaces for all canonical roles
        for role in _CANONICAL_ROLES:
            mgr.create_workspace(role, "sess-rt-001")

        # Check files within scope
        violations = mgr.check_violations(
            "planner",
            ["docs/briefs/overview.md", ".harness/config.toml"],
            session_id="sess-rt-001",
        )
        assert violations == []

        # Verify workspace
        summary = mgr.verify_workspace("sess-rt-001")
        assert summary.workspaces_valid is True
        assert len(summary.roles_isolated) == len(_CANONICAL_ROLES)

    def test_violation_round_trip(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        mgr.create_workspace("planner", "sess-rt-002")

        # Check files out of scope
        violations = mgr.check_violations(
            "planner",
            ["src/main.py"],
            session_id="sess-rt-002",
        )
        assert "src/main.py" in violations

        # Record the violation
        mgr.append_event(
            IsolationRecord(
                event="violation_detected",
                role="planner",
                workspace_path=".harness/isolation/sess-rt-002/planner",
                session_id="sess-rt-002",
                files_touched=tuple(violations),
            ),
            session_id="sess-rt-002",
        )

        # Verify picks up the violation
        summary = mgr.verify_workspace("sess-rt-002")
        assert summary.workspaces_valid is False
        assert "src/main.py" in summary.files_outside_scope

    def test_load_after_create(self, tmp_path: Path) -> None:
        write_permissive_config(tmp_path)
        mgr = IsolationManager(tmp_path)
        original = mgr.create_workspace("implementer", "sess-rt-003")

        loaded = mgr.load_workspace("sess-rt-003", "implementer")
        assert loaded is not None
        assert loaded.role == original.role
        assert loaded.session_id == original.session_id
        assert loaded.allowed_paths == original.allowed_paths
        assert loaded.allowed_roles == original.allowed_roles
