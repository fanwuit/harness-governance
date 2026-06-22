"""Tests for ``harness verify``, ``harness review``, and ``harness config``."""

from __future__ import annotations

import sys
from pathlib import Path

from click.testing import CliRunner

from harness_governance.cli import cli
from harness_governance.commands import verify as verify_module
from harness_governance.session import SessionState, create_session, load_session
from harness_governance.state_machine.classification import RoutingPath
from harness_governance.state_machine.layers import HarnessLayer


def _mark_harness_governance_repo(project_root: Path) -> None:
    (project_root / "src" / "harness_governance").mkdir(parents=True)
    (project_root / "pyproject.toml").write_text(
        '[project]\nname = "harness-governance"\n',
        encoding="utf-8",
    )


def _seed_review_session(project_root: Path, session_id: str) -> None:
    create_session(
        project_root,
        SessionState(
            session_id=session_id,
            created_at="2026-06-20T00:00:00+00:00",
            description="Review close test session",
            routing_path=RoutingPath.GOVERNED_PATH,
            current_layer=HarnessLayer.REVIEW_NEXT,
        ),
    )


def test_verify_routing_preset_passes(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "verify", "routing-guardrails"],
    )
    assert result.exit_code == 0, result.output


def test_verify_unknown_preset_fails(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "verify", "no-such-preset"],
    )
    assert result.exit_code != 0
    assert "Unknown preset" in result.output


def test_verify_all_local_checks_passes(tmp_repo: Path) -> None:
    (tmp_repo / "README.md").write_text(
        "# README\n\n| x | x | x | x | 是 | x |\n\n启用的非 system skills：0 个\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "verify", "all-local-checks"],
    )
    assert result.exit_code == 0, result.output


def test_verify_local_release_runs_release_steps(
    tmp_repo: Path,
    monkeypatch,
) -> None:
    _mark_harness_governance_repo(tmp_repo)
    monkeypatch.setattr(
        verify_module,
        "_RELEASE_COMMANDS",
        ((sys.executable, "-c", "print('release step ok')"),),
    )
    monkeypatch.setattr(verify_module, "_verify_wheel_contents", lambda root: True)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "verify", "local", "--release"],
    )
    assert result.exit_code == 0, result.output
    assert "verify local --release: 通过" in result.output or "verify local --release: passed" in result.output


def test_verify_local_release_is_self_repo_only(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "verify", "local", "--release"],
    )
    assert result.exit_code != 0
    assert "only available in the harness-governance source repository" in result.output


def test_verify_local_release_fails_on_step(
    tmp_repo: Path,
    monkeypatch,
) -> None:
    _mark_harness_governance_repo(tmp_repo)
    monkeypatch.setattr(
        verify_module,
        "_RELEASE_COMMANDS",
        ((sys.executable, "-c", "raise SystemExit(3)"),),
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "verify", "local", "--release"],
    )
    assert result.exit_code == 1, result.output
    assert "verify local --release: 失败" in result.output or "verify local --release: failed" in result.output


def test_review_close_writes_checkpoint(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "review",
            "close",
            "task-1",
            "--evidence",
            "pytest -q",
            "--evidence",
            "all checks green",
            "--risk",
            "scope creep",
            "--next-resume",
            "NEXT.md [ready] task-2",
        ],
    )
    assert result.exit_code == 0, result.output
    checkpoint = (tmp_repo / ".harness" / "run-checkpoint.md").read_text(
        encoding="utf-8"
    )
    assert "task-1" in checkpoint
    assert "pytest -q" in checkpoint
    assert "scope creep" in checkpoint


