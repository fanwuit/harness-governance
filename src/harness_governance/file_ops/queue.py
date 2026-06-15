"""NEXT.md queue helpers.

The queue is the scheduler surface used by ``harness-status.mjs`` and
``autonomous-ready-loop``. This module parses entries into
:class:`harness_governance.models.QueueItem` records so they can be
rendered or routed programmatically.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

from ..models.schemas import QueueItem
from ..state_machine.layers import HarnessLayer

# ``[active]`` / ``[ready]`` / ``[blocked]`` / ``[not-now]`` flags
# appear at the start of a queue entry line.
_TAG_RE = re.compile(r"^\s*\[(?P<tag>active|ready|blocked|not-now|done)\]\s+", re.IGNORECASE)
# ``Key: Value`` field within an entry. The leading ``- `` is
# optional because both plain and bullet-list forms are accepted.
_FIELD_RE = re.compile(
    r"^-\s*(?P<key>Layer|Change|Packetization|Evidence)\s*:\s*(?P<value>.+?)\s*$",
    re.MULTILINE,
)


def parse_queue(markdown: str) -> list[QueueItem]:
    """Parse a NEXT.md document into a list of :class:`QueueItem` objects.

    Entries are separated by a blank line. Each entry begins with a tag
    (``[active]``, ``[ready]``, …) optionally followed by ``Key: Value``
    fields. Unknown fields are preserved on ``QueueItem.raw``.
    """
    items: list[QueueItem] = []
    current: list[str] = []

    def flush() -> None:
        if not current:
            return
        raw = "\n".join(current).strip()
        items.append(_entry_to_item(raw))

    for line in markdown.splitlines():
        if line.strip() == "":
            flush()
            current = []
            continue
        current.append(line)
    flush()

    if not items and markdown.strip():
        items.append(QueueItem(raw=markdown.strip()))

    return items


def read_queue(
    queue_path: Path,
    blocked_statuses: tuple[str, ...] = ("blocked", "archived"),
) -> list[QueueItem]:
    """Read and parse a NEXT.md file.

    *blocked_statuses* documents which tag values the governance model
    treats as non-actionable.  The default matches the schema default in
    :class:`HarnessConfig`.  Callers may pass ``cfg.blocked_statuses``
    from the project config to override.
    """
    if not queue_path.is_file():
        return []
    return parse_queue(queue_path.read_text(encoding="utf-8"))


def _entry_to_item(raw: str) -> QueueItem:
    tag_match = _TAG_RE.match(raw)
    tag = tag_match.group("tag").lower() if tag_match else ""
    active = tag == "active"
    ready = tag == "ready"

    layer: HarnessLayer | None = None
    change_id: str | None = None
    packetization: str | None = None
    evidence: str | None = None

    for line in raw.splitlines():
        field = _FIELD_RE.match(line)
        if not field:
            continue
        key = field.group("key")
        value = field.group("value")
        if key == "Layer":
            try:
                layer = HarnessLayer(value.strip().lower())
            except ValueError:
                layer = None
        elif key == "Change":
            change_id = value.strip() or None
        elif key == "Packetization":
            packetization = value.strip() or None
        elif key == "Evidence":
            evidence = value.strip() or None

    return QueueItem(
        raw=raw,
        active=active,
        ready=ready,
        layer=layer,
        change_id=change_id,
        packetization=packetization,
        evidence=evidence,
    )


def format_queue(items: Iterable[QueueItem]) -> str:
    """Render a list of items back into NEXT.md format."""
    blocks: list[str] = []
    for item in items:
        blocks.append(item.raw.strip())
    return "\n\n".join(blocks) + ("\n" if blocks else "")


# Extended inline field keys beyond the core Layer/Change/Packetization/Evidence.
# Used by extract_ready_block_fields() for Subagent runner variable extraction.
_EXTENDED_FIELD_KEYS = frozenset({
    "layer", "change", "packetization", "evidence",
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
})


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
        stripped = line.strip().lstrip("-").strip()
        if not stripped:
            continue

        colon_idx = stripped.find(":")
        if colon_idx > 0:
            candidate = stripped[:colon_idx].strip().lower()
            if candidate in _EXTENDED_FIELD_KEYS:
                if current_key is not None:
                    result[current_key] = "\n".join(buffer).strip()
                current_key = candidate
                value = stripped[colon_idx + 1:].strip()
                buffer = [value] if value else []
                continue

        if current_key is not None:
            buffer.append(stripped)

    if current_key is not None:
        result[current_key] = "\n".join(buffer).strip()

    return result


__all__ = ["parse_queue", "read_queue", "format_queue", "extract_ready_block_fields"]
