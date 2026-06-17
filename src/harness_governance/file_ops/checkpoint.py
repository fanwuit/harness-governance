"""Runner checkpoint file (``autonomous-ready-loop``)."""

from __future__ import annotations

from dataclasses import dataclass, fields
from pathlib import Path

from ._util import atomic_write_text


@dataclass(slots=True)
class Checkpoint:
    """In-memory representation of ``.harness/run-checkpoint.md``.

    The on-disk file is a Markdown document with section headings
    (``## Last Worker``, ``## Durable State Updated``, ``## Verification``,
    ``## Next Resume Source``, ``## Stop Reason``). This dataclass holds
    the parsed fields for reading; writing happens through
    :meth:`Checkpoint.dump`.
    """

    last_worker: str = ""
    durable_state_updated: str = ""
    verification: str = ""
    next_resume_source: str = ""
    stop_reason: str = ""

    @classmethod
    def load(cls, path: Path) -> "Checkpoint":
        """Parse a checkpoint file; missing file returns an empty record."""
        if not path.is_file():
            return cls()
        return cls.from_markdown(path.read_text(encoding="utf-8"))

    @classmethod
    def from_markdown(cls, text: str) -> "Checkpoint":
        # Known field names on the dataclass; unknown headings are ignored
        # rather than crashing cls(**fields) with TypeError.
        valid_field_names = {f.name for f in fields(cls)}
        field_defaults = {
            "last_worker": "",
            "durable_state_updated": "",
            "verification": "",
            "next_resume_source": "",
            "stop_reason": "",
        }
        current: str | None = None
        buffer: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith("## "):
                if current is not None:
                    field_defaults[current] = "\n".join(buffer).strip()
                candidate = _heading_to_field(stripped[3:])
                # Only track headings that map to a real dataclass field.
                current = candidate if candidate in valid_field_names else None
                buffer = []
            elif current is not None:
                buffer.append(line)
        if current is not None:
            field_defaults[current] = "\n".join(buffer).strip()
        return cls(**field_defaults)

    def dump(self, path: Path) -> None:
        """Write the checkpoint as Markdown to ``path``."""
        path.parent.mkdir(parents=True, exist_ok=True)
        body = "\n".join(
            [
                "# Harness Runner Checkpoint",
                "",
                "## Last Worker",
                "",
                self.last_worker or "-",
                "",
                "## Durable State Updated",
                "",
                self.durable_state_updated or "-",
                "",
                "## Verification",
                "",
                self.verification or "-",
                "",
                "## Next Resume Source",
                "",
                self.next_resume_source or "-",
                "",
                "## Stop Reason",
                "",
                self.stop_reason or "-",
                "",
            ]
        )
        atomic_write_text(path, body)


_HEADING_TO_FIELD = {
    "last worker": "last_worker",
    "durable state updated": "durable_state_updated",
    "verification": "verification",
    "next resume source": "next_resume_source",
    "stop reason": "stop_reason",
}


def _heading_to_field(heading: str) -> str:
    key = heading.strip().lower()
    return _HEADING_TO_FIELD.get(key, key.replace(" ", "_"))


__all__ = ["Checkpoint"]
