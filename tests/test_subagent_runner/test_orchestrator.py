"""Tests for runner/orchestrator.py — OrchestratorPromptBuilder."""

from __future__ import annotations

from pathlib import Path

import pytest

from harness_governance.runner.orchestrator import OrchestratorPromptBuilder


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """Create a minimal project for orchestrator tests."""
    (tmp_path / "NEXT.md").write_text(
        "[ready] Implement status dashboard\n"
        "- Layer: implementation\n"
        "- Change: dev-workbench\n"
        "Role: Implementer\n"
        "Verification command: npm test\n"
        "Done when: dashboard renders\n"
        "Forbidden shortcut: no mock data\n",
        encoding="utf-8",
    )

    pkt = tmp_path / "docs" / "changes" / "dev-workbench"
    pkt.mkdir(parents=True)
    (pkt / "tasks.md").write_text(
        "# Tasks\n\n"
        "## Owner Files\n\n"
        "src/dashboard.py\n\n"
        "## Expected Behavior\n\n"
        "Shows queue status\n\n"
        "## Done When\n\n"
        "tests pass\n",
        encoding="utf-8",
    )
    (pkt / "contracts.md").write_text(
        "# Contracts\n\n- Must render status\n",
        encoding="utf-8",
    )

    return tmp_path


class TestOrchestratorPromptBuilder:
    def test_build_returns_prompt_text(self, project: Path) -> None:
        builder = OrchestratorPromptBuilder()
        prompt = builder.build(project_root=project)

        assert prompt.text
        assert "Orchestrator" in prompt.text or "orchestrator" in prompt.text.lower()

    def test_build_includes_role_prompt(self, project: Path) -> None:
        builder = OrchestratorPromptBuilder()
        prompt = builder.build(project_root=project)

        # Should include IMPLEMENTER_PROMPT section
        assert "IMPLEMENTER_PROMPT" in prompt.text

    def test_build_detects_role_from_queue(self, project: Path) -> None:
        builder = OrchestratorPromptBuilder()
        prompt = builder.build(project_root=project)

        assert "implementer" in prompt.roles_needed

    def test_build_includes_queue_item(self, project: Path) -> None:
        builder = OrchestratorPromptBuilder()
        prompt = builder.build(project_root=project)

        assert "Implement status dashboard" in prompt.text

    def test_build_includes_execution_params(self, project: Path) -> None:
        builder = OrchestratorPromptBuilder()
        prompt = builder.build(
            project_root=project, mode="boundary", max_rounds=5
        )

        assert "boundary" in prompt.text
        assert "5" in prompt.text

    def test_build_no_ready_raises(self, tmp_path: Path) -> None:
        (tmp_path / "NEXT.md").write_text(
            "[done] Finished task\n- Layer: implementation\n",
            encoding="utf-8",
        )
        builder = OrchestratorPromptBuilder()
        with pytest.raises(ValueError, match="No.*ready.*active"):
            builder.build(project_root=tmp_path)

    def test_build_full_pipeline_when_no_role(self, tmp_path: Path) -> None:
        (tmp_path / "NEXT.md").write_text(
            "[ready] Generic task\n- Layer: implementation\n",
            encoding="utf-8",
        )
        builder = OrchestratorPromptBuilder()
        prompt = builder.build(project_root=tmp_path)

        assert "planner" in prompt.roles_needed
        assert "contract-writer" in prompt.roles_needed
        assert "implementer" in prompt.roles_needed
        assert "reviewer" in prompt.roles_needed

    def test_build_with_checkpoint(self, project: Path) -> None:
        (project / ".harness").mkdir(exist_ok=True)
        (project / ".harness" / "run-checkpoint.md").write_text(
            "# Checkpoint\n\n## Last Worker\n\nround 1\n",
            encoding="utf-8",
        )

        builder = OrchestratorPromptBuilder()
        prompt = builder.build(
            project_root=project,
            checkpoint_file=Path(".harness/run-checkpoint.md"),
        )

        assert "Checkpoint" in prompt.text
        assert "round 1" in prompt.text

    def test_missing_variables_tracked(self, project: Path) -> None:
        builder = OrchestratorPromptBuilder()
        prompt = builder.build(project_root=project)

        # missing_variables is a list (may be empty or populated)
        assert isinstance(prompt.missing_variables, list)


