"""Three-way classification of incoming requests.

The classification is the mechanical entry point of governed work.
The wording mirrors ``harness-engineering/SKILL.md`` § Entry Priority
so the rules can be cited verbatim in user-facing output.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Iterable

from .layers import HarnessLayer
from .rigor import RigorTier, resolve_rigor

logger = logging.getLogger("harness.classification")


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

# Work-action keywords that signal the task involves file modifications.
# When the description contains any of these, the classifier should NOT
# return Fast Path even when no explicit flags are set.
# Source: common engineering verbs in both English and Chinese.
WORK_ACTION_KEYWORDS: tuple[str, ...] = (
    # English
    "implement",
    "develop",
    "fix",
    "refactor",
    "rewrite",
    "build",
    "debug",
    "migrate",
    "redesign",
    "optimize",
    "integrate",
    "adapt",
    "align",
    # Chinese
    "开发",
    "实现",
    "修复",
    "重构",
    "对齐",
    "修改",
    "重写",
    "添加",
    "删除",
    "优化",
    "迁移",
    "适配",
    "集成",
    "部署",
    "调整",
)


class RoutingDecision:
    """Result of classifying an incoming request.

    Includes the resolved :class:`~.rigor.RigorTier` so downstream
    components (session creation, gate engine) know the governance
    depth without re-detecting.
    """

    __slots__ = ("path", "rationale", "current_layer", "primary_skill", "rigor_tier")

    def __init__(
        self,
        path: RoutingPath,
        rationale: str,
        current_layer: HarnessLayer | None = None,
        primary_skill: str | None = None,
        rigor_tier: RigorTier = RigorTier.STRICT,
    ) -> None:
        self.path = path
        self.rationale = rationale
        self.current_layer = current_layer
        self.primary_skill = primary_skill
        self.rigor_tier = rigor_tier

    def __repr__(self) -> str:
        return (
            f"RoutingDecision(path={self.path.value!r}, "
            f"layer={self.current_layer.value if self.current_layer else None!r}, "
            f"primary_skill={self.primary_skill!r}, "
            f"rigor={self.rigor_tier.value!r})"
        )

    def to_disclosure(self, companion_skills: Iterable[str] = ()) -> str:
        """Format the canonical governed-path disclosure block.

        The disclosure identifies the governance routing decision and any
        companion workflow skills that run alongside harness governance.
        """
        companions = ", ".join(companion_skills) if companion_skills else "none"
        local_line = (
            "Local governance: harness governed-start → layer advance → "
            "gate check (enforced pipeline)"
        )
        return (
            f"{local_line}\n"
            f"Companion workflow skills: {companions}\n"
            "Routing decision: harness-governance owns entry routing; "
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
    rigor: str | None = None,
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
    rigor:
        Optional explicit rigor tier override. When None (default),
        auto-detected from *description* keywords.

    Rules
    -----
    * Fast path: no file changes, no durable artifacts (pure Q&A,
      read-only lookup, plan/advice with no implementation).
    * Trivial safe change: low-risk, single target, no public
      contract impact, clear verification.
    * Governed path: everything else.
    """
    resolved_rigor = resolve_rigor(rigor, description)
    description_lc = description.lower()

    mentions_work = _mentions_work_action_keyword(description_lc)

    if not has_file_changes and not is_public_contract and not has_external_side_effect:
        if not is_unclear_or_high_risk and not mentions_work:
            logger.info("classified as fast-path")
            logger.debug(
                "fast-path flags: file_changes=%s public=%s external=%s unclear=%s work_kw=%s",
                has_file_changes, is_public_contract, has_external_side_effect, is_unclear_or_high_risk, mentions_work,
            )
            return RoutingDecision(
                path=RoutingPath.FAST_PATH,
                rationale=(
                    "No file changes, no public contract impact, no external "
                    "side effects, and risk is bounded; treat as fast path."
                ),
                rigor_tier=resolved_rigor,
            )

    if (
        has_file_changes
        and not is_public_contract
        and not has_external_side_effect
        and not is_unclear_or_high_risk
        and not _mentions_public_contract_keyword(description_lc)
        and not mentions_work
    ):
        logger.info("classified as trivial-safe-change")
        return RoutingDecision(
            path=RoutingPath.TRIVIAL_SAFE_CHANGE,
            rationale=(
                "Low-risk single-target edit with clear verification; "
                "no public contract, schema, dependency, security, "
                "persistence, network, deployment, or build impact."
            ),
            rigor_tier=resolved_rigor,
        )

    logger.info("classified as governed-path")
    logger.debug(
        "governed-path flags: file_changes=%s public=%s external=%s unclear=%s keyword=%s work_kw=%s",
        has_file_changes, is_public_contract, has_external_side_effect,
        is_unclear_or_high_risk, _mentions_public_contract_keyword(description_lc), mentions_work,
    )
    return RoutingDecision(
        path=RoutingPath.GOVERNED_PATH,
        rationale=_governed_rationale(
            has_file_changes=has_file_changes,
            is_public_contract=is_public_contract,
            has_external_side_effect=has_external_side_effect,
            is_unclear_or_high_risk=is_unclear_or_high_risk,
            mentions_public_keyword=_mentions_public_contract_keyword(description_lc),
            mentions_work_keyword=mentions_work,
        ),
        current_layer=HarnessLayer.INTAKE_ORIENTATION,
        primary_skill="harness-engineering",
        rigor_tier=resolved_rigor,
    )


def _mentions_public_contract_keyword(description_lc: str) -> bool:
    return any(keyword in description_lc for keyword in PUBLIC_CONTRACT_KEYWORDS)


def _mentions_work_action_keyword(description_lc: str) -> bool:
    return any(keyword in description_lc for keyword in WORK_ACTION_KEYWORDS)


def _governed_rationale(
    *,
    has_file_changes: bool,
    is_public_contract: bool,
    has_external_side_effect: bool,
    is_unclear_or_high_risk: bool,
    mentions_public_keyword: bool,
    mentions_work_keyword: bool = False,
) -> str:
    reasons: list[str] = []
    if is_public_contract or mentions_public_keyword:
        reasons.append("touches a public contract surface")
    if has_external_side_effect:
        reasons.append("produces external side effects or persisted data")
    if is_unclear_or_high_risk:
        reasons.append("scope, risk, or requirements are unclear")
    if mentions_work_keyword and not reasons:
        reasons.append("description implies file modifications")
    if has_file_changes and not reasons:
        reasons.append("requires multi-layer governance")
    return "Governed path: " + "; ".join(reasons) + "."