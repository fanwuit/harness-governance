"""Tests for planning carrier helpers."""

from __future__ import annotations

from pathlib import Path

from harness_governance.file_ops.plan import (
    attest_plan,
    init_plan,
    is_plan_complete,
    plan_dir,
    resolve_active_plan,
    set_active_plan,
)


def test_init_plan_creates_three_files(tmp_repo: Path) -> None:
    session = init_plan(tmp_repo, slug="phase-a")
    for filename in ("task_plan.md", "findings.md", "progress.md"):
        assert (session.plan_dir / filename).is_file()
    assert session.plan_id.endswith("phase-a")


def test_init_plan_pins_active(tmp_repo: Path) -> None:
    init_plan(tmp_repo, slug="phase-a")
    active = resolve_active_plan(tmp_repo)
    assert active is not None
    assert active.plan_id.endswith("phase-a")


def test_set_active_plan_switches(tmp_repo: Path) -> None:
    init_plan(tmp_repo, slug="first")
    init_plan(tmp_repo, slug="second")
    set_active_plan(tmp_repo, plan_id=plan_dir(tmp_repo, "first").name or "")
    # resolve_active_plan still picks the pinned one.
    active = resolve_active_plan(tmp_repo)
    assert active is not None


def test_attest_plan_records_sha256(tmp_repo: Path) -> None:
    session = init_plan(tmp_repo, slug="phase-a")
    digest = attest_plan(tmp_repo, session.plan_id)
    assert len(digest) == 64
    session_dir = plan_dir(tmp_repo, session.plan_id)
    assert (session_dir / ".attestation").read_text(encoding="utf-8").strip() == digest


def test_is_plan_complete_false_until_phases_done(tmp_repo: Path) -> None:
    session = init_plan(tmp_repo, slug="phase-a")
    assert not is_plan_complete(tmp_repo, session.plan_id)
    body = (session.task_plan_path).read_text(encoding="utf-8")
    # Inject a completed phase.
    new_body = body + "\n## Phase 1. Demo\n\nStatus: complete\n"
    session.task_plan_path.write_text(new_body, encoding="utf-8")
    # Still incomplete because the original phases remain.
    assert not is_plan_complete(tmp_repo, session.plan_id)


def test_resolve_active_plan_returns_none_when_empty(tmp_repo: Path) -> None:
    assert resolve_active_plan(tmp_repo) is None
