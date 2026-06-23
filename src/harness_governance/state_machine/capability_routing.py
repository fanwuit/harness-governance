"""Capability-tier subagent routing: role policy, adapter resolution, provenance.

This is the core of the P0 Capability-Tiered Subagent Routing feature.
It separates *what* capability a subagent needs (policy) from *how* it
is executed (adapter), keeping harness core platform-neutral.

Adapter/model candidates are declared in each agent directory's
``tiers.json`` — harness core discovers them at runtime and never
encodes model rankings itself.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from ..models.schemas import (
    CapabilityTier,
    HarnessConfig,
    ProvenanceRecord,
    ROLE_CAPABILITY_POLICY,
)
from .agent_declarations import (
    AgentCapabilityDeclaration,
    discover_declarations,
    resolve_adapter_from_declarations as _resolve_adapter_from_decls,
)


def resolve_required_tier(
    role: str, config: HarnessConfig | None = None
) -> CapabilityTier:
    """Return the minimum required :class:`CapabilityTier` for *role*.

    Checks project config overrides first, then the built-in
    ``ROLE_CAPABILITY_POLICY``.  Unknown roles default to ``STRONG``.
    """
    if config:
        for override in config.role_capability_overrides:
            if override.role == role:
                return override.required_tier

    return ROLE_CAPABILITY_POLICY.get(role, CapabilityTier.STRONG)


def verifier_required_for_tier(tier: CapabilityTier) -> bool:
    """Return ``True`` when invocations at *tier* need independent verification.

    ``EXECUTION`` and ``MECHANICAL`` tiers cannot self-verify or close out;
    they require an independent ``STRONG`` verifier.
    """
    return tier in (CapabilityTier.EXECUTION, CapabilityTier.MECHANICAL)


def resolve_adapter(
    role: str,
    tier: CapabilityTier,
    project_root: Path | None = None,
    declarations: Sequence[AgentCapabilityDeclaration] | None = None,
) -> dict[str, str] | None:
    """Resolve the adapter and model label for a (role, tier) pair.

    Checks agent directory declarations first, then returns ``None``
    if no declaration matches (platform default will be used).
    """
    if declarations is None and project_root is not None:
        declarations = discover_declarations(project_root)
    if declarations:
        result = _resolve_adapter_from_decls(role, tier.value, declarations)
        if result:
            return result
    return None


def build_provenance(
    *,
    role: str,
    required_tier: CapabilityTier,
    actual_tier: CapabilityTier | None = None,
    platform: str = "",
    model_label: str = "",
    adapter: str = "",
    owner_files: tuple[str, ...] = (),
    changed_files: tuple[str, ...] = (),
) -> ProvenanceRecord:
    """Build a :class:`ProvenanceRecord` with default verifier requirement."""
    actual = actual_tier or required_tier
    return ProvenanceRecord(
        role=role,
        required_tier=required_tier,
        actual_tier=actual,
        platform=platform,
        model_label=model_label,
        adapter=adapter,
        owner_files=owner_files,
        changed_files=changed_files,
        verifier_required=verifier_required_for_tier(actual),
    )


def role_policy_summary(config: HarnessConfig | None = None) -> list[dict[str, str]]:
    """Return a human-readable summary of the resolved role policy.

    Each entry contains ``role``, ``required_tier``, and
    ``verifier_required``.
    """
    all_roles = sorted(
        set(ROLE_CAPABILITY_POLICY.keys())
        | {o.role for o in (config.role_capability_overrides if config else ())}
    )
    summary: list[dict[str, str]] = []
    for role in all_roles:
        tier = resolve_required_tier(role, config).value
        needs_verifier = str(verifier_required_for_tier(CapabilityTier(tier)))
        summary.append(
            {"role": role, "required_tier": tier, "verifier_required": needs_verifier}
        )
    return summary


__all__ = [
    "resolve_required_tier",
    "verifier_required_for_tier",
    "resolve_adapter",
    "build_provenance",
    "role_policy_summary",
]
