"""Three-way classification of incoming requests.

The classification is the mechanical entry point of governed work.
The wording mirrors ``harness-engineering/SKILL.md`` § Entry Priority
so the rules can be cited verbatim in user-facing output.
"""

from __future__ import annotations

from enum import Enum
from typing import Iterable

from .layers import HarnessLayer


class RoutingPath(str, Enum):
    """The three routing paths for an incoming request."""

    FAST_PATH = "fast-path"
    TRIVIAL_SAFE_CHANGE = "trivial-safe-change"
    GOVERNED_PATH = "governed-path"


# Public-contract surface categories that force a governed path.
# Source: harness-engineering/SKILL.md § Entry Priority.
PUBLIC_CONTRACT_KEYWORDS: tuple[str, ...] = (
    "public api",
    "public contract",
    "schema",
    "dependency",
    "build",
    "deployment",
    "security",
    "permission",
    "authentication",
    "authorization",
    "persistence",
    "network",
    "external api",
    "billing",
    "payment",
)


class RoutingDecision:
    """Result of classifying an incoming request."""

    __slots__ = ("path", "rationale", "current_layer", "primary_skill")

    def __init__(
        self,
        path: RoutingPath,
        rationale: str,
        current_layer: HarnessLayer | None = None,
        primary_skill: str | None = None,
    ) -> None:
        self.path = path
        self.rationale = rationale
        self.current_layer = current_layer
        self.primary_skill = primary_skill

    def __repr__(self) -> str:
        return (
            f"RoutingDecision(path={self.path.value!r}, "
            f"layer={self.current_layer.value if self.current_layer else None!r}, "
            f"primary_skill={self.primary_skill!r})"
        )

    def to_disclosure(self, companion_skills: Iterable[str] = ()) -> str:
        """Format the canonical governed-path disclosure block.

        The wording matches ``harness-engineering/SKILL.md`` § Required
        disclosure for governed path.
        """
        companions = ", ".join(companion_skills) if companion_skills else "none"
        base_local = ["skill-use-transparency", "harness-engineering"]
        # Avoid duplicating ``harness-engineering`` when it is also the
        # primary skill (the canonical entry router is always listed).
        if self.primary_skill and self.primary_skill not in base_local:
            base_local.append(self.primary_skill)
        local_line = "Local governance skills: " + ", ".join(base_local)
        return (
            f"{local_line}\n"
            f"Companion workflow skills: {companions}\n"
            "Routing decision: harness-engineering owns governed entry routing; "
            "fast path and trivial safe change remain local lightweight paths, "
            "and companion workflows run only after harness selects the current "
            "layer."
        )


def classify(
    description: str,
    *,
    has_file_changes: bool,
    is_public_contract: bool,
    has_external_side_effect: bool,
    is_unclear_or_high_risk: bool,
) -> RoutingDecision:
    """Classify a request into Fast/Trivial/Governed.

    Parameters
    ----------
    description:
        Human-readable description of the task.
    has_file_changes:
        Whether the task produces file changes or durable artifacts.
    is_public_contract:
        Whether the task touches a public contract surface (API,
        schema, dependency, persistence, network, build, deployment,
        security, auth, billing, …).
    has_external_side_effect:
        Whether the task produces persisted data or external side
        effects (network calls, deployments, billing, etc.).
    is_unclear_or_high_risk:
        Whether scope, risk, or requirements are unclear.

    Rules
    -----
    * Fast path: no file changes, no durable artifacts (pure Q&A,
      read-only lookup, plan/advice with no implementation).
    * Trivial safe change: low-risk, single target, no public
      contract impact, clear verification.
    * Governed path: everything else.
    """
    description_lc = description.lower()

    if not has_file_changes and not is_public_contract and not has_external_side_effect:
        if not is_unclear_or_high_risk:
            return RoutingDecision(
                path=RoutingPath.FAST_PATH,
                rationale=(
                    "No file changes, no public contract impact, no external "
                    "side effects, and risk is bounded; treat as fast path."
                ),
            )

    if (
        has_file_changes
        and not is_public_contract
        and not has_external_side_effect
        and not is_unclear_or_high_risk
        and not _mentions_public_contract_keyword(description_lc)
    ):
        return RoutingDecision(
            path=RoutingPath.TRIVIAL_SAFE_CHANGE,
            rationale=(
                "Low-risk single-target edit with clear verification; "
                "no public contract, schema, dependency, security, "
                "persistence, network, deployment, or build impact."
            ),
        )

    return RoutingDecision(
        path=RoutingPath.GOVERNED_PATH,
        rationale=_governed_rationale(
            has_file_changes=has_file_changes,
            is_public_contract=is_public_contract,
            has_external_side_effect=has_external_side_effect,
            is_unclear_or_high_risk=is_unclear_or_high_risk,
            mentions_public_keyword=_mentions_public_contract_keyword(description_lc),
        ),
        current_layer=HarnessLayer.INTAKE_ORIENTATION,
        primary_skill="harness-engineering",
    )


def _mentions_public_contract_keyword(description_lc: str) -> bool:
    return any(keyword in description_lc for keyword in PUBLIC_CONTRACT_KEYWORDS)


def _governed_rationale(
    *,
    has_file_changes: bool,
    is_public_contract: bool,
    has_external_side_effect: bool,
    is_unclear_or_high_risk: bool,
    mentions_public_keyword: bool,
) -> str:
    reasons: list[str] = []
    if is_public_contract or mentions_public_keyword:
        reasons.append("touches a public contract surface")
    if has_external_side_effect:
        reasons.append("produces external side effects or persisted data")
    if is_unclear_or_high_risk:
        reasons.append("scope, risk, or requirements are unclear")
    if has_file_changes and not reasons:
        reasons.append("requires multi-layer governance")
    return "Governed path: " + "; ".join(reasons) + "."