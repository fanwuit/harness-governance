"""Agent capability-tier declaration discovery.

Each agent platform places a ``tiers.json`` in its config directory
(e.g. ``.claude/tiers.json``) to declare what models/adapters it can
provide for each role at each capability tier.

Harness core discovers these declarations at runtime by scanning
well-known agent directories.  It never encodes model rankings itself.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Sequence

from ..models.schemas import (
    AGENT_CONFIG_DIRS,
    AGENT_TIERS_FILE,
    AgentCapabilityDeclaration,
)


def discover_declarations(
    project_root: Path,
    *,
    extra_dirs: Sequence[Path] = (),
) -> list[AgentCapabilityDeclaration]:
    """Scan well-known agent directories for ``tiers.json`` files.

    Returns a list of :class:`AgentCapabilityDeclaration` objects in
    priority order (most specific platform directory first).
    """
    declarations: list[AgentCapabilityDeclaration] = []
    seen: set[Path] = set()

    dirs = list(extra_dirs) + list(AGENT_CONFIG_DIRS)
    for rel_dir in dirs:
        path = (project_root / rel_dir).resolve()
        if path in seen:
            continue
        seen.add(path)
        tiers_file = path / AGENT_TIERS_FILE
        if not tiers_file.is_file():
            continue
        try:
            raw = json.loads(tiers_file.read_text(encoding="utf-8"))
            declarations.append(AgentCapabilityDeclaration.model_validate(raw))
        except (json.JSONDecodeError, Exception) as exc:
            import logging

            logging.getLogger("harness.agent_declarations").warning(
                "Failed to load %s: %s", tiers_file, exc
            )
            continue

    return declarations


def resolve_adapter_from_declarations(
    role: str,
    required_tier: str,
    declarations: Sequence[AgentCapabilityDeclaration],
) -> dict[str, str] | None:
    """Find the first adapter declaration matching (role, tier).

    Returns a dict with ``adapter`` and ``model_label`` keys, or ``None``
    if no declaration matches.
    """
    for decl in declarations:
        for route in decl.adapters:
            if route.role == role and route.required_tier.value == required_tier:
                return {
                    "adapter": route.adapter,
                    "model_label": route.model_label,
                    "platform": decl.platform,
                }
    return None


def all_adapters_from_declarations(
    declarations: Sequence[AgentCapabilityDeclaration],
) -> dict[str, list[dict[str, str]]]:
    """Group all declared adapters by role for reporting."""
    by_role: dict[str, list[dict[str, str]]] = {}
    for decl in declarations:
        for route in decl.adapters:
            by_role.setdefault(route.role, []).append(
                {
                    "required_tier": route.required_tier.value,
                    "adapter": route.adapter,
                    "model_label": route.model_label,
                    "platform": decl.platform,
                }
            )
    return by_role


__all__ = [
    "discover_declarations",
    "resolve_adapter_from_declarations",
    "all_adapters_from_declarations",
]
