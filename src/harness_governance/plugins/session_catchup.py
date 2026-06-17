"""Session catchup helper (port of ``planning-with-files/scripts/session-catchup.py``).

Reports unsynced context after the last planning file update. Used by
agents on session start to pick up where a prior session left off.

The implementation is a faithful, dependency-free port of the legacy
Python script's Claude + Codex branches. OpenCode support is intentionally
omitted in Phase B (it requires ``sqlite3`` introspection of an
external DB); a placeholder stub is returned when that runtime is
detected so callers degrade gracefully.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

PLANNING_FILES: tuple[str, ...] = ("task_plan.md", "progress.md", "findings.md")
MIN_SESSION_BYTES = 5000


def _normalize_path(project_path: str) -> str:
    """Git Bash /c/Users/... → C:/Users/... (matches Claude Code internal)."""
    p = project_path
    if len(p) >= 3 and p[0] == "/" and p[2] == "/":
        p = p[1].upper() + ":" + p[2:]
    try:
        resolved = str(Path(p).resolve())
        if os.name == "nt" or "\\" in resolved:
            p = resolved
    except OSError:
        pass
    return p


def _claude_project_dir(project_path: str) -> Path:
    normalized = _normalize_path(project_path)
    sanitized = normalized.replace("\\", "-").replace("/", "-").replace(":", "-").replace("_", "-")
    if sanitized.startswith("-"):
        sanitized = sanitized[1:]
    return Path.home() / ".claude" / "projects" / sanitized


def _codex_sessions_dir() -> Path:
    return Path(os.path.expanduser(os.environ.get("CODEX_SESSIONS_DIR", "~/.codex/sessions")))


def _list_claude_sessions(project_dir: Path) -> list[Path]:
    if not project_dir.is_dir():
        return []
    sessions = [s for s in project_dir.glob("*.jsonl") if not s.name.startswith("agent-")]
    sessions.sort(key=_safe_mtime, reverse=True)
    return [s for s in sessions if _is_substantial(s)]


def _list_codex_sessions(project_path: str) -> list[Path]:
    sessions_dir = _codex_sessions_dir()
    if not sessions_dir.is_dir():
        return []
    project_cmp = _normalize_path(project_path)
    thread = os.environ.get("CODEX_THREAD_ID", "").strip()
    candidates = sorted(sessions_dir.rglob("rollout-*.jsonl"), key=_safe_mtime, reverse=True)
    matched: list[Path] = []
    for s in candidates:
        if thread and thread not in s.name:
            continue
        if _is_codex_session_for_project(s, project_cmp):
            matched.append(s)
    return matched


def _is_codex_session_for_project(session: Path, project_cmp: str) -> bool:
    try:
        if session.stat().st_size <= MIN_SESSION_BYTES:
            return False
    except OSError:
        return False
    try:
        with session.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if data.get("type") != "session_meta":
                    continue
                payload = data.get("payload")
                if not isinstance(payload, dict):
                    return False
                source = payload.get("source")
                if isinstance(source, dict) and "subagent" in source:
                    return False
                cwd = payload.get("cwd")
                if isinstance(cwd, str) and _normalize_path(cwd) == project_cmp:
                    return True
                return False
    except OSError:
        return False
    return False


def _safe_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _is_substantial(session: Path) -> bool:
    try:
        return session.stat().st_size > MIN_SESSION_BYTES
    except OSError:
        return False


def _planning_file_from_path(path_value: str) -> str | None:
    for pf in PLANNING_FILES:
        if path_value.endswith(pf):
            return pf
    return None


@dataclass(slots=True)
class CatchupReport:
    runtime: str
    previous_session: Path | None = None
    last_planning_update_file: str | None = None
    last_planning_update_line: int = -1
    unsynced_message_count: int = 0
    unsynced_preview: list[str] = field(default_factory=list)

    def to_markdown(self) -> str:
        if self.previous_session is None:
            return ""
        lines = [
            "",
            "[planning-with-files] SESSION CATCHUP DETECTED",
            f"Previous session: {self.previous_session.stem}",
            f"Runtime: {self.runtime}",
        ]
        if self.last_planning_update_file:
            lines.append(
                f"Last planning update: {self.last_planning_update_file} "
                f"at message #{self.last_planning_update_line}"
            )
        lines.append(f"Unsynced messages: {self.unsynced_message_count}")
        if self.unsynced_preview:
            lines.append("")
            lines.append("--- UNSYNCED CONTEXT ---")
            lines.extend(self.unsynced_preview)
            lines.append("")
            lines.append("--- RECOMMENDED ---")
            lines.append("1. Run: git diff --stat")
            lines.append("2. Read: task_plan.md, progress.md, findings.md")
            lines.append("3. Update planning files based on above context")
            lines.append("4. Continue with task")
        return "\n".join(lines) + "\n"


def _parse_claude_messages(session: Path) -> list[dict]:
    """Parse a Claude session JSONL stream; return the raw record list."""
    out: list[dict] = []
    try:
        with session.open("r", encoding="utf-8", errors="replace") as handle:
            for line_num, line in enumerate(handle):
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                data["_line_num"] = line_num
                out.append(data)
    except OSError:
        return []
    return out


def _find_last_claude_planning_update(messages: list[dict]) -> tuple[int, str | None]:
    last_line = -1
    last_file: str | None = None
    for msg in messages:
        line_num = msg.get("_line_num")
        if not isinstance(line_num, int):
            continue
        content = msg.get("message", {}).get("content", [])
        if not isinstance(content, list):
            continue
        for item in content:
            if not isinstance(item, dict) or item.get("type") != "tool_use":
                continue
            tool_name = item.get("name", "")
            tool_input = item.get("input", {})
            if tool_name in ("Write", "Edit") and isinstance(tool_input, dict):
                pf = _planning_file_from_path(tool_input.get("file_path", ""))
                if pf:
                    last_line = line_num
                    last_file = pf
    return last_line, last_file


def _extract_claude_after(
    messages: list[dict], after_line: int
) -> list[dict]:
    """Surface user/assistant messages with line numbers after ``after_line``."""
    out: list[dict] = []
    for msg in messages:
        line_num = msg.get("_line_num")
        if not isinstance(line_num, int) or line_num <= after_line:
            continue
        msg_type = msg.get("type")
        if msg_type == "user" and not msg.get("isMeta", False):
            content = msg.get("message", {}).get("content", "")
            text = content if isinstance(content, str) else ""
            if text.startswith(("<local-command", "<command-", "<task-notification")):
                continue
            if len(text) > 20:
                out.append({"role": "user", "text": text, "line": line_num})
        elif msg_type == "assistant":
            content = msg.get("message", {}).get("content", "")
            text = content if isinstance(content, str) else "\n".join(
                item.get("text", "")
                for item in content
                if isinstance(item, dict) and isinstance(item.get("text"), str)
            )
            tools: list[str] = []
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get("type") == "tool_use":
                        tool_input = item.get("input", {})
                        if not isinstance(tool_input, dict):
                            tool_input = {}
                        if item.get("name") == "Edit":
                            tools.append(f"Edit: {tool_input.get('file_path', '')}")
                        elif item.get("name") == "Write":
                            tools.append(f"Write: {tool_input.get('file_path', '')}")
                        elif item.get("name") == "Bash":
                            tools.append(f"Bash: {(tool_input.get('command', '') or '')[:80]}")
            if text or tools:
                out.append({"role": "assistant", "text": text[:600], "tools": tools, "line": line_num})
    return out


def catchup(project_path: str) -> CatchupReport:
    """Return a :class:`CatchupReport` for the given project."""
    has_planning = any((Path(project_path) / f).exists() for f in PLANNING_FILES)
    if not has_planning:
        return CatchupReport(runtime="none")

    claude_dir = _claude_project_dir(project_path)
    if claude_dir.is_dir():
        sessions = _list_claude_sessions(claude_dir)
        if not sessions:
            return CatchupReport(runtime="claude")
        target = sessions[0]
        messages = _parse_claude_messages(target)
        last_line, last_file = _find_last_claude_planning_update(messages)
        if last_line < 0:
            return CatchupReport(runtime="claude", previous_session=target)
        after = _extract_claude_after(messages, last_line)
        preview: list[str] = []
        for msg in after[-15:]:
            preview.append(
                f"{msg['role'].upper()} (line {msg['line']}): {msg['text'][:300]}"
            )
            if msg.get("tools"):
                preview.append(f"  Tools: {', '.join(msg['tools'][:4])}")
        return CatchupReport(
            runtime="claude",
            previous_session=target,
            last_planning_update_file=last_file,
            last_planning_update_line=last_line,
            unsynced_message_count=len(after),
            unsynced_preview=preview,
        )

    codex_sessions = _list_codex_sessions(project_path)
    if codex_sessions:
        return CatchupReport(
            runtime="codex",
            previous_session=codex_sessions[0],
            last_planning_update_file=None,
            last_planning_update_line=-1,
            unsynced_message_count=0,
        )

    return CatchupReport(runtime="none")


def main(argv: Iterable[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    project_path = args[0] if args else os.getcwd()
    report = catchup(project_path)
    markdown = report.to_markdown()
    if markdown:
        sys.stdout.write(markdown)
    return 0


__all__ = ["CatchupReport", "catchup", "main"]