class TestOrchestratorGovernanceRoles:
    """Test governance role detection and layer-to-role inference."""

    def test_detects_adr_writer(self, tmp_path: Path) -> None:
        (tmp_path / "NEXT.md").write_text(
            "[ready] Write ADR for DB migration\n"
            "- Layer: adr\n"
            "Role: ADR Writer\n",
            encoding="utf-8",
        )
        builder = OrchestratorPromptBuilder()
        prompt = builder.build(project_root=tmp_path)
        assert "adr-writer" in prompt.roles_needed
        assert "ADR_WRITER_PROMPT" in prompt.text

    def test_detects_fact_finder_reviewer(self, tmp_path: Path) -> None:
        (tmp_path / "NEXT.md").write_text(
            "[ready] Review architecture facts\n"
            "- Layer: fact-discovery\n"
            "Role: Fact Finder\n",
            encoding="utf-8",
        )
        builder = OrchestratorPromptBuilder()
        prompt = builder.build(project_root=tmp_path)
        assert "fact-finder-reviewer" in prompt.roles_needed
        assert "FACT_FINDER_REVIEWER_PROMPT" in prompt.text

    def test_detects_readiness_gate_writer(self, tmp_path: Path) -> None:
        (tmp_path / "NEXT.md").write_text(
            "[ready] Fix readiness gates\n"
            "- Layer: readiness\n"
            "Role: Readiness Gate Writer\n",
            encoding="utf-8",
        )
        builder = OrchestratorPromptBuilder()
        prompt = builder.build(project_root=tmp_path)
        assert "readiness-gate-writer" in prompt.roles_needed
        assert "READINESS_GATE_WRITER_PROMPT" in prompt.text

    def test_detects_document_gardener(self, tmp_path: Path) -> None:
        (tmp_path / "NEXT.md").write_text(
            "[ready] Fix documentation drift\n"
            "Role: Document Gardener\n",
            encoding="utf-8",
        )
        builder = OrchestratorPromptBuilder()
        prompt = builder.build(project_root=tmp_path)
        assert "document-gardener" in prompt.roles_needed
        assert "DOCUMENT_GARDENER_PROMPT" in prompt.text

    def test_detects_integrator(self, tmp_path: Path) -> None:
        (tmp_path / "NEXT.md").write_text(
            "[ready] Integrate worker outputs\n"
            "Role: Integrator\n",
            encoding="utf-8",
        )
        builder = OrchestratorPromptBuilder()
        prompt = builder.build(project_root=tmp_path)
        assert "integrator" in prompt.roles_needed
        assert "INTEGRATOR_PROMPT" in prompt.text

    def test_layer_adr_infers_adr_writer(self, tmp_path: Path) -> None:
        (tmp_path / "NEXT.md").write_text(
            "[ready] Record architectural decision\n"
            "- Layer: adr\n",
            encoding="utf-8",
        )
        builder = OrchestratorPromptBuilder()
        prompt = builder.build(project_root=tmp_path)
        assert "adr-writer" in prompt.roles_needed

    def test_layer_fact_discovery_infers_fact_finder(self, tmp_path: Path) -> None:
        (tmp_path / "NEXT.md").write_text(
            "[ready] Discover facts\n"
            "- Layer: fact-discovery\n",
            encoding="utf-8",
        )
        builder = OrchestratorPromptBuilder()
        prompt = builder.build(project_root=tmp_path)
        assert "fact-finder-reviewer" in prompt.roles_needed

    def test_layer_readiness_infers_readiness_gate(self, tmp_path: Path) -> None:
        (tmp_path / "NEXT.md").write_text(
            "[ready] Prepare readiness\n"
            "- Layer: readiness\n",
            encoding="utf-8",
        )
        builder = OrchestratorPromptBuilder()
        prompt = builder.build(project_root=tmp_path)
        assert "readiness-gate-writer" in prompt.roles_needed

    def test_hyphenated_role_name(self, tmp_path: Path) -> None:
        (tmp_path / "NEXT.md").write_text(
            "[ready] Write ADR\n"
            "Role: adr-writer\n",
            encoding="utf-8",
        )
        builder = OrchestratorPromptBuilder()
        prompt = builder.build(project_root=tmp_path)
        assert "adr-writer" in prompt.roles_needed


class TestOrchestratorPlatformDispatch:
    """Test platform-specific dispatch and hard-gate substitution."""

    def test_default_is_generic(self, project: Path) -> None:
        builder = OrchestratorPromptBuilder()
        prompt = builder.build(project_root=project)
        assert "native subagent mechanism" in prompt.text
        assert "main session" in prompt.text

    def test_claude_code_dispatch(self, project: Path) -> None:
        builder = OrchestratorPromptBuilder()
        prompt = builder.build(project_root=project, platform="claude-code")
        assert "Agent tool" in prompt.text
        assert "general-purpose" in prompt.text

    def test_codex_dispatch(self, project: Path) -> None:
        builder = OrchestratorPromptBuilder()
        prompt = builder.build(project_root=project, platform="codex")
        assert "NOT an external process" in prompt.text

    def test_cursor_dispatch(self, project: Path) -> None:
        builder = OrchestratorPromptBuilder()
        prompt = builder.build(project_root=project, platform="cursor")
        assert "Cursor" in prompt.text

    def test_qoderwork_dispatch(self, project: Path) -> None:
        builder = OrchestratorPromptBuilder()
        prompt = builder.build(project_root=project, platform="qoderwork")
        assert "Task tool" in prompt.text

    def test_cline_dispatch(self, project: Path) -> None:
        builder = OrchestratorPromptBuilder()
        prompt = builder.build(project_root=project, platform="cline")
        assert "Cline" in prompt.text

    def test_opencode_dispatch(self, project: Path) -> None:
        builder = OrchestratorPromptBuilder()
        prompt = builder.build(project_root=project, platform="opencode")
        assert "OpenCode" in prompt.text

    def test_no_raw_placeholders_remain(self, project: Path) -> None:
        """All {{DISPATCH_INSTRUCTION}} and {{HARD_GATE_COMMAND}} must be resolved."""
        for platform in ("claude-code", "codex", "cline", "cursor", "opencode", "qoderwork", "generic"):
            builder = OrchestratorPromptBuilder()
            prompt = builder.build(project_root=project, platform=platform)
            assert "{{DISPATCH_INSTRUCTION}}" not in prompt.text
            assert "{{HARD_GATE_COMMAND}}" not in prompt.text

    def test_unknown_platform_falls_back_to_generic(self, project: Path) -> None:
        builder = OrchestratorPromptBuilder()
        prompt = builder.build(project_root=project, platform="nonexistent-agent")
        assert "native subagent mechanism" in prompt.text

    def test_none_platform_uses_generic(self, project: Path) -> None:
        builder = OrchestratorPromptBuilder()
        prompt = builder.build(project_root=project, platform=None)
        assert "native subagent mechanism" in prompt.text
