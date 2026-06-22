"""Optional project-level queue policy hook.

Derived projects may place ``.harness/queue-policy.json`` in the repo
root to declare extra queue rules. The harness core reads the file and
applies its rules mechanically; projects do not need to fork the core
to get stricter queue gating.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class QueuePolicy:
    role_required_by_layer: dict[str, str] = field(default_factory=dict)
    role_required_by_change_kind: dict[str, str] = field(default_factory=dict)
    verification_presets: dict[str, str] = field(default_factory=dict)
    child_gate_ordering: dict[str, tuple[str, ...]] = field(default_factory=dict)
    forbidden_owner_overlap: tuple[tuple[str, ...], ...] = ()


def load_queue_policy(project_root: Path) -> QueuePolicy:
    """Load ``.harness/queue-policy.json`` if present, else defaults."""
    path = project_root / ".harness" / "queue-policy.json"
    if not path.is_file():
        return QueuePolicy()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid queue policy file: {path}") from exc

    def _mapping(name: str) -> dict[str, str]:
        raw = data.get(name, {})
        if not isinstance(raw, dict):
            raise ValueError(f"{name} must be an object")
        return {str(k).strip().lower(): str(v).strip().lower() for k, v in raw.items()}

    def _ordering() -> dict[str, tuple[str, ...]]:
        raw = data.get("child_gate_ordering", {})
        if not isinstance(raw, dict):
            raise ValueError("child_gate_ordering must be an object")
        result: dict[str, tuple[str, ...]] = {}
        for gate_id, children in raw.items():
            if not isinstance(children, list):
                raise ValueError("child_gate_ordering values must be arrays")
            result[str(gate_id).strip().lower()] = tuple(
                str(child).strip().lower() for child in children if str(child).strip()
            )
        return result

    def _overlap() -> tuple[tuple[str, ...], ...]:
        raw = data.get("forbidden_owner_overlap", [])
        if not isinstance(raw, list):
            raise ValueError("forbidden_owner_overlap must be an array")
        result: list[tuple[str, ...]] = []
        for entry in raw:
            if not isinstance(entry, list):
                raise ValueError("forbidden_owner_overlap entries must be arrays")
            normalized = tuple(
                str(path).strip() for path in entry if str(path).strip()
            )
            if normalized:
                result.append(normalized)
        return tuple(result)

    return QueuePolicy(
        role_required_by_layer=_mapping("role_required_by_layer"),
        role_required_by_change_kind=_mapping("role_required_by_change_kind"),
        verification_presets=_mapping("verification_presets"),
        child_gate_ordering=_ordering(),
        forbidden_owner_overlap=_overlap(),
    )


__all__ = ["QueuePolicy", "load_queue_policy"]

