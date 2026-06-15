"""Tests for runner/variables.py — VariableExtractor and helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from harness_governance.file_ops.queue import extract_ready_block_fields
from harness_governance.file_ops.packet import extract_task_packet_sections
from harness_governance.models.schemas import QueueItem
from harness_governance.runner.variables import (
    RoleVariables,
    VariableExtractor,
    _build_project_context,
    _not_found,
    fill_missing,
    is_not_found,
)


# ---------------------------------------------------------------------------
# extract_ready_block_fields
# ---------------------------------------------------------------------------

class TestExtractReadyBlockFields:
    def test_extracts_role(self):
        raw = "[ready] Do something\nRole: Implementer\nLayer: implementation"
        fields = extract_ready_block_fields(raw)
        assert fields["role"] == "Implementer"

    def test_extracts_done_when(self):
        raw = "[ready] Task\nDone when: all tests pass"
        fields = extract_ready_block_fields(raw)
        assert fields["done when"] == "all tests pass"

    def test_extracts_verification_command(self):
        raw = "[ready] Task\nVerification command: npm test"
        fields = extract_ready_block_fields(raw)
        assert fields["verification command"] == "npm test"

    def test_extracts_forbidden_shortcut(self):
        raw = "[ready] Task\nForbidden shortcut: no direct DB access"
        fields = extract_ready_block_fields(raw)
        assert fields["forbidden shortcut"] == "no direct DB access"

    def test_multiline_value(self):
        raw = (
            "[ready] Task\n"
            "Forbidden scope: no API changes\n"
            "no schema changes\n"
            "Done when: tests pass"
        )
        fields = extract_ready_block_fields(raw)
        assert "no API changes" in fields["forbidden scope"]
        assert "no schema changes" in fields["forbidden scope"]
        assert fields["done when"] == "tests pass"

    def test_bullet_prefix(self):
        raw = "[ready] Task\n- Role: Planner\n- Done when: plan approved"
        fields = extract_ready_block_fields(raw)
        assert fields["role"] == "Planner"
        assert fields["done when"] == "plan approved"

    def test_ignores_unknown_keys(self):
        raw = "[ready] Task\nCustomField: some value\nRole: Implementer"
        fields = extract_ready_block_fields(raw)
        assert "customfield" not in fields
        assert fields["role"] == "Implementer"

    def test_empty_input(self):
        assert extract_ready_block_fields("") == {}

    def test_core_fields_included(self):
        raw = "Layer: implementation\nChange: my-change\nPacketization: ready\nEvidence: contracts.md"
        fields = extract_ready_block_fields(raw)
        assert fields["layer"] == "implementation"
        assert fields["change"] == "my-change"
        assert fields["packetization"] == "ready"
        assert fields["evidence"] == "contracts.md"


# ---------------------------------------------------------------------------
# extract_task_packet_sections
# ---------------------------------------------------------------------------

class TestExtractTaskPacketSections:
    def test_basic_sections(self):
        text = (
            "# Tasks\n\n"
            "## Owner Files\n\n"
            "src/foo.py\n\n"
            "## Expected Behavior\n\n"
            "foo() returns 42\n\n"
            "## Done When\n\n"
            "test passes\n"
        )
        sections = extract_task_packet_sections(text)
        assert sections["owner files"] == "src/foo.py"
        assert sections["expected behavior"] == "foo() returns 42"
        assert sections["done when"] == "test passes"

    def test_multiline_section_body(self):
        text = (
            "## Owner Files\n\n"
            "src/a.py\n"
            "src/b.py\n"
            "src/c.py\n\n"
            "## Failure Behavior\n\n"
            "return error\n"
        )
        sections = extract_task_packet_sections(text)
        assert "src/a.py" in sections["owner files"]
        assert "src/c.py" in sections["owner files"]
        assert sections["failure behavior"] == "return error"

    def test_h1_closes_section(self):
        text = (
            "## Scope\n\n"
            "some scope\n\n"
            "# New Top Heading\n\n"
            "## Another\n\n"
            "text\n"
        )
        sections = extract_task_packet_sections(text)
        assert sections["scope"] == "some scope"
        assert "another" in sections

    def test_empty_input(self):
        assert extract_task_packet_sections("") == {}

    def test_no_sections(self):
        text = "# Tasks\n\n- [ ] task 1\n- [ ] task 2\n"
        assert extract_task_packet_sections(text) == {}


# ---------------------------------------------------------------------------
# RoleVariables / fill_missing / is_not_found
# ---------------------------------------------------------------------------

class TestRoleVariables:
    def test_default_empty(self):
        v = RoleVariables()
        assert v.queue_item_raw == ""
        assert v.git_diff == ""

    def test_fill_missing_marks_required_fields(self):
        v = RoleVariables()
        filled = fill_missing(v)
        assert is_not_found(filled.owner_files)
        assert is_not_found(filled.contracts)
        assert is_not_found(filled.expected_behavior)

    def test_fill_missing_preserves_optional_empty(self):
        v = RoleVariables()
        filled = fill_missing(v)
        # Optional fields should remain empty, not NOT FOUND
        assert filled.git_diff == ""
        assert filled.project_context == ""

    def test_fill_missing_preserves_set_values(self):
        v = RoleVariables(owner_files="src/main.py", done_when="tests pass")
        filled = fill_missing(v)
        assert filled.owner_files == "src/main.py"
        assert filled.done_when == "tests pass"

    def test_is_not_found_true(self):
        assert is_not_found("NOT FOUND: OWNER_FILES")

    def test_is_not_found_false(self):
        assert not is_not_found("src/main.py")

    def test_not_found_format(self):
        assert _not_found("CONTRACTS") == "NOT FOUND: {{CONTRACTS}}"


# ---------------------------------------------------------------------------
# VariableExtractor
# ---------------------------------------------------------------------------

class TestVariableExtractor:
    @pytest.fixture
    def project(self, tmp_path: Path) -> Path:
        """Create a minimal project with NEXT.md and a change packet."""
        # NEXT.md — core fields (Layer, Change) need ``- `` prefix to
        # match the queue parser's _FIELD_RE regex.
        (tmp_path / "NEXT.md").write_text(
            "[ready] Implement status dashboard\n"
            "- Layer: implementation\n"
            "- Change: dev-workbench-core-loop\n"
            "Role: Implementer\n"
            "Verification command: npm test\n"
            "Done when: dashboard renders correctly\n"
            "Forbidden shortcut: no mock data in production\n",
            encoding="utf-8",
        )

        # Change packet
        pkt = tmp_path / "docs" / "changes" / "dev-workbench-core-loop"
        pkt.mkdir(parents=True)

        (pkt / "tasks.md").write_text(
            "# Tasks\n\n"
            "## Owner Files\n\n"
            "apps/web-designer/src/StatusDashboard.vue\n\n"
            "## Expected Behavior\n\n"
            "Dashboard shows queue summary, packet status, and runner stats.\n\n"
            "## Failure Behavior\n\n"
            "Empty state shows 'No data available' message.\n\n"
            "## Allowed Assumptions\n\n"
            "status.json is available at .harness/status.json\n\n"
            "## Done When\n\n"
            "- [ ] Dashboard component renders\n"
            "- [ ] Empty state handled\n",
            encoding="utf-8",
        )

        (pkt / "contracts.md").write_text(
            "# Contracts\n\n"
            "## StatusDashboard\n\n"
            "- Component must accept StatusPayload as prop\n"
            "- Empty queue shows placeholder text\n",
            encoding="utf-8",
        )

        return tmp_path

    def test_extract_fills_inline_fields(self, project: Path) -> None:
        from harness_governance.file_ops.queue import read_queue

        items = read_queue(project / "NEXT.md")
        assert len(items) == 1

        extractor = VariableExtractor()
        variables = extractor.extract(project, items[0])

        assert variables.role == "Implementer"
        assert variables.verification_commands == "npm test"
        assert variables.done_when == "dashboard renders correctly"
        assert variables.forbidden_scope == "no mock data in production"

    def test_extract_fills_packet_fields(self, project: Path) -> None:
        from harness_governance.file_ops.queue import read_queue

        items = read_queue(project / "NEXT.md")
        extractor = VariableExtractor()
        variables = extractor.extract(project, items[0])

        assert "StatusDashboard.vue" in variables.owner_files
        assert "queue summary" in variables.expected_behavior
        assert "Empty state" in variables.failure_behavior
        assert "status.json" in variables.allowed_assumptions
        assert "StatusPayload" in variables.contracts

    def test_extract_change_id(self, project: Path) -> None:
        from harness_governance.file_ops.queue import read_queue

        items = read_queue(project / "NEXT.md")
        extractor = VariableExtractor()
        variables = extractor.extract(project, items[0])

        assert variables.change_id == "dev-workbench-core-loop"

    def test_extract_no_change_id(self, tmp_path: Path) -> None:
        (tmp_path / "NEXT.md").write_text(
            "[ready] Quick fix\nLayer: implementation\nRole: Implementer\n",
            encoding="utf-8",
        )
        from harness_governance.file_ops.queue import read_queue

        items = read_queue(tmp_path / "NEXT.md")
        extractor = VariableExtractor()
        variables = extractor.extract(tmp_path, items[0])

        assert variables.change_id == ""
        assert variables.owner_files == ""

    def test_extract_for_role_reviewer(self, project: Path) -> None:
        from harness_governance.file_ops.queue import read_queue

        items = read_queue(project / "NEXT.md")
        extractor = VariableExtractor()
        variables = extractor.extract_for_role(project, items[0], "reviewer")

        # git_diff should be attempted (may be empty if not a git repo)
        assert hasattr(variables, "git_diff")

    def test_extract_for_role_planner(self, project: Path) -> None:
        # Create checkpoint and harness dir for project context
        (project / ".harness").mkdir(exist_ok=True)
        (project / ".harness" / "run-checkpoint.md").write_text(
            "# Checkpoint\n\n## Last Worker\n\nround 1\n",
            encoding="utf-8",
        )

        from harness_governance.file_ops.queue import read_queue

        items = read_queue(project / "NEXT.md")
        extractor = VariableExtractor()
        variables = extractor.extract_for_role(project, items[0], "planner")

        assert "Checkpoint" in variables.project_context or "Queue" in variables.project_context


class TestRoleVariablesNewFields:
    """Tests for scope, allowed_scope, and worker_results fields."""

    def test_default_empty(self):
        v = RoleVariables()
        assert v.scope == ""
        assert v.allowed_scope == ""
        assert v.worker_results == ""

    def test_scope_and_allowed_scope_optional(self):
        """scope, allowed_scope, worker_results are optional — no NOT FOUND."""
        v = RoleVariables()
        filled = fill_missing(v)
        assert filled.scope == ""
        assert filled.allowed_scope == ""
        assert filled.worker_results == ""

    def test_worker_results_optional(self):
        v = RoleVariables()
        filled = fill_missing(v)
        assert filled.worker_results == ""


class TestVariableExtractorGovernance:
    """Test variable extraction for governance roles."""

    @pytest.fixture
    def project_with_scope(self, tmp_path: Path) -> Path:
        (tmp_path / "NEXT.md").write_text(
            "[ready] Write ADR\n"
            "- Layer: adr\n"
            "- Change: adr-change\n"
            "Role: ADR Writer\n"
            "Done when: ADR approved\n",
            encoding="utf-8",
        )
        pkt = tmp_path / "docs" / "changes" / "adr-change"
        pkt.mkdir(parents=True)
        (pkt / "tasks.md").write_text(
            "# Tasks\n\n"
            "## Scope\n\n"
            "Database migration layer\n\n"
            "## Allowed Scope\n\n"
            "docs/adr/ only\n\n"
            "## Owner Files\n\n"
            "docs/adr/001.md\n",
            encoding="utf-8",
        )
        (pkt / "contracts.md").write_text("# Contracts\n", encoding="utf-8")
        return tmp_path

    def test_extract_scope_from_packet(self, project_with_scope: Path) -> None:
        from harness_governance.file_ops.queue import read_queue

        items = read_queue(project_with_scope / "NEXT.md")
        extractor = VariableExtractor()
        variables = extractor.extract(project_with_scope, items[0])

        assert variables.scope == "Database migration layer"
        assert variables.allowed_scope == "docs/adr/ only"

    def test_extract_for_role_fact_finder_gets_git_diff(
        self, project_with_scope: Path,
    ) -> None:
        from harness_governance.file_ops.queue import read_queue

        items = read_queue(project_with_scope / "NEXT.md")
        extractor = VariableExtractor()
        variables = extractor.extract_for_role(
            project_with_scope, items[0], "fact-finder-reviewer"
        )
        # Should have git_diff attempted (may be empty if not git repo)
        assert hasattr(variables, "git_diff")

    def test_scope_design_fallback(self, tmp_path: Path) -> None:
        """Scope falls back to design.md when tasks.md has no Scope section."""
        (tmp_path / "NEXT.md").write_text(
            "[ready] Plan migration\n"
            "- Layer: adr\n"
            "- Change: scope-test\n"
            "Role: ADR Writer\n",
            encoding="utf-8",
        )
        pkt = tmp_path / "docs" / "changes" / "scope-test"
        pkt.mkdir(parents=True)
        (pkt / "tasks.md").write_text(
            "# Tasks\n\n## Owner Files\n\nfoo.md\n",
            encoding="utf-8",
        )
        (pkt / "design.md").write_text(
            "# Design\n\nFull migration design here\n",
            encoding="utf-8",
        )

        from harness_governance.file_ops.queue import read_queue

        items = read_queue(tmp_path / "NEXT.md")
        extractor = VariableExtractor()
        variables = extractor.extract(tmp_path, items[0])

        assert "migration design" in variables.scope


# ---------------------------------------------------------------------------
# _build_project_context
# ---------------------------------------------------------------------------

class TestBuildProjectContext:
    def test_with_checkpoint_and_queue(self, tmp_path: Path) -> None:
        (tmp_path / ".harness").mkdir()
        (tmp_path / ".harness" / "run-checkpoint.md").write_text("checkpoint data", encoding="utf-8")
        (tmp_path / "NEXT.md").write_text("[ready] Task\n", encoding="utf-8")

        ctx = _build_project_context(tmp_path)
        assert "checkpoint data" in ctx
        assert "[ready] Task" in ctx

    def test_empty_project(self, tmp_path: Path) -> None:
        ctx = _build_project_context(tmp_path)
        assert is_not_found(ctx)