def test_review_close_marks_matching_queue_item_done(tmp_repo: Path) -> None:
    (tmp_repo / "NEXT.md").write_text(
        "[active] Implement queue closure\n"
        "- Session: task-1\n"
        "- Layer: implementation\n"
        "- Verification command: pytest\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "review",
            "close",
            "task-1",
            "--evidence",
            "pytest -q",
            "--risk",
            "none",
        ],
    )
    assert result.exit_code == 0, result.output
    text = (tmp_repo / "NEXT.md").read_text(encoding="utf-8")
    assert "[done] Implement queue closure" in text
    assert "- Closed: task-1" in text
    assert "- Evidence: pytest -q" in text
    assert "- Risk: none" in text


def test_review_close_closes_matching_session_and_queue(tmp_repo: Path) -> None:
    _seed_review_session(tmp_repo, "task-1")
    (tmp_repo / "NEXT.md").write_text(
        "[active] Implement queue closure\n"
        "- Session: task-1\n"
        "- Layer: implementation\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "review",
            "close",
            "task-1",
            "--evidence",
            "pytest -q",
            "--risk",
            "none",
        ],
    )
    assert result.exit_code == 0, result.output

    session = load_session(tmp_repo, "task-1")
    assert session.status == "closed"
    assert session.closed_at is not None

    queue = (tmp_repo / "NEXT.md").read_text(encoding="utf-8")
    assert "[done] Implement queue closure" in queue
    assert "- Closed: task-1" in queue


def test_finish_closes_matching_session_and_queue(tmp_repo: Path) -> None:
    _seed_review_session(tmp_repo, "task-1")
    (tmp_repo / "NEXT.md").write_text(
        "[active] Implement queue closure\n"
        "- Session: task-1\n"
        "- Layer: implementation\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "finish",
            "task-1",
            "--evidence",
            "pytest -q",
            "--risk",
            "none",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Finished: task-1" in result.output

    session = load_session(tmp_repo, "task-1")
    assert session.status == "closed"
    assert session.closed_at is not None

    queue = (tmp_repo / "NEXT.md").read_text(encoding="utf-8")
    assert "[done] Implement queue closure" in queue
    assert "- Status: done" in queue
    assert "- Closed: task-1" in queue
    assert "- CompletedAt:" in queue
    assert "- Evidence: pytest -q" in queue
    assert "- Risk: none" in queue


def test_finish_rejects_closing_review_queue_by_item_id(tmp_repo: Path) -> None:
    (tmp_repo / "NEXT.md").write_text(
        "[active] Review implementation\n"
        "- Id: review-1\n"
        "- Role: reviewer-verifier\n"
        "- SessionId: review-session\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "finish",
            "review-1",
            "--evidence",
            "manual review",
        ],
    )

    assert result.exit_code == 1
    assert "must be finished by their own sessionId" in result.output


def test_finish_prompts_for_review_queue_after_implementation(tmp_repo: Path) -> None:
    _seed_review_session(tmp_repo, "task-1")
    (tmp_repo / "NEXT.md").write_text(
        "[active] Implement queue closure\n"
        "- Id: task-1\n"
        "- Role: implementer\n"
        "- SessionId: task-1\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "finish",
            "task-1",
            "--evidence",
            "pytest -q",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "reviewer-verifier queue item" in result.output


def test_status_warns_active_queue_item_can_be_finished(tmp_repo: Path) -> None:
    (tmp_repo / "NEXT.md").write_text(
        "[active] Finish reminder\n"
        "- Session: task-1\n"
        "- Layer: implementation\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["--project-root", str(tmp_repo), "status"])
    assert result.exit_code == 0, result.output
    assert "harness finish task-1" in result.output


def test_review_close_missing_session_is_non_fatal(tmp_repo: Path) -> None:
    _seed_review_session(tmp_repo, "unrelated-session")
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "review",
            "close",
            "task-1",
            "--evidence",
            "pytest -q",
        ],
    )
    assert result.exit_code == 0, result.output
    assert load_session(tmp_repo, "unrelated-session").status == "active"


def test_config_init_writes_file(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "config", "init"],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_repo / ".harness" / "config.toml").is_file()


