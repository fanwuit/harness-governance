"""CLI integration tests for the Subagent runner commands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from harness_governance.cli import cli


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """Create a minimal project for CLI tests."""
    (tmp_path / "NEXT.md").write_text(
        "[ready] Implement dashboard\n"
        "- Layer: implementation\n"
        "- Change: my-change\n"
        "Role: Implementer\n"
        "Verification command: npm test\n"
        "Done when: dashboard renders\n"
        "Forbidden shortcut: no mock data\n",
        encoding="utf-8",
    )

    pkt = tmp_path / "docs" / "changes" / "my-change"
    pkt.mkdir(parents=True)
    (pkt / "tasks.md").write_text(
        "# Tasks\n\n"
        "## Owner Files\n\n"
        "src/dashboard.py\n\n"
        "## Expected Behavior\n\n"
        "Shows status\n\n"
        "## Done When\n\n"
        "tests pass\n",
        encoding="utf-8",
    )
    (pkt / "contracts.md").write_text(
        "# Contracts\n\n- Must render\n",
        encoding="utf-8",
    )

    return tmp_path


class TestRunnerStartOrchestrator:
    def test_orchestrator_stdout(self, project: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root", str(project),
                "runner", "start",
                "--executor", "orchestrator",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "IMPLEMENTER_PROMPT" in result.output
        assert "Orchestrator" in result.output or "orchestrator" in result.output

    def test_orchestrator_output_file(self, project: Path) -> None:
        runner = CliRunner()
        output = project / ".harness" / "orchestrator-prompt.md"
        result = runner.invoke(
            cli,
            [
                "--project-root", str(project),
                "runner", "start",
                "--executor", "orchestrator",
                "--output", str(output),
            ],
        )
        assert result.exit_code == 0, result.output
        assert output.is_file()
        content = output.read_text(encoding="utf-8")
        assert "IMPLEMENTER_PROMPT" in content

    def test_orchestrator_no_ready_item(self, tmp_path: Path) -> None:
        (tmp_path / "NEXT.md").write_text(
            "[done] Finished\n- Layer: implementation\n",
            encoding="utf-8",
        )
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "runner", "start",
                "--executor", "orchestrator",
            ],
        )
        assert result.exit_code != 0


class TestRunnerRender:
    def test_render_implementer(self, project: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root", str(project),
                "runner", "render",
                "--role", "implementer",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Implementer" in result.output

    def test_render_reviewer(self, project: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root", str(project),
                "runner", "render",
                "--role", "reviewer",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Reviewer" in result.output
        assert "Forbidden Inputs" in result.output

    def test_render_to_file(self, project: Path) -> None:
        runner = CliRunner()
        output = project / ".harness" / "implementer-prompt.md"
        result = runner.invoke(
            cli,
            [
                "--project-root", str(project),
                "runner", "render",
                "--role", "implementer",
                "--output", str(output),
            ],
        )
        assert result.exit_code == 0, result.output
        assert output.is_file()

    def test_render_no_ready(self, tmp_path: Path) -> None:
        (tmp_path / "NEXT.md").write_text("[done] Task\n", encoding="utf-8")
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root", str(tmp_path),
                "runner", "render",
                "--role", "implementer",
            ],
        )
        assert result.exit_code != 0


class TestRunnerRenderGovernance:
    """Test rendering governance role templates via CLI."""

    @pytest.fixture
    def adr_project(self, tmp_path: Path) -> Path:
        (tmp_path / "NEXT.md").write_text(
            "[ready] Write ADR for DB migration\n"
            "- Layer: adr\n"
            "- Change: adr-db-migration\n"
            "Role: ADR Writer\n"
            "Done when: ADR approved\n",
            encoding="utf-8",
        )
        pkt = tmp_path / "docs" / "changes" / "adr-db-migration"
        pkt.mkdir(parents=True)
        (pkt / "tasks.md").write_text(
            "# Tasks\n\n"
            "## Scope\n\n"
            "Database layer\n\n"
            "## Owner Files\n\n"
            "docs/adr/001-db-migration.md\n",
            encoding="utf-8",
        )
        (pkt / "contracts.md").write_text("# ADR Contracts\n", encoding="utf-8")
        return tmp_path

    def test_render_adr_writer(self, adr_project: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root", str(adr_project),
                "runner", "render",
                "--role", "adr-writer",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "ADR Writer" in result.output
        assert "Database layer" in result.output

    def test_render_fact_finder(self, adr_project: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root", str(adr_project),
                "runner", "render",
                "--role", "fact-finder-reviewer",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Fact Finder" in result.output
        assert "Forbidden Inputs" in result.output

    def test_render_readiness_gate_writer(self, adr_project: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root", str(adr_project),
                "runner", "render",
                "--role", "readiness-gate-writer",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Readiness Gate Writer" in result.output

    def test_render_document_gardener(self, adr_project: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root", str(adr_project),
                "runner", "render",
                "--role", "document-gardener",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Document Gardener" in result.output

    def test_render_integrator(self, adr_project: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root", str(adr_project),
                "runner", "render",
                "--role", "integrator",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "Integrator" in result.output

    def test_orchestrator_with_adr_role(self, adr_project: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root", str(adr_project),
                "runner", "start",
                "--executor", "orchestrator",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "ADR_WRITER_PROMPT" in result.output


class TestRunnerParseResult:
    def test_parse_implementer_result(self, project: Path) -> None:
        input_file = project / "result.json"
        input_file.write_text(json.dumps({
            "role": "implementer",
            "filesChanged": ["src/dashboard.py"],
            "summary": "Done",
            "verificationResults": [
                {"command": "npm test", "status": "passed", "evidence": "ok"},
            ],
            "contractBlocked": False,
            "openRisks": [],
        }), encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root", str(project),
                "runner", "parse-result",
                "--role", "implementer",
                "--input", str(input_file),
            ],
        )
        assert result.exit_code == 0, result.output
        parsed = json.loads(result.output)
        assert parsed["role"] == "implementer"
        assert parsed["verificationPassed"] is True
        assert parsed["isAcceptable"] is True

        # Invocation log should have an entry
        log = project / ".harness" / "invocations.ndjson"
        assert log.is_file()

    def test_parse_reviewer_reject(self, project: Path) -> None:
        input_file = project / "review.json"
        input_file.write_text(json.dumps({
            "role": "reviewer",
            "verdict": "reject",
            "findings": [
                {"severity": "blocking", "description": "Missing test"},
            ],
            "verificationResults": [],
            "residualRisks": [],
        }), encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root", str(project),
                "runner", "parse-result",
                "--role", "reviewer",
                "--input", str(input_file),
            ],
        )
        assert result.exit_code == 0, result.output
        parsed = json.loads(result.output)
        assert parsed["verdict"] == "reject"
        assert parsed["isAcceptable"] is False
        assert parsed["findingsCount"] == 1

    def test_parse_from_stdin(self, project: Path) -> None:
        data = json.dumps({"role": "implementer", "filesChanged": []})
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root", str(project),
                "runner", "parse-result",
                "--role", "implementer",
            ],
            input=data,
        )
        assert result.exit_code == 0, result.output
