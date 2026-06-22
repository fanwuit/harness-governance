"""Tests for ``harness queue`` commands."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from harness_governance.cli import cli
from tests.conftest import seed_session


def test_queue_validate_passes_structured_items(tmp_repo: Path) -> None:
    (tmp_repo / "NEXT.md").write_text(
        "[ready] Implement\n"
        "- Id: impl-1\n"
        "- Role: implementer\n"
        "- SessionId: impl-session\n"
        "- Layer: implementation\n"
        "- RolePlan: planner -> contract-test-writer -> implementer -> reviewer-verifier\n"
        "- TestPlan: tests/test_app.py\n"
        "- FailingTestEvidence: pytest tests/test_app.py failed\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli, ["--project-root", str(tmp_repo), "--json", "queue", "validate"]
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["check"] == "queue"


def test_queue_validate_accepts_full_role_taxonomy(tmp_repo: Path) -> None:
    (tmp_repo / "NEXT.md").write_text(
        "[ready] Plan work\n"
        "- Id: plan-1\n"
        "- Role: planner\n"
        "- SessionId: plan-session\n"
        "- Layer: brief\n\n"
        "[ready] Write contract tests\n"
        "- Id: contract-test-1\n"
        "- Role: contract-test-writer\n"
        "- SessionId: contract-test-session\n"
        "- Layer: contract\n\n"
        "[ready] Write ADR\n"
        "- Id: adr-1\n"
        "- Role: architect-adr\n"
        "- SessionId: adr-session\n"
        "- Layer: adr\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli, ["--project-root", str(tmp_repo), "queue", "validate"]
    )

    assert result.exit_code == 0, result.output


def test_queue_validate_accepts_archived_status(tmp_repo: Path) -> None:
    (tmp_repo / "NEXT.md").write_text(
        "[archived] Old work\n"
        "- Id: old-1\n"
        "- Status: archived\n"
        "- Role: planner\n"
        "- SessionId: plan-session\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli, ["--project-root", str(tmp_repo), "queue", "validate"]
    )

    assert result.exit_code == 0, result.output


def test_queue_validate_allows_ready_role_item_without_session(tmp_repo: Path) -> None:
    (tmp_repo / "NEXT.md").write_text(
        "[ready] Implement\n"
        "- Id: impl-1\n"
        "- Role: implementer\n"
        "- RolePlan: planner -> contract-test-writer -> implementer -> reviewer-verifier\n"
        "- TestPlan: tests/test_app.py\n"
        "- FailingTestEvidence: pytest tests/test_app.py failed\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli, ["--project-root", str(tmp_repo), "queue", "validate"]
    )

    assert result.exit_code == 0, result.output


def test_queue_validate_fails_active_role_item_without_session(tmp_repo: Path) -> None:
    (tmp_repo / "NEXT.md").write_text(
        "[active] Implement\n"
        "- Id: impl-1\n"
        "- Role: implementer\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli, ["--project-root", str(tmp_repo), "queue", "validate"]
    )

    assert result.exit_code == 1
    assert "Active/done role queue item must declare sessionId" in result.output


def test_queue_validate_fails_done_role_item_without_session(tmp_repo: Path) -> None:
    (tmp_repo / "NEXT.md").write_text(
        "[done] Implement\n"
        "- Id: impl-1\n"
        "- Role: implementer\n"
        "- Evidence: pytest -q\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli, ["--project-root", str(tmp_repo), "queue", "validate"]
    )

    assert result.exit_code == 1
    assert "Active/done role queue item must declare sessionId" in result.output


def test_check_role_isolation_rejects_same_session_review(tmp_repo: Path) -> None:
    (tmp_repo / "NEXT.md").write_text(
        "[done] Implement\n"
        "- Id: impl-1\n"
        "- Role: implementer\n"
        "- SessionId: shared-session\n\n"
        "[ready] Review\n"
        "- Id: review-1\n"
        "- Role: reviewer-verifier\n"
        "- SessionId: shared-session\n"
        "- DependsOn: impl-1\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli, ["--project-root", str(tmp_repo), "check", "role-isolation"]
    )

    assert result.exit_code == 1
    assert "sessionId must differ" in result.output


def test_check_role_isolation_passes_review_dependency(tmp_repo: Path) -> None:
    (tmp_repo / "NEXT.md").write_text(
        "[done] Implement\n"
        "- Id: impl-1\n"
        "- Role: implementer\n"
        "- SessionId: impl-session\n"
        "- Evidence: pytest -q\n\n"
        "[ready] Review\n"
        "- Id: review-1\n"
        "- Role: reviewer-verifier\n"
        "- SessionId: review-session\n"
        "- DependsOn: impl-1\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli, ["--project-root", str(tmp_repo), "check", "role-isolation"]
    )

    assert result.exit_code == 0, result.output


def test_check_role_isolation_allows_ready_review_without_session(tmp_repo: Path) -> None:
    (tmp_repo / "NEXT.md").write_text(
        "[done] Implement\n"
        "- Id: impl-1\n"
        "- Role: implementer\n"
        "- SessionId: impl-session\n"
        "- Evidence: pytest -q\n\n"
        "[ready] Review\n"
        "- Id: review-1\n"
        "- Role: reviewer-verifier\n"
        "- DependsOn: impl-1\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli, ["--project-root", str(tmp_repo), "check", "role-isolation"]
    )

    assert result.exit_code == 0, result.output


def test_check_role_isolation_rejects_active_review_without_session(
    tmp_repo: Path,
) -> None:
    (tmp_repo / "NEXT.md").write_text(
        "[done] Implement\n"
        "- Id: impl-1\n"
        "- Role: implementer\n"
        "- SessionId: impl-session\n"
        "- Evidence: pytest -q\n\n"
        "[active] Review\n"
        "- Id: review-1\n"
        "- Role: reviewer-verifier\n"
        "- DependsOn: impl-1\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli, ["--project-root", str(tmp_repo), "check", "role-isolation"]
    )

    assert result.exit_code == 1
    assert "must declare its own sessionId" in result.output


def test_check_role_isolation_rejects_done_item_without_evidence(tmp_repo: Path) -> None:
    (tmp_repo / "NEXT.md").write_text(
        "[done] Implement\n"
        "- Id: impl-1\n"
        "- Role: implementer\n"
        "- SessionId: impl-session\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli, ["--project-root", str(tmp_repo), "check", "role-isolation"]
    )

    assert result.exit_code == 1
    assert "must record evidence or verification" in result.output


def test_queue_add_list_next_start_finish_block(tmp_repo: Path) -> None:
    seed_session(tmp_repo, session_id="session-1")
    runner = CliRunner()

    add_result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "queue",
            "add",
            "impl-1",
            "Implement queue suite",
            "--role",
            "implementer",
            "--layer",
            "implementation",
            "--session-id",
            "session-1",
        ],
    )
    assert add_result.exit_code == 0, add_result.output

    block_add = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "queue",
            "add",
            "blocked-1",
            "Blocked queue item",
            "--role",
            "implementer",
            "--layer",
            "implementation",
            "--session-id",
            "session-1",
        ],
    )
    assert block_add.exit_code == 0, block_add.output

    list_result = runner.invoke(
        cli, ["--project-root", str(tmp_repo), "queue", "list"]
    )
    assert list_result.exit_code == 0, list_result.output
    assert "impl-1" in list_result.output

    next_result = runner.invoke(
        cli, ["--project-root", str(tmp_repo), "queue", "next"]
    )
    assert next_result.exit_code == 0, next_result.output
    assert "impl-1" in next_result.output

    start_result = runner.invoke(
        cli, ["--project-root", str(tmp_repo), "queue", "start", "impl-1"]
    )
    assert start_result.exit_code == 0, start_result.output

    finish_result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "queue",
            "finish",
            "impl-1",
            "--evidence",
            "pytest -q",
        ],
    )
    assert finish_result.exit_code == 0, finish_result.output

    block_result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "queue",
            "block",
            "blocked-1",
            "--reason",
            "dependency missing",
        ],
    )
    assert block_result.exit_code == 0, block_result.output

    queue_text = (tmp_repo / "NEXT.md").read_text(encoding="utf-8")
    assert "[done] Implement queue suite" in queue_text
    assert "CompletedAt" in queue_text
    assert "dependency missing" in queue_text


def test_queue_start_rejects_reviewer_with_implementation_session(
    tmp_repo: Path,
) -> None:
    (tmp_repo / "NEXT.md").write_text(
        "[done] Implement\n"
        "- Id: impl-1\n"
        "- Role: implementer\n"
        "- SessionId: impl-session\n"
        "- Evidence: pytest -q\n\n"
        "[ready] Review\n"
        "- Id: review-1\n"
        "- Role: reviewer-verifier\n"
        "- DependsOn: impl-1\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "queue",
            "start",
            "review-1",
            "--session-id",
            "impl-session",
        ],
    )

    assert result.exit_code == 1
    assert "sessionId must differ" in result.output


def test_queue_validate_applies_project_policy(tmp_repo: Path) -> None:
    harness_dir = tmp_repo / ".harness"
    harness_dir.mkdir(parents=True, exist_ok=True)
    (harness_dir / "queue-policy.json").write_text(
        """{
  "role_required_by_layer": {
    "implementation": "implementer"
  },
  "verification_presets": {
    "implementer": "pytest -q"
  }
}""",
        encoding="utf-8",
    )
    (tmp_repo / "NEXT.md").write_text(
        "[ready] Bad implementer item\n"
        "- Id: impl-1\n"
        "- Layer: implementation\n"
        "- Role: reviewer-verifier\n"
        "- Verification: pytest -q\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli, ["--project-root", str(tmp_repo), "queue", "validate"]
    )

    assert result.exit_code == 1
    assert "Queue role must be 'implementer'" in result.output


def test_queue_validate_requires_policy_verification_field(tmp_repo: Path) -> None:
    harness_dir = tmp_repo / ".harness"
    harness_dir.mkdir(parents=True, exist_ok=True)
    (harness_dir / "queue-policy.json").write_text(
        """{
  "verification_presets": {
    "implementer": "pytest -q"
  }
}""",
        encoding="utf-8",
    )
    (tmp_repo / "NEXT.md").write_text(
        "[done] Implementer item\n"
        "- Id: impl-1\n"
        "- Role: implementer\n"
        "- SessionId: session-1\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli, ["--project-root", str(tmp_repo), "queue", "validate"]
    )

    assert result.exit_code == 1
    assert "requires a Verification field" in result.output


def test_queue_validate_applies_child_gate_ordering(tmp_repo: Path) -> None:
    harness_dir = tmp_repo / ".harness"
    harness_dir.mkdir(parents=True, exist_ok=True)
    (harness_dir / "queue-policy.json").write_text(
        """{
  "child_gate_ordering": {
    "implementation": ["verification", "review-next"]
  }
}""",
        encoding="utf-8",
    )
    (tmp_repo / "NEXT.md").write_text(
        "[done] Implement gate\n"
        "- Id: impl-1\n"
        "- GateId: implementation\n"
        "- Role: implementer\n"
        "- SessionId: impl-session\n"
        "- RolePlan: planner -> contract-test-writer -> implementer -> reviewer-verifier\n"
        "- TestPlan: tests/test_app.py\n"
        "- FailingTestEvidence: pytest tests/test_app.py failed\n"
        "- Verification: pytest -q\n\n"
        "[done] Verify gate\n"
        "- Id: verify-1\n"
        "- GateId: verification\n"
        "- Role: reviewer-verifier\n"
        "- SessionId: verify-session\n"
        "- DependsOn: impl-1\n"
        "- Verification: pytest -q\n\n"
        "[ready] Review gate\n"
        "- Id: review-1\n"
        "- GateId: review-next\n"
        "- Role: reviewer-verifier\n"
        "- SessionId: review-session\n"
        "- DependsOn: verify-1\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli, ["--project-root", str(tmp_repo), "queue", "validate"]
    )

    assert result.exit_code == 0, result.output


def test_queue_validate_rejects_forbidden_owner_overlap(tmp_repo: Path) -> None:
    harness_dir = tmp_repo / ".harness"
    harness_dir.mkdir(parents=True, exist_ok=True)
    (harness_dir / "queue-policy.json").write_text(
        """{
  "forbidden_owner_overlap": [
    ["src/app.py", "tests/test_app.py"]
  ]
}""",
        encoding="utf-8",
    )
    (tmp_repo / "NEXT.md").write_text(
        "[ready] Implement overlap\n"
        "- Id: impl-1\n"
        "- Role: implementer\n"
        "- SessionId: session-1\n"
        "- OwnerFiles: src/app.py, tests/test_app.py\n"
        "- Verification: pytest -q\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli, ["--project-root", str(tmp_repo), "queue", "validate"]
    )

    assert result.exit_code == 1
    assert "forbidden overlap policy" in result.output


def test_queue_validate_rejects_implementation_without_role_plan(
    tmp_repo: Path,
) -> None:
    (tmp_repo / "NEXT.md").write_text(
        "[ready] Implement missing role plan\n"
        "- Id: impl-1\n"
        "- Layer: implementation\n"
        "- Role: implementer\n"
        "- TestPlan: tests/test_app.py\n"
        "- FailingTestEvidence: pytest tests/test_app.py failed\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli, ["--project-root", str(tmp_repo), "queue", "validate"]
    )

    assert result.exit_code == 1
    assert "RolePlan" in result.output


def test_queue_validate_rejects_implementation_without_tdd_evidence(
    tmp_repo: Path,
) -> None:
    (tmp_repo / "NEXT.md").write_text(
        "[ready] Implement missing TDD evidence\n"
        "- Id: impl-1\n"
        "- Layer: implementation\n"
        "- Role: implementer\n"
        "- RolePlan: planner -> contract-test-writer -> implementer -> reviewer-verifier\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        cli, ["--project-root", str(tmp_repo), "queue", "validate"]
    )

    assert result.exit_code == 1
    assert "TestPlan" in result.output
    assert "FailingTestEvidence" in result.output
