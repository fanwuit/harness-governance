"""Tests for ``harness alignment`` CLI commands.

Covers ``alignment check`` (with and without --json, --contract flag),
``alignment trace`` (with --session-id), and the global --project-root
option.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

from click.testing import CliRunner

from harness_governance.cli import cli
from tests.conftest import write_permissive_config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


SIMPLE_TABLE_MD = textwrap.dedent("""\
    # User API Contract

    | Field | Type | Required |
    |-------|------|----------|
    | user_id | UUID | yes |
    | name | str | yes |
    | email | str | yes |
    | age | int | no |
""")

JSON_SCHEMA_MD = textwrap.dedent("""\
    # Order API

    ```json
    {
      "type": "object",
      "properties": {
        "order_id": {"type": "string"},
        "quantity": {"type": "integer"}
      },
      "required": ["order_id", "quantity"]
    }
    ```
""")

MATCHING_IMPL = """\
class User:
    user_id: str
    name: str
    email: str
    age: int
"""

MISSING_FIELD_IMPL = """\
class User:
    user_id: str
    name: str
    # email is missing
    age: int
"""

ORDER_IMPL = """\
class Order:
    order_id: str
    quantity: int
"""


def _setup_project(tmp_path: Path, *, contract: str = "", impl: str = "") -> None:
    """Create a minimal project layout under *tmp_path*."""
    write_permissive_config(tmp_path)

    if contract:
        d = tmp_path / "docs" / "contracts"
        d.mkdir(parents=True, exist_ok=True)
        (d / "api.md").write_text(contract, encoding="utf-8")

    if impl:
        s = tmp_path / "src" / "models"
        s.mkdir(parents=True, exist_ok=True)
        (s / "model.py").write_text(impl, encoding="utf-8")


def _setup_multi_contract_project(tmp_path: Path) -> None:
    """Create a project with two contracts and matching implementations."""
    write_permissive_config(tmp_path)

    contracts = tmp_path / "docs" / "contracts"
    contracts.mkdir(parents=True, exist_ok=True)
    (contracts / "user.md").write_text(SIMPLE_TABLE_MD, encoding="utf-8")
    (contracts / "order.md").write_text(JSON_SCHEMA_MD, encoding="utf-8")

    src = tmp_path / "src" / "models"
    src.mkdir(parents=True, exist_ok=True)
    (src / "user.py").write_text(MATCHING_IMPL, encoding="utf-8")
    (src / "order.py").write_text(ORDER_IMPL, encoding="utf-8")


# ===================================================================
# alignment check
# ===================================================================


class TestAlignmentCheck:
    def test_check_no_contracts_passes(self, tmp_path: Path) -> None:
        """With no contracts directory, alignment should pass."""
        _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "alignment", "check"],
        )
        assert result.exit_code == 0, result.output

    def test_check_passing_alignment_text(self, tmp_path: Path) -> None:
        _setup_project(tmp_path, contract=SIMPLE_TABLE_MD, impl=MATCHING_IMPL)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "alignment", "check"],
        )
        assert result.exit_code == 0, result.output
        # Should show summary line
        assert "expected" in result.output.lower() or "预期" in result.output

    def test_check_failing_alignment_exit_1(self, tmp_path: Path) -> None:
        _setup_project(tmp_path, contract=SIMPLE_TABLE_MD, impl=MISSING_FIELD_IMPL)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "alignment", "check"],
        )
        assert result.exit_code == 1, result.output
        # Should show error findings
        assert "missing" in result.output.lower() or "✗" in result.output

    def test_check_json_output(self, tmp_path: Path) -> None:
        _setup_project(tmp_path, contract=SIMPLE_TABLE_MD, impl=MATCHING_IMPL)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "alignment", "check", "--json"],
        )
        # Parse JSON from output (may contain trailing newline)
        output = result.output.strip()
        data = json.loads(output)
        assert "fields_expected" in data
        assert "fields_matched" in data
        assert "passed" in data
        assert "findings" in data
        assert "generated_at" in data

    def test_check_json_passing_exit_0(self, tmp_path: Path) -> None:
        _setup_project(tmp_path, contract=SIMPLE_TABLE_MD, impl=MATCHING_IMPL)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "alignment", "check", "--json"],
        )
        data = json.loads(result.output.strip())
        assert data["passed"] is True
        assert result.exit_code == 0

    def test_check_json_failing_exit_1(self, tmp_path: Path) -> None:
        _setup_project(tmp_path, contract=SIMPLE_TABLE_MD, impl=MISSING_FIELD_IMPL)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "alignment", "check", "--json"],
        )
        data = json.loads(result.output.strip())
        assert data["passed"] is False
        assert result.exit_code == 1

    def test_check_json_findings_have_issue_field(self, tmp_path: Path) -> None:
        _setup_project(tmp_path, contract=SIMPLE_TABLE_MD, impl=MISSING_FIELD_IMPL)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "alignment", "check", "--json"],
        )
        data = json.loads(result.output.strip())
        errors = [f for f in data["findings"] if f["severity"] == "error"]
        assert len(errors) > 0
        assert all("issue" in f for f in errors)

    def test_check_with_contract_flag(self, tmp_path: Path) -> None:
        """The --contract flag is accepted by the CLI (exists=True validation)."""
        _setup_project(tmp_path, contract=SIMPLE_TABLE_MD, impl=MATCHING_IMPL)
        contract_path = tmp_path / "docs" / "contracts" / "api.md"
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root",
                str(tmp_path),
                "alignment",
                "check",
                "--contract",
                str(contract_path),
            ],
        )
        # The command should run without error (flag is accepted)
        assert result.exit_code in (0, 1), result.output

    def test_check_with_nonexistent_contract_flag(self, tmp_path: Path) -> None:
        """--contract with a nonexistent path should fail (exists=True)."""
        _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root",
                str(tmp_path),
                "alignment",
                "check",
                "--contract",
                str(tmp_path / "no_such_file.md"),
            ],
        )
        assert result.exit_code != 0

    def test_check_text_shows_findings(self, tmp_path: Path) -> None:
        """Text output should list individual findings."""
        _setup_project(tmp_path, contract=SIMPLE_TABLE_MD, impl=MISSING_FIELD_IMPL)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "alignment", "check"],
        )
        # Should show at least one finding line with [missing]
        assert "[missing]" in result.output

    def test_check_text_shows_passed_message(self, tmp_path: Path) -> None:
        """When all fields match, the text output should indicate success."""
        _setup_project(tmp_path, contract=SIMPLE_TABLE_MD, impl=MATCHING_IMPL)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "alignment", "check"],
        )
        assert result.exit_code == 0
        # Should contain passed or no-findings message
        assert (
            "passed" in result.output.lower()
            or "no alignment findings" in result.output.lower()
            or "通过" in result.output
            or "未发现" in result.output
        )

    def test_check_unsupported_languages_message(self, tmp_path: Path) -> None:
        """When non-Python source files exist, output should mention unsupported languages."""
        _setup_project(tmp_path, contract=SIMPLE_TABLE_MD)
        ts_file = tmp_path / "src" / "app.ts"
        ts_file.parent.mkdir(parents=True, exist_ok=True)
        ts_file.write_text("export const x = 1;", encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "alignment", "check"],
        )
        # Should mention unsupported languages or TypeScript
        assert (
            "unsupported" in result.output.lower()
            or "typescript" in result.output.lower()
            or "TypeScript" in result.output
        )


# ===================================================================
# alignment check — project-root behavior
# ===================================================================


class TestAlignmentCheckProjectRoot:
    def test_project_root_is_respected(self, tmp_path: Path) -> None:
        """--project-root should change where the engine looks for contracts."""
        _setup_project(tmp_path, contract=SIMPLE_TABLE_MD, impl=MATCHING_IMPL)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "alignment", "check"],
        )
        assert result.exit_code == 0, result.output
        assert "4" in result.output  # 4 fields expected

    def test_empty_project_root_passes(self, tmp_path: Path) -> None:
        """An empty project (no contracts) should pass."""
        write_permissive_config(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "alignment", "check"],
        )
        assert result.exit_code == 0


# ===================================================================
# alignment trace
# ===================================================================


class TestAlignmentTrace:
    def test_trace_empty_project(self, tmp_path: Path) -> None:
        _setup_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "alignment", "trace"],
        )
        assert result.exit_code == 0, result.output
        assert "0" in result.output  # 0 fields

    def test_trace_with_fields(self, tmp_path: Path) -> None:
        _setup_project(tmp_path, contract=SIMPLE_TABLE_MD, impl=MATCHING_IMPL)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "alignment", "trace"],
        )
        assert result.exit_code == 0, result.output
        # Should show field names
        assert "user_id" in result.output
        assert "name" in result.output

    def test_trace_shows_contract_ref(self, tmp_path: Path) -> None:
        _setup_project(tmp_path, contract=SIMPLE_TABLE_MD, impl=MATCHING_IMPL)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "alignment", "trace"],
        )
        assert (
            "contract:" in result.output.lower() or "contract" in result.output.lower()
        )

    def test_trace_shows_implementation_ref(self, tmp_path: Path) -> None:
        _setup_project(tmp_path, contract=SIMPLE_TABLE_MD, impl=MATCHING_IMPL)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "alignment", "trace"],
        )
        assert (
            "implementation:" in result.output.lower()
            or "implementation" in result.output.lower()
        )

    def test_trace_with_session_id(self, tmp_path: Path) -> None:
        _setup_project(tmp_path, contract=SIMPLE_TABLE_MD, impl=MATCHING_IMPL)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root",
                str(tmp_path),
                "alignment",
                "trace",
                "--session-id",
                "test-sess-001",
            ],
        )
        assert result.exit_code == 0, result.output

    def test_trace_without_session_id(self, tmp_path: Path) -> None:
        """--session-id is optional; omitting it should still work."""
        _setup_project(tmp_path, contract=SIMPLE_TABLE_MD, impl=MATCHING_IMPL)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "alignment", "trace"],
        )
        assert result.exit_code == 0, result.output

    def test_trace_summary_line(self, tmp_path: Path) -> None:
        _setup_project(tmp_path, contract=SIMPLE_TABLE_MD, impl=MATCHING_IMPL)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "alignment", "trace"],
        )
        # Should contain a summary line with total and traced counts
        assert "traceability" in result.output.lower() or "追溯" in result.output

    def test_trace_verification_ref(self, tmp_path: Path) -> None:
        """When test files reference fields, verification ref should appear."""
        _setup_project(tmp_path, contract=SIMPLE_TABLE_MD, impl=MATCHING_IMPL)
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir(parents=True, exist_ok=True)
        (tests_dir / "test_user.py").write_text(
            "# test that user_id and name work correctly\n", encoding="utf-8"
        )

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "alignment", "trace"],
        )
        assert result.exit_code == 0
        assert (
            "verification:" in result.output.lower()
            or "verification" in result.output.lower()
        )


# ===================================================================
# alignment trace — project-root behavior
# ===================================================================


class TestAlignmentTraceProjectRoot:
    def test_project_root_is_respected(self, tmp_path: Path) -> None:
        _setup_multi_contract_project(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "alignment", "trace"],
        )
        assert result.exit_code == 0
        # Both user and order fields should appear
        assert "user_id" in result.output
        assert "order_id" in result.output

    def test_different_project_roots_give_different_results(
        self, tmp_path: Path
    ) -> None:
        """Two different project roots should produce different output."""
        project_a = tmp_path / "project_a"
        project_a.mkdir()
        _setup_project(project_a, contract=SIMPLE_TABLE_MD, impl=MATCHING_IMPL)

        project_b = tmp_path / "project_b"
        project_b.mkdir()
        write_permissive_config(project_b)

        runner = CliRunner()
        result_a = runner.invoke(
            cli,
            ["--project-root", str(project_a), "alignment", "trace"],
        )
        result_b = runner.invoke(
            cli,
            ["--project-root", str(project_b), "alignment", "trace"],
        )
        assert "user_id" in result_a.output
        assert "user_id" not in result_b.output


# ===================================================================
# alignment group help
# ===================================================================


class TestAlignmentGroupHelp:
    def test_alignment_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["alignment", "--help"])
        assert result.exit_code == 0
        assert "check" in result.output
        assert "trace" in result.output

    def test_alignment_check_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["alignment", "check", "--help"])
        assert result.exit_code == 0
        assert "--json" in result.output
        assert "--contract" in result.output

    def test_alignment_trace_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["alignment", "trace", "--help"])
        assert result.exit_code == 0
        assert "--session-id" in result.output


# ===================================================================
# Edge cases
# ===================================================================


class TestAlignmentEdgeCases:
    def test_check_contract_with_no_fields(self, tmp_path: Path) -> None:
        """A contract file without parseable fields should still run."""
        write_permissive_config(tmp_path)
        d = tmp_path / "docs" / "contracts"
        d.mkdir(parents=True, exist_ok=True)
        (d / "empty.md").write_text("# No fields here\nJust text.\n", encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "alignment", "check"],
        )
        # Should pass — no fields to check
        assert result.exit_code == 0

    def test_check_source_with_syntax_error(self, tmp_path: Path) -> None:
        """A Python file with syntax errors should not crash the command."""
        write_permissive_config(tmp_path)
        d = tmp_path / "docs" / "contracts"
        d.mkdir(parents=True, exist_ok=True)
        (d / "api.md").write_text(SIMPLE_TABLE_MD, encoding="utf-8")

        s = tmp_path / "src"
        s.mkdir(parents=True, exist_ok=True)
        (s / "broken.py").write_text("def broken(:\n  pass\n", encoding="utf-8")

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "alignment", "check"],
        )
        # Should not crash — exit 1 because fields are missing is fine
        assert result.exit_code in (0, 1)

    def test_check_multiple_findings_all_listed(self, tmp_path: Path) -> None:
        """All findings should be listed in text output."""
        _setup_project(
            tmp_path, contract=SIMPLE_TABLE_MD, impl="class Empty:\n    pass\n"
        )
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "alignment", "check"],
        )
        # All 4 contract fields should be reported as missing
        assert result.exit_code == 1
        assert "[missing]" in result.output

    def test_json_output_is_valid_json(self, tmp_path: Path) -> None:
        """The --json flag must produce parseable JSON."""
        _setup_project(tmp_path, contract=SIMPLE_TABLE_MD, impl=MATCHING_IMPL)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "alignment", "check", "--json"],
        )
        # Must be valid JSON
        data = json.loads(result.output.strip())
        assert isinstance(data, dict)

    def test_json_output_schema_matches_pydantic_model(self, tmp_path: Path) -> None:
        """JSON output should match the AlignmentReport schema."""
        _setup_project(tmp_path, contract=SIMPLE_TABLE_MD, impl=MATCHING_IMPL)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "alignment", "check", "--json"],
        )
        data = json.loads(result.output.strip())
        expected_keys = {
            "fields_expected",
            "fields_matched",
            "findings",
            "passed",
            "unsupported_languages",
            "generated_at",
        }
        assert set(data.keys()) == expected_keys
