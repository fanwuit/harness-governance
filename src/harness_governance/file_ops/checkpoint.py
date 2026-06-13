"""Runner checkpoint file (``autonomous-ready-loop``)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


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
        fields = {
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
                    fields[current] = "\n".join(buffer).strip()
                current = _heading_to_field(stripped[3:])
                buffer = []
            elif current is not None:
                buffer.append(line)
        if current is not None:
            fields[current] = "\n".join(buffer).strip()
        return cls(**fields)

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
        path.write_text(body, encoding="utf-8")


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