"""Internal helpers shared by file_ops modules."""

from __future__ import annotations

import re
from pathlib import Path

from ..messages import bilingual


_SAFE_CHANGE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def assert_inside(root: Path, target: Path) -> None:
    """Raise :class:`ValueError` if ``target`` is outside ``root``."""
    root_abs = root.resolve()
    target_abs = target.resolve()
    try:
        rel = target_abs.relative_to(root_abs)
    except ValueError as exc:
        raise ValueError(
            bilingual("packet.refuse_outside_repo", root=root_abs, target=target_abs)
        ) from exc
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError(
            bilingual("packet.refuse_outside_repo", root=root_abs, target=target_abs)
        )


def validate_change_id(change_id: str) -> str:
    """Validate that ``change_id`` is safe to use as a directory name."""
    if not change_id:
        raise ValueError(bilingual("packet.empty_id"))
    if change_id.lower() == "archive":
        raise ValueError(bilingual("packet.reserved_archive"))
    if not _SAFE_CHANGE_ID.match(change_id):
        raise ValueError(bilingual("packet.invalid_id", value=change_id))
    return change_id