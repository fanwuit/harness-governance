"""Tests for SkillChainTracer — skill invocation chain tracing and audit.

Covers: start_invocation, end_invocation, record_full_invocation,
build_tree, compute_report, validate_chain_integrity, to_mermaid,
to_ascii_tree, and gate hooks _gate_hook_skill_chain_verification
and _gate_hook_skill_chain_review.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from harness_governance.models.schemas import (
    InvocationTreeNode,
    SkillChainReport,
    SkillInvocation,
)
from harness_governance.state_machine.skill_chain import (
    SkillChainTracer,
    _gate_hook_skill_chain_review,
    _gate_hook_skill_chain_verification,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SESSION_ID = "test-session-001"


def _make_tracer(tmp_path: Path) -> SkillChainTracer:
    """Create a SkillChainTracer rooted at *tmp_path*."""
    return SkillChainTracer(tmp_path)


def _start_and_end(
    tracer: SkillChainTracer,
    *,
    parent_call_id: str | None = None,
    child_skill: str = "implementer",
    session_id: str = SESSION_ID,
    exit_code: int = 0,
    verdict: str = "success",
) -> str:
    """Convenience: start + immediately end an invocation.  Returns call_id."""
    call_id = tracer.start_invocation(
        parent_call_id=parent_call_id,
        child_skill=child_skill,
        session_id=session_id,
    )
    tracer.end_invocation(call_id, exit_code=exit_code, verdict=verdict)
    return call_id


def _seed_chain(tmp_path: Path, session_id: str = SESSION_ID) -> SkillChainTracer:
    """Create a tracer with a small parent → child chain already persisted."""
    tracer = _make_tracer(tmp_path)
    root_id = tracer.start_invocation(
        parent_call_id=None,
        child_skill="orchestrator",
        session_id=session_id,
    )
    tracer.end_invocation(root_id, exit_code=0, verdict="success")

    child_id = tracer.start_invocation(
        parent_call_id=root_id,
        child_skill="implementer",
        session_id=session_id,
    )
    tracer.end_invocation(child_id, exit_code=0, verdict="success")

    grandchild_id = tracer.start_invocation(
        parent_call_id=child_id,
        child_skill="verifier",
        session_id=session_id,
    )
    tracer.end_invocation(grandchild_id, exit_code=0, verdict="success")

    return tracer


# ===========================================================================
# start_invocation
# ===========================================================================


class TestStartInvocation:
    def test_returns_uuid_hex_string(self, tmp_path: Path) -> None:
        tracer = _make_tracer(tmp_path)
        call_id = tracer.start_invocation(
            parent_call_id=None,
            child_skill="planner",
            session_id=SESSION_ID,
        )
        assert isinstance(call_id, str)
        assert len(call_id) == 32  # uuid4 hex

    def test_stores_in_active_calls(self, tmp_path: Path) -> None:
        tracer = _make_tracer(tmp_path)
        call_id = tracer.start_invocation(
            parent_call_id=None,
            child_skill="planner",
            session_id=SESSION_ID,
        )
        assert call_id in tracer._active_calls

    def test_active_call_has_correct_skill(self, tmp_path: Path) -> None:
        tracer = _make_tracer(tmp_path)
        call_id = tracer.start_invocation(
            parent_call_id=None,
            child_skill="reviewer",
            role="reviewer",
            session_id=SESSION_ID,
        )
        inv = tracer._active_calls[call_id]
        assert inv.child_skill == "reviewer"
        assert inv.role == "reviewer"

    def test_does_not_persist_until_end(self, tmp_path: Path) -> None:
        tracer = _make_tracer(tmp_path)
        tracer.start_invocation(
            parent_call_id=None,
            child_skill="planner",
            session_id=SESSION_ID,
        )
        # NDJSON file should not exist yet
        ndjson_path = tmp_path / ".harness" / "skill-chains" / f"{SESSION_ID}.ndjson"
        assert not ndjson_path.exists()

    def test_multiple_starts_produce_unique_ids(self, tmp_path: Path) -> None:
        tracer = _make_tracer(tmp_path)
        id1 = tracer.start_invocation(parent_call_id=None, child_skill="a", session_id=SESSION_ID)
        id2 = tracer.start_invocation(parent_call_id=None, child_skill="b", session_id=SESSION_ID)
        assert id1 != id2

    def test_records_parent_call_id(self, tmp_path: Path) -> None:
        tracer = _make_tracer(tmp_path)
        parent_id = tracer.start_invocation(parent_call_id=None, child_skill="root", session_id=SESSION_ID)
        child_id = tracer.start_invocation(parent_call_id=parent_id, child_skill="child", session_id=SESSION_ID)
        inv = tracer._active_calls[child_id]
        assert inv.parent_call_id == parent_id

    def test_records_layer_and_round(self, tmp_path: Path) -> None:
        tracer = _make_tracer(tmp_path)
        call_id = tracer.start_invocation(
            parent_call_id=None,
            child_skill="impl",
            session_id=SESSION_ID,
            layer="implementation",
            round_index=3,
        )
        inv = tracer._active_calls[call_id]
        assert inv.layer == "implementation"
        assert inv.round_index == 3

    def test_records_files_passed(self, tmp_path: Path) -> None:
        tracer = _make_tracer(tmp_path)
        call_id = tracer.start_invocation(
            parent_call_id=None,
            child_skill="impl",
            session_id=SESSION_ID,
            files_passed=["a.py", "b.py"],
        )
        inv = tracer._active_calls[call_id]
        assert inv.files_passed == ("a.py", "b.py")


# ===========================================================================
# end_invocation
# ===========================================================================


class TestEndInvocation:
    def test_returns_completed_invocation(self, tmp_path: Path) -> None:
        tracer = _make_tracer(tmp_path)
        call_id = tracer.start_invocation(
            parent_call_id=None, child_skill="planner", session_id=SESSION_ID
        )
        result = tracer.end_invocation(call_id, exit_code=0, verdict="success")
        assert result is not None
        assert isinstance(result, SkillInvocation)

    def test_sets_finished_at(self, tmp_path: Path) -> None:
        tracer = _make_tracer(tmp_path)
        call_id = tracer.start_invocation(
            parent_call_id=None, child_skill="planner", session_id=SESSION_ID
        )
        result = tracer.end_invocation(call_id)
        assert result is not None
        assert result.finished_at != ""

    def test_computes_duration(self, tmp_path: Path) -> None:
        tracer = _make_tracer(tmp_path)
        call_id = tracer.start_invocation(
            parent_call_id=None, child_skill="planner", session_id=SESSION_ID
        )
        result = tracer.end_invocation(call_id)
        assert result is not None
        assert result.duration_seconds >= 0.0

    def test_persists_to_ndjson(self, tmp_path: Path) -> None:
        tracer = _make_tracer(tmp_path)
        call_id = tracer.start_invocation(
            parent_call_id=None, child_skill="planner", session_id=SESSION_ID
        )
        tracer.end_invocation(call_id)
        ndjson_path = tmp_path / ".harness" / "skill-chains" / f"{SESSION_ID}.ndjson"
        assert ndjson_path.exists()
        content = ndjson_path.read_text(encoding="utf-8").strip()
        assert len(content) > 0
        record = json.loads(content.splitlines()[0])
        assert record["child_skill"] == "planner"

    def test_removes_from_active_calls(self, tmp_path: Path) -> None:
        tracer = _make_tracer(tmp_path)
        call_id = tracer.start_invocation(
            parent_call_id=None, child_skill="planner", session_id=SESSION_ID
        )
        tracer.end_invocation(call_id)
        assert call_id not in tracer._active_calls

    def test_unknown_call_id_returns_none(self, tmp_path: Path) -> None:
        tracer = _make_tracer(tmp_path)
        result = tracer.end_invocation("nonexistent-id")
        assert result is None

    def test_records_exit_code_and_verdict(self, tmp_path: Path) -> None:
        tracer = _make_tracer(tmp_path)
        call_id = tracer.start_invocation(
            parent_call_id=None, child_skill="planner", session_id=SESSION_ID
        )
        result = tracer.end_invocation(call_id, exit_code=1, verdict="failure")
        assert result is not None
        assert result.exit_code == 1
        assert result.verdict == "failure"

    def test_records_files_returned(self, tmp_path: Path) -> None:
        tracer = _make_tracer(tmp_path)
        call_id = tracer.start_invocation(
            parent_call_id=None, child_skill="planner", session_id=SESSION_ID
        )
        result = tracer.end_invocation(
            call_id, files_returned=["output.py"]
        )
        assert result is not None
        assert result.files_returned == ("output.py",)


# ===========================================================================
# record_full_invocation
# ===========================================================================


class TestRecordFullInvocation:
    def test_appends_to_ndjson(self, tmp_path: Path) -> None:
        tracer = _make_tracer(tmp_path)
        inv = SkillInvocation(
            call_id="abc123",
            parent_call_id=None,
            child_skill="coder",
            session_id=SESSION_ID,
            started_at="2026-06-16T10:00:00+00:00",
            finished_at="2026-06-16T10:00:05+00:00",
            duration_seconds=5.0,
            exit_code=0,
            verdict="success",
        )
        result = tracer.record_full_invocation(inv)
        assert result is True
        ndjson_path = tmp_path / ".harness" / "skill-chains" / f"{SESSION_ID}.ndjson"
        assert ndjson_path.exists()

    def test_skips_invocation_without_session_id(self, tmp_path: Path) -> None:
        tracer = _make_tracer(tmp_path)
        inv = SkillInvocation(
            call_id="abc123",
            child_skill="coder",
            session_id="",
        )
        result = tracer.record_full_invocation(inv)
        assert result is False

    def test_multiple_records_in_same_file(self, tmp_path: Path) -> None:
        tracer = _make_tracer(tmp_path)
        for i in range(3):
            inv = SkillInvocation(
                call_id=f"id-{i}",
                child_skill=f"skill-{i}",
                session_id=SESSION_ID,
                started_at="2026-06-16T10:00:00+00:00",
                finished_at="2026-06-16T10:00:01+00:00",
            )
            tracer.record_full_invocation(inv)
        ndjson_path = tmp_path / ".harness" / "skill-chains" / f"{SESSION_ID}.ndjson"
        lines = ndjson_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 3


# ===========================================================================
# build_tree
# ===========================================================================


class TestBuildTree:
    def test_returns_none_for_empty_session(self, tmp_path: Path) -> None:
        tracer = _make_tracer(tmp_path)
        tree = tracer.build_tree("nonexistent-session")
        assert tree is None

    def test_builds_single_root(self, tmp_path: Path) -> None:
        tracer = _make_tracer(tmp_path)
        _start_and_end(tracer)
        tree = tracer.build_tree(SESSION_ID)
        assert tree is not None
        assert isinstance(tree, InvocationTreeNode)

    def test_parent_child_relationship(self, tmp_path: Path) -> None:
        tracer = _seed_chain(tmp_path)
        tree = tracer.build_tree(SESSION_ID)
        assert tree is not None
        # Root should be orchestrator
        assert tree.skill == "orchestrator"
        # Should have one child: implementer
        assert len(tree.children) == 1
        assert tree.children[0].skill == "implementer"
        # Grandchild: verifier
        assert len(tree.children[0].children) == 1
        assert tree.children[0].children[0].skill == "verifier"

    def test_tree_node_has_call_id(self, tmp_path: Path) -> None:
        tracer = _seed_chain(tmp_path)
        tree = tracer.build_tree(SESSION_ID)
        assert tree is not None
        assert tree.call_id != ""

    def test_tree_with_multiple_roots(self, tmp_path: Path) -> None:
        """Two invocations with no parent should get a synthetic root."""
        tracer = _make_tracer(tmp_path)
        _start_and_end(tracer, child_skill="root-a")
        _start_and_end(tracer, child_skill="root-b")
        tree = tracer.build_tree(SESSION_ID)
        assert tree is not None
        # Should be a synthetic session root wrapping both
        assert tree.skill == "(session)"
        assert len(tree.children) == 2


# ===========================================================================
# compute_report
# ===========================================================================


class TestComputeReport:
    def test_empty_session(self, tmp_path: Path) -> None:
        tracer = _make_tracer(tmp_path)
        report = tracer.compute_report("empty-session")
        assert isinstance(report, SkillChainReport)
        assert report.total_invocations == 0

    def test_total_invocations(self, tmp_path: Path) -> None:
        tracer = _seed_chain(tmp_path)
        report = tracer.compute_report(SESSION_ID)
        assert report.total_invocations == 3

    def test_max_depth(self, tmp_path: Path) -> None:
        tracer = _seed_chain(tmp_path)
        report = tracer.compute_report(SESSION_ID)
        assert report.max_depth == 2  # root=0, child=1, grandchild=2

    def test_unique_skills(self, tmp_path: Path) -> None:
        tracer = _seed_chain(tmp_path)
        report = tracer.compute_report(SESSION_ID)
        assert "orchestrator" in report.unique_skills
        assert "implementer" in report.unique_skills
        assert "verifier" in report.unique_skills

    def test_longest_chain(self, tmp_path: Path) -> None:
        tracer = _seed_chain(tmp_path)
        report = tracer.compute_report(SESSION_ID)
        assert len(report.longest_chain) == 3  # root → child → grandchild

    def test_orphan_invocations(self, tmp_path: Path) -> None:
        tracer = _make_tracer(tmp_path)
        # Create an invocation with a nonexistent parent
        inv = SkillInvocation(
            call_id="orphan-1",
            parent_call_id="nonexistent-parent",
            child_skill="lost-skill",
            session_id=SESSION_ID,
            started_at="2026-06-16T10:00:00+00:00",
            finished_at="2026-06-16T10:00:01+00:00",
        )
        tracer.record_full_invocation(inv)
        report = tracer.compute_report(SESSION_ID)
        assert "orphan-1" in report.orphan_invocations

    def test_no_orphans_in_clean_chain(self, tmp_path: Path) -> None:
        tracer = _seed_chain(tmp_path)
        report = tracer.compute_report(SESSION_ID)
        assert len(report.orphan_invocations) == 0

    def test_report_has_generated_at(self, tmp_path: Path) -> None:
        tracer = _seed_chain(tmp_path)
        report = tracer.compute_report(SESSION_ID)
        assert report.generated_at != ""

    def test_report_includes_tree(self, tmp_path: Path) -> None:
        tracer = _seed_chain(tmp_path)
        report = tracer.compute_report(SESSION_ID)
        assert report.tree is not None
        assert isinstance(report.tree, InvocationTreeNode)

    def test_flat_chain_depth_zero(self, tmp_path: Path) -> None:
        tracer = _make_tracer(tmp_path)
        _start_and_end(tracer, child_skill="solo")
        report = tracer.compute_report(SESSION_ID)
        assert report.max_depth == 0
        assert report.total_invocations == 1


# ===========================================================================
# validate_chain_integrity
# ===========================================================================


class TestValidateChainIntegrity:
    def test_no_records_returns_issue(self, tmp_path: Path) -> None:
        tracer = _make_tracer(tmp_path)
        issues = tracer.validate_chain_integrity("no-session")
        assert len(issues) == 1
        assert "No skill invocation records found" in issues[0]

    def test_clean_chain_no_issues(self, tmp_path: Path) -> None:
        tracer = _seed_chain(tmp_path)
        issues = tracer.validate_chain_integrity(SESSION_ID)
        assert issues == []

    def test_detects_orphan(self, tmp_path: Path) -> None:
        tracer = _make_tracer(tmp_path)
        inv = SkillInvocation(
            call_id="orphan-x",
            parent_call_id="missing-parent",
            child_skill="lost",
            session_id=SESSION_ID,
            started_at="2026-06-16T10:00:00+00:00",
            finished_at="2026-06-16T10:00:01+00:00",
        )
        tracer.record_full_invocation(inv)
        issues = tracer.validate_chain_integrity(SESSION_ID)
        assert any("Orphan invocation" in i for i in issues)

    def test_detects_incomplete_invocation(self, tmp_path: Path) -> None:
        tracer = _make_tracer(tmp_path)
        inv = SkillInvocation(
            call_id="incomplete-1",
            child_skill="unfinished",
            session_id=SESSION_ID,
            started_at="2026-06-16T10:00:00+00:00",
            finished_at="",  # never finished
        )
        tracer.record_full_invocation(inv)
        issues = tracer.validate_chain_integrity(SESSION_ID)
        assert any("Incomplete invocation" in i for i in issues)

    def test_no_cycles_in_normal_chain(self, tmp_path: Path) -> None:
        tracer = _seed_chain(tmp_path)
        issues = tracer.validate_chain_integrity(SESSION_ID)
        cycle_issues = [i for i in issues if "Cycle" in i]
        assert len(cycle_issues) == 0


# ===========================================================================
# to_mermaid
# ===========================================================================


class TestToMermaid:
    def test_empty_session(self, tmp_path: Path) -> None:
        tracer = _make_tracer(tmp_path)
        output = tracer.to_mermaid("no-session")
        assert "graph TD" in output
        assert "No invocations recorded" in output

    def test_generates_mermaid_diagram(self, tmp_path: Path) -> None:
        tracer = _seed_chain(tmp_path)
        output = tracer.to_mermaid(SESSION_ID)
        assert "graph TD" in output
        assert "orchestrator" in output
        assert "-->" in output  # at least one edge

    def test_includes_verdict_marks(self, tmp_path: Path) -> None:
        tracer = _make_tracer(tmp_path)
        _start_and_end(tracer, child_skill="passer", verdict="success")
        _start_and_end(tracer, child_skill="failer", verdict="failure")
        output = tracer.to_mermaid(SESSION_ID)
        assert "passer" in output
        assert "failer" in output

    def test_node_ids_are_shortened(self, tmp_path: Path) -> None:
        tracer = _seed_chain(tmp_path)
        output = tracer.to_mermaid(SESSION_ID)
        # Node IDs should be 8-char prefixes, not full 32-char UUIDs
        lines = output.splitlines()
        for line in lines:
            if "[" in line and "]" in line:
                # Extract node_id before the bracket
                node_id = line.strip().split("[")[0].strip()
                if node_id:
                    assert len(node_id) <= 8


# ===========================================================================
# to_ascii_tree
# ===========================================================================


class TestToAsciiTree:
    def test_empty_session(self, tmp_path: Path) -> None:
        tracer = _make_tracer(tmp_path)
        output = tracer.to_ascii_tree("no-session")
        assert output == "(no invocations)"

    def test_generates_ascii_tree(self, tmp_path: Path) -> None:
        tracer = _seed_chain(tmp_path)
        output = tracer.to_ascii_tree(SESSION_ID)
        assert "orchestrator" in output
        assert "implementer" in output
        assert "verifier" in output

    def test_includes_tree_connectors(self, tmp_path: Path) -> None:
        tracer = _seed_chain(tmp_path)
        output = tracer.to_ascii_tree(SESSION_ID)
        # Should contain tree connector characters
        assert any(c in output for c in ["\u2514", "\u251c", "\u2502"])  # └, ├, │

    def test_includes_verdict_marks(self, tmp_path: Path) -> None:
        tracer = _make_tracer(tmp_path)
        call_id = tracer.start_invocation(
            parent_call_id=None, child_skill="winner", session_id=SESSION_ID
        )
        tracer.end_invocation(call_id, verdict="success")
        output = tracer.to_ascii_tree(SESSION_ID)
        assert "winner" in output


# ===========================================================================
# _read_invocations (static)
# ===========================================================================


class TestReadInvocations:
    def test_reads_empty_for_missing_file(self, tmp_path: Path) -> None:
        records = SkillChainTracer._read_invocations("no-sess", tmp_path)
        assert records == []

    def test_round_trip(self, tmp_path: Path) -> None:
        tracer = _seed_chain(tmp_path)
        records = SkillChainTracer._read_invocations(SESSION_ID, tmp_path)
        assert len(records) == 3
        assert all(isinstance(r, SkillInvocation) for r in records)

    def test_skips_malformed_lines(self, tmp_path: Path) -> None:
        chains_dir = tmp_path / ".harness" / "skill-chains"
        chains_dir.mkdir(parents=True, exist_ok=True)
        ndjson_path = chains_dir / f"{SESSION_ID}.ndjson"
        ndjson_path.write_text(
            '{"call_id": "good", "child_skill": "ok", "session_id": "test"}\n'
            'THIS IS NOT JSON\n'
            '{"call_id": "good2", "child_skill": "ok2", "session_id": "test"}\n',
            encoding="utf-8",
        )
        records = SkillChainTracer._read_invocations(SESSION_ID, tmp_path)
        assert len(records) == 2


# ===========================================================================
# Gate hooks
# ===========================================================================


class TestGateHookSkillChainVerification:
    def test_passes_with_no_session_id(self, tmp_path: Path) -> None:
        failures = _gate_hook_skill_chain_verification(
            session=None, project_root=tmp_path
        )
        assert failures == []

    def test_passes_with_empty_session_id_attr(self, tmp_path: Path) -> None:
        class FakeSession:
            session_id = ""
        failures = _gate_hook_skill_chain_verification(
            session=FakeSession(), project_root=tmp_path
        )
        assert failures == []

    def test_passes_on_clean_chain(self, tmp_path: Path) -> None:
        _seed_chain(tmp_path)

        class FakeSession:
            session_id = SESSION_ID
        failures = _gate_hook_skill_chain_verification(
            session=FakeSession(), project_root=tmp_path
        )
        assert failures == []

    def test_fails_on_orphan(self, tmp_path: Path) -> None:
        tracer = _make_tracer(tmp_path)
        inv = SkillInvocation(
            call_id="orphan-hook",
            parent_call_id="missing",
            child_skill="lost",
            session_id=SESSION_ID,
            started_at="2026-06-16T10:00:00+00:00",
            finished_at="2026-06-16T10:00:01+00:00",
        )
        tracer.record_full_invocation(inv)

        class FakeSession:
            session_id = SESSION_ID
        failures = _gate_hook_skill_chain_verification(
            session=FakeSession(), project_root=tmp_path
        )
        assert any("Orphan" in f for f in failures)

    def test_no_records_is_non_blocking(self, tmp_path: Path) -> None:
        """'No records' message should be skipped (non-blocking)."""
        class FakeSession:
            session_id = "empty-sess"
        failures = _gate_hook_skill_chain_verification(
            session=FakeSession(), project_root=tmp_path
        )
        assert failures == []


class TestGateHookSkillChainReview:
    def test_passes_with_no_session_id(self, tmp_path: Path) -> None:
        failures = _gate_hook_skill_chain_review(
            session=None, project_root=tmp_path
        )
        assert failures == []

    def test_fails_when_no_invocations(self, tmp_path: Path) -> None:
        class FakeSession:
            session_id = "empty-review"
        failures = _gate_hook_skill_chain_review(
            session=FakeSession(), project_root=tmp_path
        )
        assert any("No skill invocation records archived" in f for f in failures)

    def test_fails_on_orphans(self, tmp_path: Path) -> None:
        tracer = _make_tracer(tmp_path)
        inv = SkillInvocation(
            call_id="review-orphan",
            parent_call_id="gone",
            child_skill="lost",
            session_id=SESSION_ID,
            started_at="2026-06-16T10:00:00+00:00",
            finished_at="2026-06-16T10:00:01+00:00",
        )
        tracer.record_full_invocation(inv)

        class FakeSession:
            session_id = SESSION_ID
        failures = _gate_hook_skill_chain_review(
            session=FakeSession(), project_root=tmp_path
        )
        assert any("orphan" in f.lower() for f in failures)

    def test_passes_on_clean_chain(self, tmp_path: Path) -> None:
        _seed_chain(tmp_path)

        class FakeSession:
            session_id = SESSION_ID
        failures = _gate_hook_skill_chain_review(
            session=FakeSession(), project_root=tmp_path
        )
        assert failures == []

    def test_fails_on_flat_chain_with_multiple_invocations(self, tmp_path: Path) -> None:
        """Multiple invocations all at depth=0 should be flagged."""
        tracer = _make_tracer(tmp_path)
        _start_and_end(tracer, child_skill="flat-a")
        _start_and_end(tracer, child_skill="flat-b")

        class FakeSession:
            session_id = SESSION_ID
        failures = _gate_hook_skill_chain_review(
            session=FakeSession(), project_root=tmp_path
        )
        assert any("flat" in f.lower() for f in failures)


# ===========================================================================
# _compute_depths (static)
# ===========================================================================


class TestComputeDepths:
    def test_root_has_depth_zero(self) -> None:
        inv = SkillInvocation(call_id="root", parent_call_id=None, child_skill="root")
        by_id = {"root": inv}
        SkillChainTracer._compute_depths(by_id)
        assert inv.trace_depth == 0

    def test_child_has_depth_one(self) -> None:
        root = SkillInvocation(call_id="root", parent_call_id=None, child_skill="root")
        child = SkillInvocation(call_id="child", parent_call_id="root", child_skill="child")
        by_id = {"root": root, "child": child}
        SkillChainTracer._compute_depths(by_id)
        assert child.trace_depth == 1

    def test_grandchild_has_depth_two(self) -> None:
        root = SkillInvocation(call_id="r", parent_call_id=None, child_skill="r")
        child = SkillInvocation(call_id="c", parent_call_id="r", child_skill="c")
        grandchild = SkillInvocation(call_id="gc", parent_call_id="c", child_skill="gc")
        by_id = {"r": root, "c": child, "gc": grandchild}
        SkillChainTracer._compute_depths(by_id)
        assert grandchild.trace_depth == 2

    def test_cycle_protection(self) -> None:
        """A cyclic parent reference should not cause infinite recursion."""
        a = SkillInvocation(call_id="a", parent_call_id="b", child_skill="a")
        b = SkillInvocation(call_id="b", parent_call_id="a", child_skill="b")
        by_id = {"a": a, "b": b}
        # Should not raise
        SkillChainTracer._compute_depths(by_id)
        # Both should have finite depth
        assert a.trace_depth >= 0
        assert b.trace_depth >= 0
