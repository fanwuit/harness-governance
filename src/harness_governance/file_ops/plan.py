"""Planning carrier (``planning-with-files``) helpers.

Encapsulates the conventions from
``planning-with-files/scripts/{init-session.sh,attest-plan.sh,
check-complete.sh}``.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date
from importlib import resources
from pathlib import Path
from typing import Iterable

from ..models.schemas import PlanningSession
from ._util import assert_inside

_TEMPLATES_PACKAGE = "harness_governance.data.templates.planning"

# A phase line in task_plan.md is "## Phase N. Title" or "### Phase N. Title".
_PHASE_RE = re.compile(r"^#{2,4}\s*Phase\s+\d+\b", re.IGNORECASE | re.MULTILINE)
# "Status: complete" inside a phase block counts as done.
_PHASE_STATUS_RE = re.compile(r"^Status\s*:\s*(complete|done)\b", re.IGNORECASE | re.MULTILINE)


def plan_dir(project_root: Path, plan_id: str) -> Path:
    """Return the absolute path to a planning session directory."""
    return (project_root / ".planning" / plan_id).resolve()


def init_plan(
    project_root: Path,
    *,
    template: str = "default",
    slug: str | None = None,
    today: date | None = None,
) -> PlanningSession:
    """Create a new ``.planning/<id>/`` directory from templates."""
    today = today or date.today()
    plan_id = f"{today.isoformat()}-{slug or 'session'}"
    target = plan_dir(project_root, plan_id)
    assert_inside(project_root.resolve(), target)
    target.mkdir(parents=True, exist_ok=True)

    files = {
        "task_plan.md": _load_template(template, "task_plan.md"),
        "findings.md": _load_template(template, "findings.md"),
        "progress.md": _load_template(template, "progress.md"),
    }
    for name, body in files.items():
        (target / name).write_text(body, encoding="utf-8")

    # Pin ``.planning/.active_plan`` to this plan.
    active_file = project_root / ".planning" / ".active_plan"
    active_file.parent.mkdir(parents=True, exist_ok=True)
    active_file.write_text(plan_id + "\n", encoding="utf-8")

    return PlanningSession(
        plan_id=plan_id,
        plan_dir=target,
        task_plan_path=target / "task_plan.md",
        findings_path=target / "findings.md",
        progress_path=target / "progress.md",
        attested=False,
    )


def resolve_active_plan(project_root: Path) -> PlanningSession | None:
    """Return the active planning session, or ``None`` if none exists."""
    planning_root = project_root / ".planning"
    active_file = planning_root / ".active_plan"
    if active_file.is_file():
        plan_id = active_file.read_text(encoding="utf-8").strip()
        if plan_id:
            return _session_from_id(project_root, plan_id)

    # Fallback: newest ``.planning/<date>-<slug>/`` by mtime.
    if not planning_root.is_dir():
        return None
    candidates = [p for p in planning_root.iterdir() if p.is_dir()]
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return _session_from_id(project_root, candidates[0].name)


def set_active_plan(project_root: Path, plan_id: str) -> Path:
    """Pin ``.planning/.active_plan`` to ``plan_id``."""
    planning_root = project_root / ".planning"
    planning_root.mkdir(parents=True, exist_ok=True)
    active_file = planning_root / ".active_plan"
    active_file.write_text(plan_id + "\n", encoding="utf-8")
    return active_file


def attest_plan(project_root: Path, plan_id: str | None = None) -> str:
    """Write a SHA-256 attestation of the current ``task_plan.md``.

    Returns the hex digest. The attestation lives in
    ``.planning/<id>/.attestation``.
    """
    session = _resolve_session(project_root, plan_id)
    digest = hashlib.sha256(session.task_plan_path.read_bytes()).hexdigest()
    attestation = session.plan_dir / ".attestation"
    attestation.write_text(digest + "\n", encoding="utf-8")
    return digest


def is_plan_complete(project_root: Path, plan_id: str | None = None) -> bool:
    """Return ``True`` if every Phase block has ``Status: complete``."""
    session = _resolve_session(project_root, plan_id)
    text = session.task_plan_path.read_text(encoding="utf-8")
    phase_iter: Iterable[re.Match[str]] = list(_PHASE_RE.finditer(text))
    if not phase_iter:
        return False
    blocks = _split_into_phase_blocks(text, phase_iter)
    return all(bool(_PHASE_STATUS_RE.search(block)) for block in blocks)


def _split_into_phase_blocks(text: str, matches: Iterable[re.Match[str]]) -> list[str]:
    positions = [m.start() for m in matches] + [len(text)]
    return [text[positions[i]:positions[i + 1]] for i in range(len(positions) - 1)]


def _load_template(template: str, name: str) -> str:
    resource = resources.files(_TEMPLATES_PACKAGE).joinpath(name)
    if not resource.is_file():
        raise FileNotFoundError(f"Planning template not found: {name}")
    return resource.read_text(encoding="utf-8")


def _session_from_id(project_root: Path, plan_id: str) -> PlanningSession:
    directory = plan_dir(project_root, plan_id)
    attestation = directory / ".attestation"
    attested = False
    digest: str | None = None
    if attestation.is_file():
        attested = True
        digest = attestation.read_text(encoding="utf-8").strip() or None
    return PlanningSession(
        plan_id=plan_id,
        plan_dir=directory,
        task_plan_path=directory / "task_plan.md",
        findings_path=directory / "findings.md",
        progress_path=directory / "progress.md",
        attested=attested,
        attestation_sha256=digest,
    )


def _resolve_session(project_root: Path, plan_id: str | None) -> PlanningSession:
    if plan_id is None:
        session = resolve_active_plan(project_root)
        if session is None:
            raise FileNotFoundError("No active planning session. Run `harness plan init` first.")
        return session
    return _session_from_id(project_root, plan_id)


__all__ = [
    "init_plan",
    "resolve_active_plan",
    "set_active_plan",
    "attest_plan",
    "is_plan_complete",
]