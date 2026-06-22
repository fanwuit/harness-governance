"""Configured queue file helpers.

The queue is the scheduler surface used by ``harness-status.mjs`` and
``autonomous-ready-loop``. This module parses entries into
:class:`harness_governance.models.QueueItem` records so they can be
rendered or routed programmatically.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from ..models.schemas import QueueItem, ScopeBudget
from ..state_machine.layers import HarnessLayer

# ``[active]`` / ``[ready]`` / ``[blocked]`` / ``[not-now]`` flags
# appear at the start of a queue entry line.  An optional list marker
# (``1. ``, ``- ``, ``* ``) is allowed before the tag so that numbered
# or bulleted lists like ``1. [ready] Task description`` are accepted.
_TAG_RE = re.compile(
    r"^\s*(?:(?:\d+\.|[-*])\s+)?"
    r"\[(?P<tag>planned|active|ready|blocked|not-now|done|archived)\]\s+",
    re.IGNORECASE,
)
# ``Key: Value`` field within an entry. The leading list marker
# (``- ``, ``* ``, ``1. ``) is optional so both plain and
# bullet/numbered-list forms are accepted.
_FIELD_RE = re.compile(
    r"^\s*(?:[-*]|\d+\.)?\s*"
    r"(?P<key>Id|ID|Status|Layer|Role|Change|ChangeId|ChangeID|Packetization|"
    r"ChangeKind|Change Kind|GateId|Gate ID|OwnerFiles|Owner Files|"
    r"Evidence|Verification|Scope|DependsOn|Depends On|Session|SessionId|"
    r"SessionID|StopConditions|Stop Conditions|HandoffFrom|Handoff From)\s*:\s*(?P<value>.+?)\s*$",
    re.MULTILINE | re.IGNORECASE,
)


def parse_queue(markdown: str) -> list[QueueItem]:
    """Parse queue markdown into a list of :class:`QueueItem` objects.

    Entries are separated by a blank line. Each entry begins with a tag
    (``[active]``, ``[ready]``, …) optionally followed by ``Key: Value``
    fields. Unknown fields are preserved on ``QueueItem.raw``.
    """
    items: list[QueueItem] = []
    current: list[str] = []
    in_comment = False

    def flush() -> None:
        if not current:
            return
        raw = "\n".join(current).strip()
        if _TAG_RE.match(raw):
            items.append(_entry_to_item(raw))

    for line in markdown.splitlines():
        stripped = line.strip()
        if in_comment:
            if "-->" in stripped:
                in_comment = False
            continue
        if stripped.startswith("<!--"):
            if "-->" not in stripped:
                in_comment = True
            continue
        if line.strip() == "":
            flush()
            current = []
            continue
        current.append(line)
    flush()

    return items


def read_queue(
    queue_path: Path,
    blocked_statuses: tuple[str, ...] = ("blocked", "archived"),
) -> list[QueueItem]:
    """Read and parse a configured queue file.

    *blocked_statuses* documents which tag values the governance model
    treats as non-actionable.  The default matches the schema default in
    :class:`HarnessConfig`.  Callers may pass ``cfg.blocked_statuses``
    from the project config to override.
    """
    if not queue_path.is_file():
        return []
    return parse_queue(queue_path.read_text(encoding="utf-8"))


def _parse_scope(value: str) -> ScopeBudget:
    """Parse a ``Scope:`` value string into a :class:`ScopeBudget`.

    Accepted formats::

        Scope: max-files=8, max-diff-lines=500
        Scope: max-files=3, forbidden=src/core/**, owner=src/feat.py
        Scope: 8/500

    The short form ``N/M`` means ``max-files=N, max-diff-lines=M``.
    The long form uses ``key=value`` pairs separated by commas.
    ``forbidden`` and ``owner`` accept comma-separated glob patterns
    (use semicolons within the value if commas are needed in globs).
    """
    value = value.strip()
    max_files = 0
    max_diff_lines = 0
    forbidden: list[str] = []
    owner: list[str] = []

    # Short form: "8/500"
    if "/" in value and "=" not in value:
        parts = value.split("/", 1)
        try:
            max_files = int(parts[0].strip())
        except ValueError:
            pass
        try:
            max_diff_lines = int(parts[1].strip())
        except ValueError:
            pass
        return ScopeBudget(max_files=max_files, max_diff_lines=max_diff_lines)

    # Long form: "max-files=8, max-diff-lines=500, forbidden=..., owner=..."
    for token in value.split(","):
        token = token.strip()
        if not token:
            continue
        if "=" not in token:
            continue
        key, _, val = token.partition("=")
        key = key.strip().lower()
        val = val.strip()
        if key in ("max-files", "max_files"):
            try:
                max_files = int(val)
            except ValueError:
                pass
        elif key in ("max-diff-lines", "max_diff_lines"):
            try:
                max_diff_lines = int(val)
            except ValueError:
                pass
        elif key == "forbidden":
            forbidden.extend(p.strip() for p in val.split(";") if p.strip())
        elif key == "owner":
            owner.extend(p.strip() for p in val.split(";") if p.strip())

    return ScopeBudget(
        max_files=max_files,
        max_diff_lines=max_diff_lines,
        forbidden_paths=tuple(forbidden),
        owner_files=tuple(owner),
    )


def _entry_to_item(raw: str) -> QueueItem:
    tag_match = _TAG_RE.match(raw)
    tag = tag_match.group("tag").lower() if tag_match else ""
    active = tag == "active"
    ready = tag == "ready"

    item_id: str | None = None
    status = tag
    layer: HarnessLayer | None = None
    role: str | None = None
    gate_id: str | None = None
    change_id: str | None = None
    change_kind: str | None = None
    depends_on: tuple[str, ...] = ()
    owner_files: tuple[str, ...] = ()
    session_id: str | None = None
    packetization: str | None = None
    evidence: str | None = None
    verification: str | None = None
    stop_conditions: str | None = None
    handoff_from: str | None = None
    scope_budget: ScopeBudget | None = None

    for line in raw.splitlines():
        field = _FIELD_RE.match(line)
        if not field:
            continue
        key = field.group("key").lower().replace(" ", "")
        value = field.group("value")
        if key == "id":
            item_id = value.strip() or None
        elif key == "status":
            status = value.strip().lower() or status
        elif key == "layer":
            try:
                layer = HarnessLayer(value.strip().lower())
            except ValueError:
                layer = None
        elif key == "role":
            role = value.strip().lower() or None
        elif key in {"gateid", "gateid"}:
            gate_id = value.strip() or None
        elif key in {"change", "changeid"}:
            change_id = value.strip() or None
        elif key in {"changekind"}:
            change_kind = value.strip() or None
        elif key == "dependson":
            depends_on = tuple(
                part.strip()
                for part in re.split(r"[,;]", value)
                if part.strip()
            )
        elif key == "ownerfiles":
            owner_files = tuple(
                part.strip()
                for part in re.split(r"[,;]", value)
                if part.strip()
            )
        elif key in {"session", "sessionid"}:
            session_id = value.strip() or None
        elif key == "packetization":
            packetization = value.strip() or None
        elif key == "evidence":
            evidence = value.strip() or None
        elif key == "verification":
            verification = value.strip() or None
        elif key == "stopconditions":
            stop_conditions = value.strip() or None
        elif key == "handofffrom":
            handoff_from = value.strip() or None
        elif key == "scope":
            scope_budget = _parse_scope(value)

    return QueueItem(
        raw=raw,
        id=item_id,
        status=status,
        active=active,
        ready=ready,
        layer=layer,
        role=role,
        gate_id=gate_id,
        change_id=change_id,
        change_kind=change_kind,
        depends_on=depends_on,
        owner_files=owner_files,
        session_id=session_id,
        packetization=packetization,
        evidence=evidence,
        verification=verification,
        stop_conditions=stop_conditions,
        handoff_from=handoff_from,
        scope_budget=scope_budget,
    )


def format_queue(items: Iterable[QueueItem]) -> str:
    """Render a list of items back into queue markdown format."""
    blocks: list[str] = []
    for item in items:
        blocks.append(item.raw.strip())
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def append_governed_queue_item(
    queue_path: Path,
    *,
    session_id: str,
    description: str,
    layer: HarnessLayer,
    rigor_tier: str,
) -> bool:
    """Append a governed task entry to the queue file if not already present."""
    existing = queue_path.read_text(encoding="utf-8") if queue_path.is_file() else ""
    if f"Session: {session_id}" in existing:
        return False

    entry = "\n".join(
        (
            f"[active] {description}",
            f"- Session: {session_id}",
            f"- Layer: {layer.value}",
            f"- Rigor: {rigor_tier}",
            "- Verification command: harness check all",
            "- Done when: review close records verification evidence",
        )
    )
    queue_path.parent.mkdir(parents=True, exist_ok=True)
    separator = "\n\n" if existing.strip() else ""
    queue_path.write_text(existing.rstrip() + separator + entry + "\n", encoding="utf-8")
    return True


def append_structured_queue_item(
    queue_path: Path,
    *,
    item_id: str,
    description: str,
    status: str = "planned",
    layer: str | None = None,
    role: str | None = None,
    change_id: str | None = None,
    gate_id: str | None = None,
    change_kind: str | None = None,
    depends_on: Iterable[str] = (),
    owner_files: Iterable[str] = (),
    session_id: str | None = None,
    verification: str | None = None,
    stop_conditions: str | None = None,
    handoff_from: str | None = None,
) -> bool:
    """Append a structured queue item if ``Id`` is not already present."""
    existing = queue_path.read_text(encoding="utf-8") if queue_path.is_file() else ""
    if re.search(rf"^\s*-?\s*Id:\s*{re.escape(item_id)}\s*$", existing, re.MULTILINE):
        return False

    entry = [f"[{status}] {description}", f"- Id: {item_id}", f"- Status: {status}"]
    if layer:
        entry.append(f"- Layer: {layer}")
    if role:
        entry.append(f"- Role: {role}")
    if change_id:
        entry.append(f"- ChangeId: {change_id}")
    if gate_id:
        entry.append(f"- GateId: {gate_id}")
    if change_kind:
        entry.append(f"- ChangeKind: {change_kind}")
    if depends_on:
        entry.append(f"- DependsOn: {', '.join(depends_on)}")
    if owner_files:
        entry.append(f"- OwnerFiles: {', '.join(owner_files)}")
    if session_id:
        entry.append(f"- SessionId: {session_id}")
    if verification:
        entry.append(f"- Verification: {verification}")
    if stop_conditions:
        entry.append(f"- StopConditions: {stop_conditions}")
    if handoff_from:
        entry.append(f"- HandoffFrom: {handoff_from}")

    queue_path.parent.mkdir(parents=True, exist_ok=True)
    separator = "\n\n" if existing.strip() else ""
    queue_path.write_text(
        existing.rstrip() + separator + "\n".join(entry) + "\n",
        encoding="utf-8",
    )
    return True


def mark_queue_item_status(
    queue_path: Path,
    *,
    task_id: str,
    status: str,
    session_id: str | None = None,
    evidence: Iterable[str] = (),
    risks: Iterable[str] = (),
    completed_at: str | None = None,
) -> bool:
    """Update the queue block matching *task_id* to a new status."""
    if not queue_path.is_file():
        return False

    text = queue_path.read_text(encoding="utf-8")
    blocks = _split_blocks(text)
    changed = False
    rendered: list[str] = []
    for block in blocks:
        if not changed and _queue_block_matches(block, task_id):
            rendered.append(
                _set_block_status(
                    block,
                    task_id,
                    status=status,
                    session_id=session_id,
                    evidence=evidence,
                    risks=risks,
                    completed_at=completed_at,
                )
            )
            changed = True
        else:
            rendered.append(block.rstrip())

    if changed:
        queue_path.write_text("\n\n".join(rendered).rstrip() + "\n", encoding="utf-8")
    return changed


def mark_queue_item_done(
    queue_path: Path,
    *,
    task_id: str,
    evidence: Iterable[str] = (),
    risks: Iterable[str] = (),
    session_id: str | None = None,
    completed_at: str | None = None,
) -> bool:
    """Mark the queue block matching *task_id* as ``[done]``.

    Matching is intentionally broad enough for CLI use: it accepts a
    ``Session: <task_id>`` field, a ``Change: <task_id>`` field, or a first-line
    task title containing the id passed to ``harness review close``.
    """
    if not queue_path.is_file():
        return False

    text = queue_path.read_text(encoding="utf-8")
    blocks = _split_blocks(text)
    changed = False
    rendered: list[str] = []
    for block in blocks:
        if not changed and _queue_block_matches(block, task_id):
            rendered.append(
                _mark_block_done(
                    block,
                    task_id,
                    evidence,
                    risks,
                    session_id=session_id,
                    completed_at=completed_at,
                )
            )
            changed = True
        else:
            rendered.append(block.rstrip())

    if changed:
        queue_path.write_text("\n\n".join(rendered).rstrip() + "\n", encoding="utf-8")
    return changed


def _split_blocks(text: str) -> list[str]:
    blocks: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        if line.strip() == "":
            if current:
                blocks.append("\n".join(current).rstrip())
                current = []
            continue
        current.append(line)
    if current:
        blocks.append("\n".join(current).rstrip())
    return blocks


def _queue_block_matches(block: str, task_id: str) -> bool:
    escaped = re.escape(task_id)
    return bool(
        re.search(rf"^\s*-?\s*Id:\s*{escaped}\s*$", block, re.IGNORECASE | re.MULTILINE)
        or re.search(rf"^\s*-?\s*ID:\s*{escaped}\s*$", block, re.MULTILINE)
        or re.search(rf"^\s*-?\s*Session:\s*{escaped}\s*$", block, re.MULTILINE)
        or re.search(rf"^\s*-?\s*Change:\s*{escaped}\s*$", block, re.MULTILINE)
        or re.search(rf"^\s*\[(?:active|ready)\]\s+.*{escaped}", block, re.IGNORECASE)
    )


def _mark_block_done(
    block: str,
    task_id: str,
    evidence: Iterable[str],
    risks: Iterable[str],
    *,
    session_id: str | None = None,
    completed_at: str | None = None,
) -> str:
    lines = block.splitlines()
    if lines:
        lines[0] = re.sub(
            r"^(\s*)\[(active|ready)\]",
            r"\1[done]",
            lines[0],
            count=1,
            flags=re.IGNORECASE,
        )
    if not any(re.match(r"\s*-?\s*Status:\s*", line, re.IGNORECASE) for line in lines):
        lines.append("- Status: done")
    if not any(re.match(r"\s*-?\s*Closed:\s*", line) for line in lines):
        lines.append(f"- Closed: {task_id}")
    if session_id and not any(
        re.match(r"\s*-?\s*Session(?:Id|ID)?:\s*", line, re.IGNORECASE)
        for line in lines
    ):
        lines.append(f"- SessionId: {session_id}")
    if completed_at and not any(
        re.match(r"\s*-?\s*CompletedAt:\s*", line, re.IGNORECASE) for line in lines
    ):
        lines.append(f"- CompletedAt: {completed_at}")
    for item in evidence:
        lines.append(f"- Evidence: {item}")
    for item in risks:
        lines.append(f"- Risk: {item}")
    return "\n".join(lines)


def _set_block_status(
    block: str,
    task_id: str,
    *,
    status: str,
    session_id: str | None = None,
    evidence: Iterable[str] = (),
    risks: Iterable[str] = (),
    completed_at: str | None = None,
) -> str:
    lines = block.splitlines()
    if lines:
        lines[0] = re.sub(
            r"^(\s*)\[(active|ready|planned|blocked|done|not-now|archived)\]",
            rf"\1[{status}]",
            lines[0],
            count=1,
            flags=re.IGNORECASE,
        )
    else:
        lines = [f"[{status}] {task_id}"]

    def ensure_line(prefix: str, value: str) -> None:
        pattern = re.compile(rf"^\s*-?\s*{re.escape(prefix)}\s*:", re.IGNORECASE)
        if not any(pattern.match(line) for line in lines):
            lines.append(f"- {prefix}: {value}")
        else:
            for idx, line in enumerate(lines):
                if pattern.match(line):
                    lines[idx] = f"- {prefix}: {value}"
                    break

    ensure_line("Status", status)
    if session_id:
        ensure_line("SessionId", session_id)
    if completed_at:
        ensure_line("CompletedAt", completed_at)
    for item in evidence:
        lines.append(f"- Evidence: {item}")
    for item in risks:
        lines.append(f"- Risk: {item}")
    return "\n".join(lines)


# Extended inline field keys beyond the core Layer/Change/Packetization/Evidence.
# Used by extract_ready_block_fields() for Subagent runner variable extraction.
_EXTENDED_FIELD_KEYS = frozenset(
    {
        "layer",
        "change",
        "packetization",
        "evidence",
        "scope",
        "role",
        "forbidden shortcut",
        "forbidden scope",
        "verification command",
        "verification commands",
        "done when",
        "allowed assumptions",
        "expected behavior",
        "failure behavior",
        "owner files",
        "success criteria",
        "non-goals",
        "non goals",
        "stop conditions",
    }
)


def extract_ready_block_fields(raw: str) -> dict[str, str]:
    """Extract ``Key: Value`` inline fields from a ready block's raw text.

    Extends the core four fields (Layer, Change, Packetization, Evidence)
    with role-specific fields used by the Subagent runner for template
    variable extraction. Multi-line values (continuation lines that do
    not match any known key) are appended to the preceding key.

    Returns a dict with lower-cased keys.
    """
    result: dict[str, str] = {}
    current_key: str | None = None
    buffer: list[str] = []

    for line in raw.splitlines():
        stripped = line.strip()
        # Strip optional list marker: "1. ", "- ", "* "
        stripped = re.sub(r"^(?:\d+\.|[-*])\s+", "", stripped)
        if not stripped:
            continue

        colon_idx = stripped.find(":")
        if colon_idx > 0:
            candidate = stripped[:colon_idx].strip().lower()
            if candidate in _EXTENDED_FIELD_KEYS:
                if current_key is not None:
                    result[current_key] = "\n".join(buffer).strip()
                current_key = candidate
                value = stripped[colon_idx + 1 :].strip()
                buffer = [value] if value else []
                continue

        if current_key is not None:
            buffer.append(stripped)

    if current_key is not None:
        result[current_key] = "\n".join(buffer).strip()

    return result


__all__ = [
    "parse_queue",
    "read_queue",
    "format_queue",
    "append_governed_queue_item",
    "append_structured_queue_item",
    "mark_queue_item_status",
    "mark_queue_item_done",
    "extract_ready_block_fields",
]
