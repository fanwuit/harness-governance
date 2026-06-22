"""Tests for ``harness state-contract`` commands."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from harness_governance.cli import cli


def _write_contract_file(path: Path, terms: tuple[str, ...]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(terms), encoding="utf-8")


def test_state_contract_check_passes_with_required_evidence(tmp_repo: Path) -> None:
    _write_contract_file(
        tmp_repo / "tests" / "test_commands" / "test_layer_cmd.py",
        ("test_answer_records_qa_for_gate", "test_ask_records"),
    )
    _write_contract_file(
        tmp_repo / "tests" / "test_commands" / "test_tech_stack_cmd.py",
        ("test_check_passes_after_cli_lint", "manifest.lint_tools"),
    )
    _write_contract_file(
        tmp_repo / "tests" / "test_e2e" / "test_governed_path_smoke.py",
        ("test_strict_governed_path_minimum_smoke",),
    )
    _write_contract_file(
        tmp_repo / "tests" / "STATE_CONTRACTS.md",
        ("State Contract Closure",),
    )
    _write_contract_file(
        tmp_repo / "tests" / "test_commands" / "test_queue_cmd.py",
        (
            "test_queue_validate_rejects_implementation_without_role_plan",
            "test_queue_validate_rejects_implementation_without_tdd_evidence",
        ),
    )
    _write_contract_file(
        tmp_repo / "tests" / "test_commands" / "test_verify_review_config.py",
        (
            "test_finish_rejects_matching_queue_item_without_role_plan",
            "test_finish_requires_role_plan_and_targeted_evidence",
        ),
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "state-contract", "check"],
    )
    assert result.exit_code == 0, result.output
    assert "state-contract check: passed" in result.output


def test_state_contract_check_fails_when_evidence_missing(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "state-contract", "check"],
    )
    assert result.exit_code == 1
    assert "state-contract check: failed" in result.output
