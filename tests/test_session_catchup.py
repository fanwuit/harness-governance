"""Tests for the session-catchup plugin."""

from __future__ import annotations

import json
from pathlib import Path

from harness_governance.plugins.session_catchup import CatchupReport, catchup


def test_catchup_returns_empty_when_no_planning_files(tmp_path: Path) -> None:
    report = catchup(str(tmp_path))
    assert report.runtime == "none"
    assert report.previous_session is None


def test_catchup_finds_claude_session(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "task_plan.md").write_text("# Plan\n", encoding="utf-8")
    project_dir = tmp_path / "fake_claude_project"
    project_dir.mkdir()
    session = project_dir / "session-1.jsonl"
    session.write_text(
        json.dumps(
            {
                "type": "user",
                "message": {"content": "begin work on the new feature for the demo"},
                "_line_num": 0,
            }
        )
        + "\n"
        + json.dumps(
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Edit",
                            "input": {"file_path": str(tmp_path / "task_plan.md")},
                        }
                    ]
                },
                "_line_num": 1,
            }
        )
        + "\n"
        + json.dumps(
            {
                "type": "user",
                "message": {"content": "follow-up: please continue the work above and ship the patch"},
                "_line_num": 2,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    # Make session big enough to be substantial.
    session.write_bytes(session.read_bytes() + b" " * (8192 - session.stat().st_size))

    # Patch the Claude project dir to point at our fake dir by monkeypatching
    # ``_normalize_path`` resolution via env HOME.
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    claude_root = fake_home / ".claude" / "projects" / "fake"
    claude_root.mkdir(parents=True)
    session.rename(claude_root / "session-1.jsonl")

    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setattr("harness_governance.plugins.session_catchup._claude_project_dir", lambda path: claude_root)

    report = catchup(str(tmp_path))
    assert report.runtime == "claude"
    assert report.previous_session is not None
    assert report.last_planning_update_file == "task_plan.md"
    assert report.unsynced_message_count >= 1


def test_catchup_report_to_markdown_includes_recommendations() -> None:
    report = CatchupReport(
        runtime="claude",
        previous_session=Path("/tmp/session.jsonl"),
        last_planning_update_file="task_plan.md",
        last_planning_update_line=5,
        unsynced_message_count=2,
        unsynced_preview=["USER: do thing"],
    )
    md = report.to_markdown()
    assert "SESSION CATCHUP DETECTED" in md
    assert "RECOMMENDED" in md