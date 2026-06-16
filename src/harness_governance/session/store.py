"""File-system operations for governance session files.

Sessions live under ``.harness/sessions/`` (configurable via
:data:`~harness_governance.config.defaults.DEFAULT_SESSIONS_DIR`).
Each session is a single JSON file named ``<session_id>.json``.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from ..config.defaults import DEFAULT_SESSIONS_DIR
from ..logging_setup import get_logger
from .state import SessionState

logger = get_logger("session.store")

# ---------------------------------------------------------------------------
# Session-ID generation
# ---------------------------------------------------------------------------

_SLUG_RE = re.compile(r"[^a-z0-9]+")
_MAX_SLUG_LEN = 40


def generate_session_id(description: str) -> str:
    """Build a human-readable session ID: ``YYYYMMDD-<slug>``.

    The slug is derived from the description by lower-casing, stripping
    non-alphanumeric characters, and truncating to 40 chars.
    """
    now = datetime.now(timezone.utc)
    slug = _SLUG_RE.sub("-", description.lower()).strip("-")
    slug = slug[:_MAX_SLUG_LEN].rstrip("-")
    if not slug:
        slug = "session"
    return f"{now:%Y%m%d}-{slug}"


def _sessions_dir(project_root: Path) -> Path:
    return project_root / DEFAULT_SESSIONS_DIR


def _session_path(project_root: Path, session_id: str) -> Path:
    return _sessions_dir(project_root) / f"{session_id}.json"


def _make_unique(project_root: Path, base_id: str) -> str:
    """Append ``-N`` suffix when *base_id* already exists on disk."""
    candidate = base_id
    counter = 2
    while _session_path(project_root, candidate).exists():
        candidate = f"{base_id}-{counter}"
        counter += 1
    return candidate


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


def create_session(
    project_root: Path,
    state: SessionState,
) -> Path:
    """Write *state* to ``.harness/sessions/<id>.json`` and return the path."""
    target = _session_path(project_root, state.session_id)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        state.model_dump_json(indent=2),
        encoding="utf-8",
    )
    logger.info("session created: %s", target)
    return target


def load_session(project_root: Path, session_id: str) -> SessionState:
    """Read and deserialize a session file.

    Raises :class:`FileNotFoundError` when the file does not exist.
    """
    target = _session_path(project_root, session_id)
    if not target.is_file():
        raise FileNotFoundError(f"Session file not found: {target}")
    raw = json.loads(target.read_text(encoding="utf-8"))
    return SessionState.model_validate(raw)


def save_session(project_root: Path, state: SessionState) -> None:
    """Overwrite the session file with the current *state*."""
    target = _session_path(project_root, state.session_id)
    target.write_text(
        state.model_dump_json(indent=2),
        encoding="utf-8",
    )
    logger.info("session saved: %s", target)


def find_active_session(project_root: Path) -> SessionState | None:
    """Return the most recently created active session, or ``None``."""
    sessions_dir = _sessions_dir(project_root)
    if not sessions_dir.is_dir():
        return None
    candidates: list[SessionState] = []
    for path in sorted(sessions_dir.glob("*.json"), reverse=True):
        try:
            state = load_session(project_root, path.stem)
        except (FileNotFoundError, json.JSONDecodeError):
            continue
        if state.status == "active":
            candidates.append(state)
    if not candidates:
        return None
    # Most recently created first (reverse sort on filename ≈ reverse time).
    return candidates[0]


def list_sessions(project_root: Path) -> list[SessionState]:
    """Return all sessions (active and closed), newest first."""
    sessions_dir = _sessions_dir(project_root)
    if not sessions_dir.is_dir():
        return []
    results: list[SessionState] = []
    for path in sorted(sessions_dir.glob("*.json"), reverse=True):
        try:
            results.append(load_session(project_root, path.stem))
        except (FileNotFoundError, json.JSONDecodeError):
            continue
    return results


__all__ = [
    "create_session",
    "find_active_session",
    "generate_session_id",
    "list_sessions",
    "load_session",
    "save_session",
]