def test_config_init_force_overwrites(tmp_repo: Path) -> None:
    runner = CliRunner()
    runner.invoke(cli, ["--project-root", str(tmp_repo), "config", "init"])
    (tmp_repo / ".harness" / "config.toml").write_text("# custom\n", encoding="utf-8")
    runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "config", "init", "--force"],
    )
    text = (tmp_repo / ".harness" / "config.toml").read_text(encoding="utf-8")
    assert "# custom" not in text


def _seed_active_session(tmp_repo: Path, session_id: str, layer: HarnessLayer) -> None:
    create_session(
        tmp_repo,
        SessionState(
            session_id=session_id,
            created_at="2026-06-20T00:00:00+00:00",
            description="Auto-close test session",
            routing_path=RoutingPath.GOVERNED_PATH,
            current_layer=layer,
        ),
    )


def test_auto_close_no_active_tasks(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "review", "auto-close"],
    )
    assert result.exit_code == 0, result.output
    assert "No active tasks found" in result.output


def test_auto_close_no_matching_session(tmp_repo: Path) -> None:
    (tmp_repo / "NEXT.md").write_text(
        "[active] Orphan task\n"
        "- Session: no-such-session\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "review", "auto-close"],
    )
    assert result.exit_code == 0, result.output
    assert "No tasks to auto-close" in result.output


def test_auto_close_session_already_closed(tmp_repo: Path) -> None:
    _seed_active_session(tmp_repo, "task-closed", HarnessLayer.IMPLEMENTATION)
    (tmp_repo / "NEXT.md").write_text(
        "[active] Closed session task\n"
        "- Session: task-closed\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    # Manually close the session first
    runner.invoke(cli, ["--project-root", str(tmp_repo), "review", "close", "task-closed"])
    # Now auto-close should pick it up
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "review", "auto-close"],
    )
    assert result.exit_code == 0, result.output
    assert "[done] Closed session task" in (tmp_repo / "NEXT.md").read_text(encoding="utf-8")


def test_auto_close_review_next_and_clean_tree(tmp_repo: Path, monkeypatch) -> None:
    _seed_active_session(tmp_repo, "task-review", HarnessLayer.REVIEW_NEXT)
    (tmp_repo / "NEXT.md").write_text(
        "[active] REVIEW_NEXT task\n"
        "- Session: task-review\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "harness_governance.commands.review._is_working_tree_clean",
        lambda _: True,
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "review", "auto-close"],
    )
    assert result.exit_code == 0, result.output
    text = (tmp_repo / "NEXT.md").read_text(encoding="utf-8")
    assert "[done] REVIEW_NEXT task" in text


def test_auto_close_dry_run_does_not_modify(tmp_repo: Path, monkeypatch) -> None:
    _seed_active_session(tmp_repo, "task-dry", HarnessLayer.REVIEW_NEXT)
    (tmp_repo / "NEXT.md").write_text(
        "[active] Dry-run task\n"
        "- Session: task-dry\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "harness_governance.commands.review._is_working_tree_clean",
        lambda _: True,
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "review", "auto-close", "--dry-run"],
    )
    assert result.exit_code == 0, result.output
    text = (tmp_repo / "NEXT.md").read_text(encoding="utf-8")
    assert "[active] Dry-run task" in text


def test_auto_close_dirty_tree_skips(tmp_repo: Path, monkeypatch) -> None:
    _seed_active_session(tmp_repo, "task-dirty", HarnessLayer.REVIEW_NEXT)
    (tmp_repo / "NEXT.md").write_text(
        "[active] Dirty tree task\n"
        "- Session: task-dirty\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "harness_governance.commands.review._is_working_tree_clean",
        lambda _: False,
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "review", "auto-close"],
    )
    assert result.exit_code == 0, result.output
    text = (tmp_repo / "NEXT.md").read_text(encoding="utf-8")
    assert "[active] Dirty tree task" in text
