"""Implementation Entry Record block parser.

The Entry Record is an inline Markdown block, not a standalone file.
Field headers follow the convention documented in
``governed-implementation-entry/SKILL.md``:

    Implementation Entry Record
    - Current layer: ...
    - Target: ...
    - Scope: ...
    - Contract evidence: ...
    - Readiness gate: ...
    - Packetization: ...
    - Verification command: ...
    - Review/Next state file: ...
    - Stop conditions: ...

Each header is ``- <Field>: <value>``. The block may contain blank
lines and trailing prose; we only inspect the relevant lines.
"""

from __future__ import annotations

import re
from typing import Mapping

from ..models.schemas import EntryRecord
from ..state_machine.layers import HarnessLayer

_FIELD_MAP: Mapping[str, str] = {
    "current layer": "current_layer",
    "target": "target",
    "scope": "scope",
    "contract evidence": "contract_evidence",
    "readiness gate": "readiness_gate",
    "packetization": "packetization",
    "verification command": "verification_command",
    "review/next state file": "review_next_state",
    "review / next state file": "review_next_state",
    "stop conditions": "stop_conditions",
}

_FIELD_RE = re.compile(
    r"^-\s*(?P<key>[^:]+):\s*(?P<value>.+?)\s*$",
    re.MULTILINE,
)

# Fixture-style heading that opens the block. The legacy fixture uses
# ``Implementation Entry Record:`` (no ``#`` heading), so we accept
# either form.
_HEADER_RE = re.compile(
    r"^(?:#+\s*)?Implementation Entry Record\s*:?\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def parse_entry_record(block: str) -> EntryRecord:
    """Parse a Markdown block into an :class:`EntryRecord`.

    Raises :class:`ValueError` if any required field is missing or if
    ``Current layer`` is not a recognized harness layer.
    """
    fields: dict[str, str] = {}

    for match in _FIELD_RE.finditer(block):
        key = match.group("key").strip().lower()
        value = match.group("value").strip()
        attr = _FIELD_MAP.get(key)
        if attr is None:
            continue
        fields[attr] = value

    missing = [name for name in _FIELD_MAP.values() if not fields.get(name)]
    if missing:
        raise ValueError(
            f"Implementation Entry Record missing fields: {', '.join(missing)}"
        )

    try:
        layer = HarnessLayer(fields["current_layer"].lower())
    except ValueError as exc:
        raise ValueError(
            f"Implementation Entry Record has invalid Current layer: "
            f"{fields['current_layer']!r}"
        ) from exc

    return EntryRecord(
        current_layer=layer,
        target=fields["target"],
        scope=fields["scope"],
        contract_evidence=fields["contract_evidence"],
        readiness_gate=fields["readiness_gate"],
        packetization=fields["packetization"],
        verification_command=fields["verification_command"],
        review_next_state=fields["review_next_state"],
        stop_conditions=fields["stop_conditions"],
    )


def has_entry_record_header(block: str) -> bool:
    """Return ``True`` if ``block`` contains the entry-record header."""
    return bool(_HEADER_RE.search(block))


def render_entry_record(record: EntryRecord) -> str:
    """Render an :class:`EntryRecord` as a Markdown block.

    Output matches the canonical heading style and field labels used by
    the bundled fixture and the legacy ``check-entry-record.mjs``
    validator (notably ``Review / Next state file`` with spaces).
    """
    lines = [
        "Implementation Entry Record:",
        f"- Current layer: {record.current_layer.value}",
        f"- Target: {record.target}",
        f"- Scope: {record.scope}",
        f"- Contract evidence: {record.contract_evidence}",
        f"- Readiness gate: {record.readiness_gate}",
        f"- Packetization: {record.packetization}",
        f"- Verification command: {record.verification_command}",
        f"- Review / Next state file: {record.review_next_state}",
        f"- Stop conditions: {record.stop_conditions}",
    ]
    return "\n".join(lines)


__all__ = ["parse_entry_record", "has_entry_record_header", "render_entry_record"]
