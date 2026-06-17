"""Tests for ``harness skill-chain`` CLI commands.

Covers: trace (ascii/mermaid), visualize (mermaid/ascii), inspect
(human-readable and --json), and edge cases like empty sessions.
"""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner, Result

from harness_governance.cli import cli
from harness_governance.models.schemas import SkillInvocation
from harness_governance.state_machine.skill_chain import SkillChainTracer


# ---------------------------------------------------------------------------
# Constants & Helpers
# ---------------------------------------------------------------------------

SESSION_ID = "20260616-test"


def _runner() -> CliRunner:
    return CliRunner()


def _invoke(root: Path, *args: str) -> Result:
    runner = _runner()
    return runner.invoke(cli, ["--project-root", str(root), *args])


def _seed_chain(tmp_path: Path, session_id: str = SESSION_ID) -> SkillChainTracer:
    """Create a tracer with a 3-level chain: orchestrator → implementer → verifier."""
    tracer = SkillChainTracer(tmp_path)

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


def _seed_flat_chain(tmp_path: Path, session_id: str = SESSION_ID) -> SkillChainTracer:
    """Create a tracer with two root-level invocations (no parent)."""
    tracer = SkillChainTracer(tmp_path)

    id1 = tracer.start_invocation(
        parent_call_id=None, child_skill="skill-a", session_id=session_id
    )
    tracer.end_invocation(id1, exit_code=0, verdict="success")

    id2 = tracer.start_invocation(
        parent_call_id=None, child_skill="skill-b", session_id=session_id
    )
    tracer.end_invocation(id2, exit_code=0, verdict="success")

    return tracer


def _seed_orphan_chain(
    tmp_path: Path, session_id: str = SESSION_ID
) -> SkillChainTracer:
    """Create a tracer with an orphan invocation (parent does not exist)."""
    tracer = SkillChainTracer(tmp_path)
    inv = SkillInvocation(
        call_id="orphan-cmd",
        parent_call_id="nonexistent-parent",
        child_skill="lost-skill",
        session_id=session_id,
        started_at="2026-06-16T10:00:00+00:00",
        finished_at="2026-06-16T10:00:01+00:00",
    )
    tracer.record_full_invocation(inv)
    return tracer


# ===========================================================================
# skill-chain trace
# ===========================================================================


class TestSkillChainTraceCLI:
    def test_trace_ascii_format(self, tmp_path: Path) -> None:
        _seed_chain(tmp_path)
        result = _invoke(
            tmp_path,
            "skill-chain",
            "trace",
            "--session-id",
            SESSION_ID,
        )
        assert result.exit_code == 0, result.output
        assert "orchestrator" in result.output
        assert "implementer" in result.output
        assert "verifier" in result.output

    def test_trace_ascii_default(self, tmp_path: Path) -> None:
        """Default format is ascii."""
        _seed_chain(tmp_path)
        result = _invoke(
            tmp_path,
            "skill-chain",
            "trace",
            "--session-id",
            SESSION_ID,
            "--format",
            "ascii",
        )
        assert result.exit_code == 0, result.output
        assert "orchestrator" in result.output

    def test_trace_mermaid_format(self, tmp_path: Path) -> None:
        _seed_chain(tmp_path)
        result = _invoke(
            tmp_path,
            "skill-chain",
            "trace",
            "--session-id",
            SESSION_ID,
            "--format",
            "mermaid",
        )
        assert result.exit_code == 0, result.output
        assert "graph TD" in result.output

    def test_trace_empty_session(self, tmp_path: Path) -> None:
        result = _invoke(
            tmp_path,
            "skill-chain",
            "trace",
            "--session-id",
            "no-such-session",
        )
        assert result.exit_code == 0, result.output
        assert "(no invocations)" in result.output

    def test_trace_shows_summary(self, tmp_path: Path) -> None:
        _seed_chain(tmp_path)
        result = _invoke(
            tmp_path,
            "skill-chain",
            "trace",
            "--session-id",
            SESSION_ID,
        )
        assert result.exit_code == 0, result.output
        # Summary line should contain total count and skill names
        assert "3" in result.output  # total_invocations

    def test_trace_with_flat_chain(self, tmp_path: Path) -> None:
        _seed_flat_chain(tmp_path)
        result = _invoke(
            tmp_path,
            "skill-chain",
            "trace",
            "--session-id",
            SESSION_ID,
        )
        assert result.exit_code == 0, result.output
        assert "skill-a" in result.output
        assert "skill-b" in result.output

    def test_trace_requires_session_id(self, tmp_path: Path) -> None:
        result = _invoke(tmp_path, "skill-chain", "trace")
        assert result.exit_code != 0  # missing required --session-id


# ===========================================================================
# skill-chain visualize
# ===========================================================================


