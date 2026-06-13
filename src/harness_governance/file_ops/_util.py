"""Internal helpers shared by file_ops modules."""

from __future__ import annotations

import re
from pathlib import Path


_SAFE_CHANGE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


def assert_inside(root: Path, target: Path) -> None:
    """Raise :class:`ValueError` if ``target`` is outside ``root``."""
    root_abs = root.resolve()
    target_abs = target.resolve()
    try:
        rel = target_abs.relative_to(root_abs)
    except ValueError as exc:
        raise ValueError(
            f"Refusing to operate outside project root {root_abs}: {target_abs}"
        ) from exc
    if rel.is_absolute() or ".." in rel.parts:
        raise ValueError(
            f"Refusing to operate outside project root {root_abs}: {target_abs}"
        )


def validate_change_id(change_id: str) -> str:
    """Validate that ``change_id`` is safe to use as a directory name."""
    if not change_id:
        raise ValueError("Change id must not be empty.")
    if change_id.lower() == "archive":
        raise ValueError("Change id 'archive' is reserved.")
    if not _SAFE_CHANGE_ID.match(change_id):
        raise ValueError(
            "Change id must match ^[A-Za-z0-9][A-Za-z0-9._-]*$ "
            f"(got: {change_id!r})"
        )
    return change_id