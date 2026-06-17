"""Internal helpers shared by file_ops modules."""

from __future__ import annotations

import os
import re
import tempfile
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


def _strip_bom(content: str) -> str:
    """Strip a leading UTF-8 BOM (U+FEFF) from *content* if present.

    ``encoding="utf-8"`` (without ``-sig``) does NOT strip a BOM on read
    and does NOT emit one on write; a BOM ingested from a packaged
    resource or an existing on-disk file would otherwise propagate
    through every read->write round-trip.  All project writes funnel
    through :func:`write_text_no_bom` / :func:`atomic_write_text`, both
    of which call this, so BOM is guaranteed never to reach disk.
    """
    if content.startswith("\ufeff"):
        content = content[1:]
    return content


def write_text_no_bom(path: Path, content: str, encoding: str = "utf-8") -> None:
    """Write *content* to *path* as UTF-8 without a BOM.

    This is the project-wide invariant: every text file written by
    ``harness init`` or any subsequent command must be UTF-8 no-BOM.
    ``encoding`` defaults to ``"utf-8"`` (never ``utf-8-sig``) and any
    leading U+FEFF is stripped first.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_strip_bom(content), encoding=encoding)


def atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    """Write *content* to *path* atomically.

    Writes to a sibling temp file and renames it into place.  On POSIX
    the rename is atomic; on Windows ``os.replace`` is also atomic for
    same-filesystem renames.  Ensures a crash mid-write never leaves a
    truncated file at *path*.

    Always strips a leading UTF-8 BOM (U+FEFF) so the no-BOM invariant
    holds even when the caller ingested a BOM from an external source.
    """
    content = _strip_bom(content)
    path.parent.mkdir(parents=True, exist_ok=True)
    # NamedTemporaryFile so the temp handle is unique per call even under
    # concurrent writers; keep it in the same directory so the rename
    # stays on the same filesystem.
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding=encoding,
        dir=str(path.parent),
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as tmp:
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    try:
        os.replace(tmp_path, path)
    except OSError:
        try:
            tmp_path.unlink()
        except OSError:
            pass
        raise


def validate_change_id(change_id: str) -> str:
    """Validate that ``change_id`` is safe to use as a directory name."""
    if not change_id:
        raise ValueError(bilingual("packet.empty_id"))
    if change_id.lower() == "archive":
        raise ValueError(bilingual("packet.reserved_archive"))
    if not _SAFE_CHANGE_ID.match(change_id):
        raise ValueError(bilingual("packet.invalid_id", value=change_id))
    return change_id