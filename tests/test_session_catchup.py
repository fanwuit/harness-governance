"""Tests for the session-catchup plugin."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from harness_governance.plugins.session_catchup import (
    CatchupReport,
    MIN_SESSION_BYTES,
    PLANNING_FILES,
    _claude_project_dir,
    _codex_sessions_dir,
    _extract_claude_after,
    _find_last_claude_planning_update,
    _is_codex_session_for_project,
    _is_substantial,
    _list_claude_sessions,
    _list_codex_sessions,
    _normalize_path,
    _parse_claude_messages,
    _planning_file_from_path,
    _safe_mtime,
    catchup,
    main,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_big_session(path: Path, extra_lines: list[dict] | None = None) -> Path:
    """Write a JSONL session file that exceeds MIN_SESSION_BYTES."""
    lines = extra_lines or []
    # Pad with dummy comment lines to exceed the size threshold.
    padding = {"type": "padding", "data": "x" * 200}
    while True:
        with path.open("w", encoding="utf-8") as f:
            for obj in lines:
                f.write(json.dumps(obj) + "\n")
            # write padding
            pad_line = json.dumps(padding) + "\n"
            count_needed = max(1, (MIN_SESSION_BYTES + 500) // len(pad_line) + 5)
            for _ in range(count_needed):
                f.write(pad_line)
        if path.stat().st_size > MIN_SESSION_BYTES:
            break
        padding = {"type": "padding", "data": "x" * 400}
    return path


# ===========================================================================
# 1. _normalize_path
# ===========================================================================

class TestNormalizePath:
    def test_git_bash_path_conversion(self) -> None:
        result = _normalize_path("/c/Users/foo/bar")
        assert result.startswith("C:")
        assert "Users" in result

    def test_git_bash_lowercase_drive(self) -> None:
        result = _normalize_path("/d/projects/myproj")
        assert result.startswith("D:")

    def test_normal_windows_path(self) -> None:
        result = _normalize_path("C:\\Users\\foo")
        # Should resolve without error
        assert "Users" in result or "users" in result.lower()

    def test_normal_unix_style_path(self) -> None:
        result = _normalize_path("/some/regular/path")
        assert "some" in result

    def test_short_path_no_conversion(self) -> None:
        # Path shorter than 3 chars should not trigger Git Bash conversion
        result = _normalize_path("/a")
        assert isinstance(result, str)

    def test_oserror_handling(self, tmp_path: Path) -> None:
        # Use a path component that is too long or otherwise triggers OSError
        # from Path.resolve() without causing ValueError (null bytes cause ValueError).
        long_component = "x" * 300
        result = _normalize_path(str(tmp_path / long_component))
        # Should return a string regardless of resolution outcome
        assert isinstance(result, str)


# ===========================================================================
# 2. _claude_project_dir
# ===========================================================================

class TestClaudeProjectDir:
    def test_special_chars_sanitized(self) -> None:
        result = _claude_project_dir("/home/user/my_project")
        # Underscores and slashes become dashes
        assert "_" not in result.name
        assert "/" not in result.name or os.sep not in result.name

    def test_leading_dash_stripped(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Craft a path whose sanitized form starts with a dash
        monkeypatch.setattr(Path, "home", lambda: Path("/fakehome"))
        result = _claude_project_dir("/_leading")
        assert not result.name.startswith("-")

    def test_returns_path_under_home(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(Path, "home", lambda: Path("/fakehome"))
        result = _claude_project_dir("/some/project")
        assert str(result).startswith(str(Path("/fakehome/.claude/projects")))


# ===========================================================================
# 3. _codex_sessions_dir
# ===========================================================================

class TestCodexSessionsDir:
    def test_default_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("CODEX_SESSIONS_DIR", raising=False)
        result = _codex_sessions_dir()
        assert ".codex" in str(result)
        assert "sessions" in str(result)

    def test_env_var_override(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CODEX_SESSIONS_DIR", "/custom/sessions")
        result = _codex_sessions_dir()
        assert str(result) == str(Path("/custom/sessions"))


# ===========================================================================
# 4. _list_claude_sessions
# ===========================================================================

class TestListClaudeSessions:
    def test_non_dir_returns_empty(self, tmp_path: Path) -> None:
        assert _list_claude_sessions(tmp_path / "nope") == []

    def test_filters_agent_prefix(self, tmp_path: Path) -> None:
        d = tmp_path / "proj"
        d.mkdir()
        # agent- prefixed files should be excluded
        agent_file = d / "agent-foo.jsonl"
        agent_file.write_bytes(b"x" * (MIN_SESSION_BYTES + 100))
        # Normal session file
        normal_file = d / "session-1.jsonl"
        normal_file.write_bytes(b"x" * (MIN_SESSION_BYTES + 100))
        result = _list_claude_sessions(d)
        names = [p.name for p in result]
        assert "agent-foo.jsonl" not in names
        assert "session-1.jsonl" in names

    def test_filters_small_files(self, tmp_path: Path) -> None:
        d = tmp_path / "proj"
        d.mkdir()
        small = d / "tiny.jsonl"
        small.write_text("{}", encoding="utf-8")
        result = _list_claude_sessions(d)
        assert result == []

    def test_sorted_by_mtime_descending(self, tmp_path: Path) -> None:
        d = tmp_path / "proj"
        d.mkdir()
        s1 = d / "old.jsonl"
        s1.write_bytes(b"x" * (MIN_SESSION_BYTES + 100))
        s2 = d / "new.jsonl"
        s2.write_bytes(b"x" * (MIN_SESSION_BYTES + 100))
        # Set mtime on s1 to epoch 0, s2 stays recent
        os.utime(s1, (0, 0))
        result = _list_claude_sessions(d)
        assert len(result) == 2
        assert result[0].name == "new.jsonl"
        assert result[1].name == "old.jsonl"


# ===========================================================================
# 5. _list_codex_sessions
# ===========================================================================

class TestListCodexSessions:
    def test_no_sessions_dir_returns_empty(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CODEX_SESSIONS_DIR", str(tmp_path / "missing"))
        result = _list_codex_sessions(str(tmp_path))
        assert result == []

    def test_thread_filter(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        monkeypatch.setenv("CODEX_SESSIONS_DIR", str(sessions_dir))
        monkeypatch.setenv("CODEX_THREAD_ID", "thread-abc")

        matching = sessions_dir / "rollout-thread-abc.jsonl"
        matching.write_bytes(b"x" * (MIN_SESSION_BYTES + 100))
        non_matching = sessions_dir / "rollout-thread-xyz.jsonl"
        non_matching.write_bytes(b"x" * (MIN_SESSION_BYTES + 100))

        # Patch _is_codex_session_for_project to always return True
        monkeypatch.setattr(
            "harness_governance.plugins.session_catchup._is_codex_session_for_project",
            lambda s, p: True,
        )
        result = _list_codex_sessions(str(tmp_path))
        names = [p.name for p in result]
        assert "rollout-thread-abc.jsonl" in names
        assert "rollout-thread-xyz.jsonl" not in names

    def test_project_matching(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        sessions_dir = tmp_path / "sessions"
        sessions_dir.mkdir()
        monkeypatch.setenv("CODEX_SESSIONS_DIR", str(sessions_dir))
        monkeypatch.delenv("CODEX_THREAD_ID", raising=False)

        good = sessions_dir / "rollout-good.jsonl"
        good.write_bytes(b"x" * (MIN_SESSION_BYTES + 100))
        bad = sessions_dir / "rollout-bad.jsonl"
        bad.write_bytes(b"x" * (MIN_SESSION_BYTES + 100))

        project_path = str(tmp_path / "myproject")

        def mock_check(session: Path, project_cmp: str) -> bool:
            return "good" in session.name

        monkeypatch.setattr(
            "harness_governance.plugins.session_catchup._is_codex_session_for_project",
            mock_check,
        )
        result = _list_codex_sessions(project_path)
        assert len(result) == 1
        assert "good" in result[0].name


# ===========================================================================
# 6. _is_codex_session_for_project
# ===========================================================================

class TestIsCodexSessionForProject:
    def test_small_file_returns_false(self, tmp_path: Path) -> None:
        f = tmp_path / "tiny.jsonl"
        f.write_text("{}", encoding="utf-8")
        assert _is_codex_session_for_project(f, "/some/path") is False

    def test_json_parse_error_skipped(self, tmp_path: Path) -> None:
        f = tmp_path / "bad.jsonl"
        # Write enough bytes but with invalid JSON lines
        content = "not json at all\n" * 500
        f.write_text(content, encoding="utf-8")
        assert _is_codex_session_for_project(f, "/some/path") is False

    def test_session_meta_with_valid_cwd(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        project_path = "/my/project"
        normalized_project = _normalize_path(project_path)

        f = tmp_path / "session.jsonl"
        meta = {
            "type": "session_meta",
            "payload": {"cwd": project_path, "source": {"cli": True}},
        }
        # Pad to exceed MIN_SESSION_BYTES
        _make_big_session(f, [meta])
        assert _is_codex_session_for_project(f, normalized_project) is True

    def test_session_meta_cwd_mismatch(self, tmp_path: Path) -> None:
        f = tmp_path / "session.jsonl"
        meta = {
            "type": "session_meta",
            "payload": {"cwd": "/other/path", "source": {"cli": True}},
        }
        _make_big_session(f, [meta])
        assert _is_codex_session_for_project(f, _normalize_path("/my/project")) is False

    def test_subagent_skip(self, tmp_path: Path) -> None:
        f = tmp_path / "session.jsonl"
        meta = {
            "type": "session_meta",
            "payload": {"cwd": "/my/project", "source": {"subagent": "worker"}},
        }
        _make_big_session(f, [meta])
        assert _is_codex_session_for_project(f, _normalize_path("/my/project")) is False

    def test_non_dict_payload_returns_false(self, tmp_path: Path) -> None:
        f = tmp_path / "session.jsonl"
        meta = {"type": "session_meta", "payload": "not_a_dict"}
        _make_big_session(f, [meta])
        assert _is_codex_session_for_project(f, "/any") is False

    def test_oserror_returns_false(self, tmp_path: Path) -> None:
        f = tmp_path / "gone.jsonl"
        # Don't create the file — stat will raise OSError
        assert _is_codex_session_for_project(f, "/any") is False


# ===========================================================================
# 7. _safe_mtime
# ===========================================================================

class TestSafeMtime:
    def test_normal_path(self, tmp_path: Path) -> None:
        f = tmp_path / "file.txt"
        f.write_text("hi", encoding="utf-8")
        result = _safe_mtime(f)
        assert result > 0

    def test_oserror_returns_zero(self, tmp_path: Path) -> None:
        f = tmp_path / "nonexistent.txt"
        assert _safe_mtime(f) == 0.0


# ===========================================================================
# 8. _is_substantial
# ===========================================================================

class TestIsSubstantial:
    def test_large_file(self, tmp_path: Path) -> None:
        f = tmp_path / "big.jsonl"
        f.write_bytes(b"x" * (MIN_SESSION_BYTES + 1))
        assert _is_substantial(f) is True

    def test_small_file(self, tmp_path: Path) -> None:
        f = tmp_path / "small.jsonl"
        f.write_text("{}", encoding="utf-8")
        assert _is_substantial(f) is False

    def test_oserror_returns_false(self, tmp_path: Path) -> None:
        f = tmp_path / "missing.jsonl"
        assert _is_substantial(f) is False


# ===========================================================================
# 9. _planning_file_from_path
# ===========================================================================

class TestPlanningFileFromPath:
    def test_match_task_plan(self) -> None:
        assert _planning_file_from_path("/some/dir/task_plan.md") == "task_plan.md"

    def test_match_progress(self) -> None:
        assert _planning_file_from_path("progress.md") == "progress.md"

    def test_match_findings(self) -> None:
        assert _planning_file_from_path("/a/b/findings.md") == "findings.md"

    def test_no_match(self) -> None:
        assert _planning_file_from_path("/some/other/file.txt") is None

    def test_partial_name_no_match(self) -> None:
        assert _planning_file_from_path("my_task_plan_extra.md") is None


# ===========================================================================
# 10. CatchupReport.to_markdown
# ===========================================================================

class TestCatchupReportToMarkdown:
    def test_none_previous_session_returns_empty(self) -> None:
        report = CatchupReport(runtime="none")
        assert report.to_markdown() == ""

    def test_with_planning_file(self) -> None:
        report = CatchupReport(
            runtime="claude",
            previous_session=Path("/tmp/sess.jsonl"),
            last_planning_update_file="task_plan.md",
            last_planning_update_line=10,
            unsynced_message_count=3,
            unsynced_preview=["USER (line 11): hello world"],
        )
        md = report.to_markdown()
        assert "SESSION CATCHUP DETECTED" in md
        assert "task_plan.md" in md
        assert "message #10" in md
        assert "Unsynced messages: 3" in md
        assert "RECOMMENDED" in md

    def test_without_planning_file(self) -> None:
        report = CatchupReport(
            runtime="claude",
            previous_session=Path("/tmp/sess.jsonl"),
            last_planning_update_file=None,
            last_planning_update_line=-1,
            unsynced_message_count=0,
        )
        md = report.to_markdown()
        assert "SESSION CATCHUP DETECTED" in md
        assert "Last planning update" not in md
        # No preview means no RECOMMENDED block
        assert "RECOMMENDED" not in md

    def test_with_preview_but_no_planning(self) -> None:
        report = CatchupReport(
            runtime="codex",
            previous_session=Path("/tmp/sess.jsonl"),
            unsynced_message_count=1,
            unsynced_preview=["USER: something"],
        )
        md = report.to_markdown()
        assert "UNSIGNED CONTEXT" in md or "UNSYNCED CONTEXT" in md
        assert "git diff" in md


# ===========================================================================
# 11. _parse_claude_messages
# ===========================================================================

class TestParseClaudeMessages:
    def test_normal_jsonl(self, tmp_path: Path) -> None:
        f = tmp_path / "session.jsonl"
        line1 = {"type": "user", "message": {"content": "hi"}}
        line2 = {"type": "assistant", "message": {"content": "hello"}}
        f.write_text(json.dumps(line1) + "\n" + json.dumps(line2) + "\n", encoding="utf-8")
        msgs = _parse_claude_messages(f)
        assert len(msgs) == 2
        assert msgs[0]["type"] == "user"
        assert msgs[0]["_line_num"] == 0
        assert msgs[1]["_line_num"] == 1

    def test_bad_json_lines_skipped(self, tmp_path: Path) -> None:
        f = tmp_path / "session.jsonl"
        content = '{"type":"user","message":{"content":"ok"}}\nnot json\n{"type":"assistant","message":{"content":"yo"}}\n'
        f.write_text(content, encoding="utf-8")
        msgs = _parse_claude_messages(f)
        assert len(msgs) == 2
        types = [m["type"] for m in msgs]
        assert "user" in types
        assert "assistant" in types

    def test_empty_lines_skipped(self, tmp_path: Path) -> None:
        f = tmp_path / "session.jsonl"
        f.write_text('\n\n{"type":"user","message":{"content":"x"}}\n\n', encoding="utf-8")
        msgs = _parse_claude_messages(f)
        assert len(msgs) == 1

    def test_oserror_returns_empty(self, tmp_path: Path) -> None:
        f = tmp_path / "nonexistent.jsonl"
        assert _parse_claude_messages(f) == []


# ===========================================================================
# 12. _find_last_claude_planning_update
# ===========================================================================

class TestFindLastClaudePlanningUpdate:
    def test_with_write_tool(self) -> None:
        messages = [
            {
                "type": "assistant",
                "_line_num": 5,
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Write",
                            "input": {"file_path": "/dir/task_plan.md"},
                        }
                    ]
                },
            }
        ]
        line, pf = _find_last_claude_planning_update(messages)
        assert line == 5
        assert pf == "task_plan.md"

    def test_with_edit_tool(self) -> None:
        messages = [
            {
                "type": "assistant",
                "_line_num": 3,
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Edit",
                            "input": {"file_path": "/dir/progress.md"},
                        }
                    ]
                },
            }
        ]
        line, pf = _find_last_claude_planning_update(messages)
        assert line == 3
        assert pf == "progress.md"

    def test_returns_last_when_multiple(self) -> None:
        messages = [
            {
                "type": "assistant",
                "_line_num": 2,
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Write",
                            "input": {"file_path": "/a/task_plan.md"},
                        }
                    ]
                },
            },
            {
                "type": "assistant",
                "_line_num": 8,
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Edit",
                            "input": {"file_path": "/b/findings.md"},
                        }
                    ]
                },
            },
        ]
        line, pf = _find_last_claude_planning_update(messages)
        assert line == 8
        assert pf == "findings.md"

    def test_no_planning_tools(self) -> None:
        messages = [
            {
                "type": "assistant",
                "_line_num": 1,
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Bash",
                            "input": {"command": "ls"},
                        }
                    ]
                },
            }
        ]
        line, pf = _find_last_claude_planning_update(messages)
        assert line == -1
        assert pf is None

    def test_non_list_content_skipped(self) -> None:
        messages = [
            {
                "type": "assistant",
                "_line_num": 1,
                "message": {"content": "just text, not a list"},
            }
        ]
        line, pf = _find_last_claude_planning_update(messages)
        assert line == -1
        assert pf is None

    def test_empty_messages(self) -> None:
        line, pf = _find_last_claude_planning_update([])
        assert line == -1
        assert pf is None


# ===========================================================================
# 13. _extract_claude_after
# ===========================================================================

class TestExtractClaudeAfter:
    def test_user_message_included(self) -> None:
        messages = [
            {
                "type": "user",
                "_line_num": 5,
                "message": {"content": "please continue the work that was started earlier in this session"},
            }
        ]
        result = _extract_claude_after(messages, 3)
        assert len(result) == 1
        assert result[0]["role"] == "user"
        assert "please continue" in result[0]["text"]

    def test_user_meta_skipped(self) -> None:
        messages = [
            {
                "type": "user",
                "_line_num": 5,
                "isMeta": True,
                "message": {"content": "this is a meta message that should be skipped"},
            }
        ]
        result = _extract_claude_after(messages, 3)
        assert result == []

    def test_user_command_skipped(self) -> None:
        messages = [
            {
                "type": "user",
                "_line_num": 5,
                "message": {"content": "<local-command>this is a command</local-command>"},
            },
            {
                "type": "user",
                "_line_num": 6,
                "message": {"content": "<command-message>another command here</command-message>"},
            },
            {
                "type": "user",
                "_line_num": 7,
                "message": {"content": "<task-notification>notification body here</task-notification>"},
            },
        ]
        result = _extract_claude_after(messages, 3)
        assert result == []

    def test_short_user_message_skipped(self) -> None:
        messages = [
            {
                "type": "user",
                "_line_num": 5,
                "message": {"content": "short"},  # len < 20
            }
        ]
        result = _extract_claude_after(messages, 3)
        assert result == []

    def test_assistant_with_edit_tool(self) -> None:
        messages = [
            {
                "type": "assistant",
                "_line_num": 6,
                "message": {
                    "content": [
                        {
                            "type": "text",
                            "text": "I will edit the file now.",
                        },
                        {
                            "type": "tool_use",
                            "name": "Edit",
                            "input": {"file_path": "/dir/task_plan.md"},
                        },
                    ]
                },
            }
        ]
        result = _extract_claude_after(messages, 3)
        assert len(result) == 1
        assert result[0]["role"] == "assistant"
        assert "Edit: /dir/task_plan.md" in result[0]["tools"]

    def test_assistant_with_write_tool(self) -> None:
        messages = [
            {
                "type": "assistant",
                "_line_num": 6,
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Write",
                            "input": {"file_path": "/dir/progress.md"},
                        },
                    ]
                },
            }
        ]
        result = _extract_claude_after(messages, 3)
        assert len(result) == 1
        assert "Write: /dir/progress.md" in result[0]["tools"]

    def test_assistant_with_bash_tool(self) -> None:
        messages = [
            {
                "type": "assistant",
                "_line_num": 6,
                "message": {
                    "content": [
                        {
                            "type": "tool_use",
                            "name": "Bash",
                            "input": {"command": "git status --short"},
                        },
                    ]
                },
            }
        ]
        result = _extract_claude_after(messages, 3)
        assert len(result) == 1
        assert any("Bash:" in t for t in result[0]["tools"])

    def test_text_only_assistant(self) -> None:
        messages = [
            {
                "type": "assistant",
                "_line_num": 7,
                "message": {"content": "Here is some text response with enough length to be included."},
            }
        ]
        result = _extract_claude_after(messages, 3)
        assert len(result) == 1
        assert result[0]["role"] == "assistant"
        assert "text response" in result[0]["text"]

    def test_messages_before_cutoff_excluded(self) -> None:
        messages = [
            {
                "type": "user",
                "_line_num": 2,
                "message": {"content": "this message is before the cutoff line number and should be excluded from results"},
            },
            {
                "type": "user",
                "_line_num": 10,
                "message": {"content": "this message is after the cutoff and should appear in the output list"},
            },
        ]
        result = _extract_claude_after(messages, 5)
        assert len(result) == 1
        assert result[0]["line"] == 10


# ===========================================================================
# 14. catchup — additional scenarios
# ===========================================================================

class TestCatchup:
    def test_claude_session_no_planning_update(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Session exists but has no Write/Edit to planning files → previous_session set, no planning info."""
        (tmp_path / "task_plan.md").write_text("# Plan\n", encoding="utf-8")
        claude_dir = tmp_path / "claude_proj"
        claude_dir.mkdir()
        session = claude_dir / "session-1.jsonl"
        # Only Bash tool, no planning file edits
        lines = [
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {"command": "ls"}}]}},
        ]
        _make_big_session(session, lines)

        monkeypatch.setattr(
            "harness_governance.plugins.session_catchup._claude_project_dir",
            lambda path: claude_dir,
        )
        report = catchup(str(tmp_path))
        assert report.runtime == "claude"
        assert report.previous_session is not None
        assert report.last_planning_update_file is None
        assert report.last_planning_update_line == -1

    def test_codex_sessions_path(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """No claude dir → falls through to codex path."""
        project_dir = tmp_path / "myproj"
        project_dir.mkdir()
        (project_dir / "progress.md").write_text("# Progress\n", encoding="utf-8")
        sessions_dir = tmp_path / "codex_sessions"
        sessions_dir.mkdir()
        monkeypatch.setenv("CODEX_SESSIONS_DIR", str(sessions_dir))

        codex_session = sessions_dir / "rollout-abc.jsonl"
        codex_session.write_bytes(b"x" * (MIN_SESSION_BYTES + 100))

        project_path = str(project_dir)

        monkeypatch.setattr(
            "harness_governance.plugins.session_catchup._claude_project_dir",
            lambda path: tmp_path / "nonexistent_claude_dir",
        )
        monkeypatch.setattr(
            "harness_governance.plugins.session_catchup._list_codex_sessions",
            lambda path: [codex_session],
        )
        report = catchup(project_path)
        assert report.runtime == "codex"
        assert report.previous_session == codex_session

    def test_no_sessions_found(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Planning file exists but no sessions at all."""
        (tmp_path / "findings.md").write_text("# Findings\n", encoding="utf-8")
        monkeypatch.setattr(
            "harness_governance.plugins.session_catchup._claude_project_dir",
            lambda path: tmp_path / "nonexistent_claude_dir",
        )
        monkeypatch.setattr(
            "harness_governance.plugins.session_catchup._list_codex_sessions",
            lambda path: [],
        )
        report = catchup(str(tmp_path))
        assert report.runtime == "none"
        assert report.previous_session is None

    def test_claude_dir_exists_but_no_sessions(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """Claude project dir exists but is empty."""
        (tmp_path / "task_plan.md").write_text("# Plan\n", encoding="utf-8")
        claude_dir = tmp_path / "empty_claude"
        claude_dir.mkdir()
        monkeypatch.setattr(
            "harness_governance.plugins.session_catchup._claude_project_dir",
            lambda path: claude_dir,
        )
        report = catchup(str(tmp_path))
        assert report.runtime == "claude"
        assert report.previous_session is None


# ===========================================================================
# 15. main
# ===========================================================================

class TestMain:
    def test_with_args(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
        # Make catchup return an empty report
        monkeypatch.setattr(
            "harness_governance.plugins.session_catchup.catchup",
            lambda path: CatchupReport(runtime="none"),
        )
        result = main([str(tmp_path)])
        assert result == 0
        captured = capsys.readouterr()
        # Empty report → no markdown output
        assert captured.out == ""

    def test_with_report_output(self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
        report = CatchupReport(
            runtime="claude",
            previous_session=Path("/tmp/sess.jsonl"),
            last_planning_update_file="task_plan.md",
            last_planning_update_line=5,
            unsynced_message_count=1,
            unsynced_preview=["USER (line 6): continue work"],
        )
        monkeypatch.setattr(
            "harness_governance.plugins.session_catchup.catchup",
            lambda path: report,
        )
        result = main(["/some/path"])
        assert result == 0
        captured = capsys.readouterr()
        assert "SESSION CATCHUP DETECTED" in captured.out

    def test_without_args_uses_cwd(self, monkeypatch: pytest.MonkeyPatch) -> None:
        captured_paths: list[str] = []

        def fake_catchup(path: str) -> CatchupReport:
            captured_paths.append(path)
            return CatchupReport(runtime="none")

        monkeypatch.setattr("harness_governance.plugins.session_catchup.catchup", fake_catchup)
        main([])
        assert len(captured_paths) == 1
        assert captured_paths[0] == os.getcwd()

    def test_empty_report_no_stdout(self, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
        monkeypatch.setattr(
            "harness_governance.plugins.session_catchup.catchup",
            lambda path: CatchupReport(runtime="none"),
        )
        result = main(["/any/path"])
        assert result == 0
        captured = capsys.readouterr()
        assert captured.out == ""