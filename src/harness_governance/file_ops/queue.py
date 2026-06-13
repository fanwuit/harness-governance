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


def read_queue(queue_path: Path) -> list[QueueItem]:
    """Read and parse a NEXT.md file."""
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


__all__ = ["parse_queue", "read_queue", "format_queue"]