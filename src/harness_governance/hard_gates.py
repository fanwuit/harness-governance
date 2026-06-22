"""Mechanical governance hard gates for queued governed work."""

from __future__ import annotations

import fnmatch
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .config import load_config
from .file_ops.queue import read_queue
from .models.schemas import QueueItem
from .session import load_session


def is_trivial_queue_item(item: QueueItem) -> bool:
    text = " ".join(
        part
        for part in (item.change_kind or "", item.raw)
        if part
    ).lower()
    return "trivial-safe-change" in text or "trivial" in text


def queue_item_key(item: QueueItem) -> str:
    return item.id or item.session_id or item.change_id or "queue item"


def active_queue_item_for_session(
    project_root: Path,
    session_id: str,
) -> QueueItem | None:
    try:
        cfg = load_config(project_root)
    except Exception:
        return None
    for item in read_queue(cfg.queue_file):
        if item.session_id == session_id and item.status in {"active", "ready", "done"}:
            return item
    return None


def render_records_path(project_root: Path, session_id: str) -> Path:
    return project_root / ".harness" / "render-records" / f"{session_id}.ndjson"


def record_render(
    project_root: Path,
    *,
    session_id: str,
    queue_id: str,
    role: str,
) -> Path:
    path = render_records_path(project_root, session_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "sessionId": session_id,
        "queueId": queue_id,
        "role": role,
        "renderedAt": datetime.now(timezone.utc).isoformat(),
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def rendered_roles(project_root: Path, session_id: str, queue_id: str) -> set[str]:
    path = render_records_path(project_root, session_id)
    if not path.is_file():
        return set()
    roles: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("sessionId") != session_id:
            continue
        if record.get("queueId") != queue_id:
            continue
        role = record.get("role")
        if isinstance(role, str) and role:
            roles.add(role)
    return roles


def missing_render_roles(
    project_root: Path,
    item: QueueItem,
    session_id: str,
) -> list[str]:
    if not item.role_plan:
        return []
    queue_id = queue_item_key(item)
    roles = rendered_roles(project_root, session_id, queue_id)
    return [role for role in item.role_plan if role not in roles]


def implementation_gate_failures(project_root: Path, session_id: str) -> list[str]:
    item = active_queue_item_for_session(project_root, session_id)
    if item is None:
        return []

    failures: list[str] = []
    is_implementation = (
        (item.layer is not None and item.layer.value == "implementation")
        or item.role == "implementer"
    )
    if is_implementation:
        if not item.test_plan:
            failures.append("Implementation queue item must declare TestPlan.")
        if not (item.failing_test_evidence or item.tdd_not_applicable):
            failures.append(
                "Implementation queue item must declare FailingTestEvidence "
                "or TddNotApplicable."
            )

    missing_roles = missing_render_roles(project_root, item, session_id)
    if missing_roles:
        failures.append(
            "Missing runner render records for role plan: "
            + ", ".join(missing_roles)
        )

    outside = changed_files_outside_owner_allowlist(
        project_root,
        item.owner_files,
        baseline=_session_git_status_baseline(project_root, session_id),
    )
    if outside:
        failures.append(
            "Changed files outside owner allowlist: " + ", ".join(outside)
        )

    return failures


def changed_files_outside_owner_allowlist(
    project_root: Path,
    owner_files: Iterable[str],
    *,
    baseline: Iterable[str] = (),
) -> list[str]:
    allowlist = tuple(path.strip() for path in owner_files if path.strip())
    if not allowlist:
        return []
    baseline_paths = {
        path.replace("\\", "/").strip()
        for path in baseline
        if path.strip()
    }
    changed = [
        path
        for path in git_changed_files(project_root)
        if path not in baseline_paths
    ]
    return [path for path in changed if not _path_allowed(path, allowlist)]


def git_changed_files(project_root: Path) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=False,
        )
    except (FileNotFoundError, OSError):
        return []
    if result.returncode != 0:
        return []
    changed: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.rsplit(" -> ", 1)[1]
        changed.append(path.replace("\\", "/"))
    return changed


def _session_git_status_baseline(project_root: Path, session_id: str) -> tuple[str, ...]:
    try:
        session = load_session(project_root, session_id)
    except (FileNotFoundError, OSError, ValueError):
        return ()
    return tuple(session.git_status_baseline)


def _path_allowed(path: str, allowlist: tuple[str, ...]) -> bool:
    normalized = path.replace("\\", "/")
    for pattern in allowlist:
        pat = pattern.replace("\\", "/")
        if normalized == pat:
            return True
        if pat.endswith("/") and normalized.startswith(pat):
            return True
        if fnmatch.fnmatch(normalized, pat):
            return True
    return False


def finish_gate_failures(
    project_root: Path,
    session_id: str,
    evidence: Iterable[str],
) -> list[str]:
    item = active_queue_item_for_session(project_root, session_id)
    if item is None:
        return []

    failures: list[str] = []
    if not item.role_plan and not is_trivial_queue_item(item):
        failures.append("Finish requires queue item RolePlan evidence.")
        return failures

    missing_roles = missing_render_roles(project_root, item, session_id)
    if missing_roles:
        failures.append(
            "Missing role evidence/render records: " + ", ".join(missing_roles)
        )

    evidence_text = "\n".join(evidence).lower()
    if "targeted" not in evidence_text and "targeted checks" not in evidence_text:
        failures.append("Finish evidence must include targeted checks.")

    outside = changed_files_outside_owner_allowlist(
        project_root,
        item.owner_files,
        baseline=_session_git_status_baseline(project_root, session_id),
    )
    if outside:
        failures.append(
            "Changed files outside owner allowlist: " + ", ".join(outside)
        )
    return failures
