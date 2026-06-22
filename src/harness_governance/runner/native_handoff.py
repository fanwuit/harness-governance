"""Native subagent handoff lifecycle records.

Harness core prepares and validates native subagent handoff records, but
does not spawn platform agents.  The main agent/platform owns the actual
native spawn.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


REQUESTS_DIR = Path(".harness/subagent-requests")
TMP_DIR = Path(".harness/tmp")
LIFECYCLE_DIR = Path(".harness/native-handoffs")


@dataclass(slots=True)
class NativePaths:
    request_path: Path
    prompt_path: Path
    lifecycle_path: Path


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def new_request_id(role: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{role}-{stamp}-{uuid.uuid4().hex[:8]}"


def paths_for(
    project_root: Path,
    *,
    session_id: str,
    role: str,
    request_id: str,
) -> NativePaths:
    request_path = project_root / REQUESTS_DIR / session_id / f"{request_id}.json"
    prompt_path = project_root / TMP_DIR / f"{role}-prompt.md"
    lifecycle_path = project_root / LIFECYCLE_DIR / f"{session_id}.ndjson"
    return NativePaths(
        request_path=request_path,
        prompt_path=prompt_path,
        lifecycle_path=lifecycle_path,
    )


def _append_lifecycle(project_root: Path, session_id: str, record: dict) -> Path:
    path = project_root / LIFECYCLE_DIR / f"{session_id}.ndjson"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def write_request(
    project_root: Path,
    *,
    session_id: str,
    queue_id: str,
    request_id: str,
    role: str,
    required_tier: str,
    actual_tier: str,
    platform: str,
    adapter: str,
    model_label: str,
    prompt_text: str,
) -> dict:
    p = paths_for(
        project_root,
        session_id=session_id,
        role=role,
        request_id=request_id,
    )
    p.prompt_path.parent.mkdir(parents=True, exist_ok=True)
    p.prompt_path.write_text(prompt_text, encoding="utf-8")
    prompt_hash = sha256_text(prompt_text)
    payload = {
        "sessionId": session_id,
        "queueId": queue_id,
        "requestId": request_id,
        "role": role,
        "requiredTier": required_tier,
        "actualTier": actual_tier,
        "platform": platform,
        "adapter": adapter,
        "modelLabel": model_label,
        "promptPath": str(p.prompt_path.relative_to(project_root)),
        "promptSha256": prompt_hash,
        "status": "prepared",
        "preparedAt": datetime.now(timezone.utc).isoformat(),
    }
    p.request_path.parent.mkdir(parents=True, exist_ok=True)
    p.request_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    _append_lifecycle(project_root, session_id, {"event": "prepared", **payload})
    return payload


def load_request(project_root: Path, session_id: str, request_id: str) -> dict:
    path = project_root / REQUESTS_DIR / session_id / f"{request_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Native handoff request not found: {request_id}")
    return json.loads(path.read_text(encoding="utf-8"))


def append_spawn(
    project_root: Path,
    *,
    session_id: str,
    role: str,
    request_id: str,
    agent_id: str,
    status: str,
) -> dict:
    request = load_request(project_root, session_id, request_id)
    if request.get("role") != role:
        raise ValueError(
            f"request role {request.get('role')!r} does not match {role!r}"
        )
    if not agent_id:
        raise ValueError("agent-id is required")
    record = {
        "event": "spawned",
        "sessionId": session_id,
        "requestId": request_id,
        "role": role,
        "agentId": agent_id,
        "status": status,
        "recordedAt": datetime.now(timezone.utc).isoformat(),
    }
    _append_lifecycle(project_root, session_id, record)
    return record


def append_completion(
    project_root: Path,
    *,
    session_id: str,
    role: str,
    request_id: str,
    agent_id: str,
    verdict: str | None,
    verification_passed: bool,
    findings_count: int,
) -> dict:
    request = load_request(project_root, session_id, request_id)
    spawn = latest_spawn(project_root, session_id, request_id, agent_id)
    request_role = request.get("role")
    if request_role != role:
        raise ValueError(
            f"request role {request_role!r} does not match completion role {role!r}"
        )
    if spawn is None:
        raise FileNotFoundError(
            f"Native spawn record not found for request {request_id} and agent {agent_id}"
        )
    spawn_role = spawn.get("role")
    if spawn_role != role:
        raise ValueError(
            f"spawn role {spawn_role!r} does not match completion role {role!r}"
        )
    record = {
        "event": "completed",
        "sessionId": session_id,
        "requestId": request_id,
        "agentId": agent_id,
        "role": role,
        "requiredTier": request.get("requiredTier", ""),
        "actualTier": request.get("actualTier", ""),
        "platform": request.get("platform", ""),
        "adapter": request.get("adapter", ""),
        "modelLabel": request.get("modelLabel", ""),
        "promptSha256": request.get("promptSha256", ""),
        "verdict": verdict,
        "verificationPassed": verification_passed,
        "findingsCount": findings_count,
        "status": "completed",
        "completedAt": datetime.now(timezone.utc).isoformat(),
    }
    _append_lifecycle(project_root, session_id, record)
    return record


def lifecycle_records(project_root: Path, session_id: str) -> list[dict]:
    path = project_root / LIFECYCLE_DIR / f"{session_id}.ndjson"
    if not path.is_file():
        return []
    records: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            records.append(data)
    return records


def latest_spawn(
    project_root: Path,
    session_id: str,
    request_id: str,
    agent_id: str,
) -> dict | None:
    for record in reversed(lifecycle_records(project_root, session_id)):
        if (
            record.get("event") == "spawned"
            and record.get("requestId") == request_id
            and record.get("agentId") == agent_id
        ):
            return record
    return None


def latest_completion(project_root: Path, session_id: str, request_id: str) -> dict | None:
    for record in reversed(lifecycle_records(project_root, session_id)):
        if record.get("event") == "completed" and record.get("requestId") == request_id:
            return record
    return None