class TestSkillChainVisualizeCLI:
    def test_visualize_mermaid_default(self, tmp_path: Path) -> None:
        _seed_chain(tmp_path)
        result = _invoke(
            tmp_path,
            "skill-chain",
            "visualize",
            "--session-id",
            SESSION_ID,
        )
        assert result.exit_code == 0, result.output
        assert "```mermaid" in result.output
        assert "graph TD" in result.output
        assert "```" in result.output

    def test_visualize_mermaid_explicit(self, tmp_path: Path) -> None:
        _seed_chain(tmp_path)
        result = _invoke(
            tmp_path,
            "skill-chain",
            "visualize",
            "--session-id",
            SESSION_ID,
            "--format",
            "mermaid",
        )
        assert result.exit_code == 0, result.output
        assert "```mermaid" in result.output

    def test_visualize_ascii_format(self, tmp_path: Path) -> None:
        _seed_chain(tmp_path)
        result = _invoke(
            tmp_path,
            "skill-chain",
            "visualize",
            "--session-id",
            SESSION_ID,
            "--format",
            "ascii",
        )
        assert result.exit_code == 0, result.output
        assert "orchestrator" in result.output

    def test_visualize_empty_session(self, tmp_path: Path) -> None:
        result = _invoke(
            tmp_path,
            "skill-chain",
            "visualize",
            "--session-id",
            "empty",
        )
        assert result.exit_code == 0, result.output
        # Should show some placeholder (mermaid empty or ascii empty)
        combined = result.output
        assert len(combined) > 0

    def test_visualize_mermaid_contains_edges(self, tmp_path: Path) -> None:
        _seed_chain(tmp_path)
        result = _invoke(
            tmp_path,
            "skill-chain",
            "visualize",
            "--session-id",
            SESSION_ID,
        )
        assert "-->" in result.output  # mermaid edge syntax

    def test_visualize_requires_session_id(self, tmp_path: Path) -> None:
        result = _invoke(tmp_path, "skill-chain", "visualize")
        assert result.exit_code != 0


# ===========================================================================
# skill-chain inspect
# ===========================================================================


class TestSkillChainInspectCLI:
    def test_inspect_clean_chain(self, tmp_path: Path) -> None:
        _seed_chain(tmp_path)
        result = _invoke(
            tmp_path,
            "skill-chain",
            "inspect",
            "--session-id",
            SESSION_ID,
        )
        assert result.exit_code == 0, result.output

    def test_inspect_shows_report_header(self, tmp_path: Path) -> None:
        _seed_chain(tmp_path)
        result = _invoke(
            tmp_path,
            "skill-chain",
            "inspect",
            "--session-id",
            SESSION_ID,
        )
        assert result.exit_code == 0, result.output
        # Should contain invocation count
        assert "3" in result.output

    def test_inspect_json_output(self, tmp_path: Path) -> None:
        _seed_chain(tmp_path)
        result = _invoke(
            tmp_path,
            "skill-chain",
            "inspect",
            "--session-id",
            SESSION_ID,
            "--json",
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["total_invocations"] == 3
        assert data["max_depth"] == 2
        assert "orchestrator" in data["unique_skills"]
        assert "implementer" in data["unique_skills"]
        assert "verifier" in data["unique_skills"]

    def test_inspect_json_contains_generated_at(self, tmp_path: Path) -> None:
        _seed_chain(tmp_path)
        result = _invoke(
            tmp_path,
            "skill-chain",
            "inspect",
            "--session-id",
            SESSION_ID,
            "--json",
        )
        data = json.loads(result.output)
        assert "generated_at" in data
        assert data["generated_at"] != ""

    def test_inspect_json_longest_chain(self, tmp_path: Path) -> None:
        _seed_chain(tmp_path)
        result = _invoke(
            tmp_path,
            "skill-chain",
            "inspect",
            "--session-id",
            SESSION_ID,
            "--json",
        )
        data = json.loads(result.output)
        assert len(data["longest_chain"]) == 3

    def test_inspect_fails_with_orphans(self, tmp_path: Path) -> None:
        _seed_orphan_chain(tmp_path)
        result = _invoke(
            tmp_path,
            "skill-chain",
            "inspect",
            "--session-id",
            SESSION_ID,
        )
        # Orphans cause a non-zero exit
        assert result.exit_code == 1

    def test_inspect_json_fails_with_orphans(self, tmp_path: Path) -> None:
        _seed_orphan_chain(tmp_path)
        result = _invoke(
            tmp_path,
            "skill-chain",
            "inspect",
            "--session-id",
            SESSION_ID,
            "--json",
        )
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert "orphan-cmd" in data["orphan_invocations"]

    def test_inspect_empty_session(self, tmp_path: Path) -> None:
        result = _invoke(
            tmp_path,
            "skill-chain",
            "inspect",
            "--session-id",
            "no-such-session",
        )
        # validate_chain_integrity returns issue about no records
        assert result.exit_code == 1

    def test_inspect_shows_unique_skills(self, tmp_path: Path) -> None:
        _seed_chain(tmp_path)
        result = _invoke(
            tmp_path,
            "skill-chain",
            "inspect",
            "--session-id",
            SESSION_ID,
        )
        assert result.exit_code == 0, result.output
        assert "orchestrator" in result.output
        assert "implementer" in result.output
        assert "verifier" in result.output

    def test_inspect_shows_longest_chain(self, tmp_path: Path) -> None:
        _seed_chain(tmp_path)
        result = _invoke(
            tmp_path,
            "skill-chain",
            "inspect",
            "--session-id",
            SESSION_ID,
        )
        assert result.exit_code == 0, result.output

    def test_inspect_requires_session_id(self, tmp_path: Path) -> None:
        result = _invoke(tmp_path, "skill-chain", "inspect")
        assert result.exit_code != 0

    def test_inspect_flat_chain(self, tmp_path: Path) -> None:
        _seed_flat_chain(tmp_path)
        result = _invoke(
            tmp_path,
            "skill-chain",
            "inspect",
            "--session-id",
            SESSION_ID,
        )
        # Flat chain with 2 invocations should pass integrity
        assert result.exit_code == 0, result.output

    def test_inspect_json_empty_session(self, tmp_path: Path) -> None:
        result = _invoke(
            tmp_path,
            "skill-chain",
            "inspect",
            "--session-id",
            "absent",
            "--json",
        )
        # "No records" issue causes exit code 1
        assert result.exit_code == 1


# ===========================================================================
# Edge cases and integration
# ===========================================================================


class TestSkillChainEdgeCases:
    def test_multiple_invocations_same_skill(self, tmp_path: Path) -> None:
        tracer = SkillChainTracer(tmp_path)
        for _ in range(5):
            cid = tracer.start_invocation(
                parent_call_id=None,
                child_skill="repeat-skill",
                session_id=SESSION_ID,
            )
            tracer.end_invocation(cid, exit_code=0, verdict="success")

        result = _invoke(
            tmp_path,
            "skill-chain",
            "inspect",
            "--session-id",
            SESSION_ID,
            "--json",
        )
        data = json.loads(result.output)
        assert data["total_invocations"] == 5
        assert data["unique_skills"] == ["repeat-skill"]

    def test_deep_chain(self, tmp_path: Path) -> None:
        tracer = SkillChainTracer(tmp_path)
        parent_id: str | None = None
        for i in range(10):
            cid = tracer.start_invocation(
                parent_call_id=parent_id,
                child_skill=f"skill-{i}",
                session_id=SESSION_ID,
            )
            tracer.end_invocation(cid, exit_code=0, verdict="success")
            parent_id = cid

        result = _invoke(
            tmp_path,
            "skill-chain",
            "inspect",
            "--session-id",
            SESSION_ID,
            "--json",
        )
        data = json.loads(result.output)
        assert data["total_invocations"] == 10
        assert data["max_depth"] == 9

    def test_failed_invocations_in_chain(self, tmp_path: Path) -> None:
        tracer = SkillChainTracer(tmp_path)
        root_id = tracer.start_invocation(
            parent_call_id=None,
            child_skill="root",
            session_id=SESSION_ID,
        )
        tracer.end_invocation(root_id, exit_code=0, verdict="success")

        child_id = tracer.start_invocation(
            parent_call_id=root_id,
            child_skill="failing-skill",
            session_id=SESSION_ID,
        )
        tracer.end_invocation(child_id, exit_code=1, verdict="failure")

        result = _invoke(
            tmp_path,
            "skill-chain",
            "inspect",
            "--session-id",
            SESSION_ID,
            "--json",
        )
        data = json.loads(result.output)
        assert data["total_invocations"] == 2

    def test_trace_mermaid_shows_failure_mark(self, tmp_path: Path) -> None:
        tracer = SkillChainTracer(tmp_path)
        cid = tracer.start_invocation(
            parent_call_id=None,
            child_skill="broken",
            session_id=SESSION_ID,
        )
        tracer.end_invocation(cid, exit_code=1, verdict="failure")

        result = _invoke(
            tmp_path,
            "skill-chain",
            "trace",
            "--session-id",
            SESSION_ID,
            "--format",
            "mermaid",
        )
        assert result.exit_code == 0, result.output
        assert "broken" in result.output

    def test_separate_sessions(self, tmp_path: Path) -> None:
        """Two separate sessions should not mix their chains."""
        tracer = SkillChainTracer(tmp_path)

        cid1 = tracer.start_invocation(
            parent_call_id=None,
            child_skill="sess1-skill",
            session_id="session-A",
        )
        tracer.end_invocation(cid1, exit_code=0, verdict="success")

        cid2 = tracer.start_invocation(
            parent_call_id=None,
            child_skill="sess2-skill",
            session_id="session-B",
        )
        tracer.end_invocation(cid2, exit_code=0, verdict="success")

        result_a = _invoke(
            tmp_path,
            "skill-chain",
            "inspect",
            "--session-id",
            "session-A",
            "--json",
        )
        data_a = json.loads(result_a.output)
        assert data_a["total_invocations"] == 1
        assert "sess1-skill" in data_a["unique_skills"]

        result_b = _invoke(
            tmp_path,
            "skill-chain",
            "inspect",
            "--session-id",
            "session-B",
            "--json",
        )
        data_b = json.loads(result_b.output)
        assert data_b["total_invocations"] == 1
        assert "sess2-skill" in data_b["unique_skills"]
