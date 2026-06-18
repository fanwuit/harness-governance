"""Three-way classification of incoming requests.

The classification is the mechanical entry point of governed work.
The wording mirrors ``harness-engineering/SKILL.md`` § Entry Priority
so the rules can be cited verbatim in user-facing output.
"""

from __future__ import annotations

import logging
import re
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

# Edit-intent keywords signal that the request is asking us to change
# project state when paired with a file/project target. They should not
# automatically force the governed path; low-risk single-file/docs edits
# can still be trivial-safe-change.
EDIT_INTENT_KEYWORDS: tuple[str, ...] = (
    # English
    "update",
    "sync",
    "clean up",
    "mark",
    "document",
    "complete",
    "finish",
    "improve",
    "remediate",
    "work through",
    "carry out",
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
    "更新",
    "同步",
    "整理",
    "清理",
    "补充",
    "标记",
    "收口",
    "完成",
    "改进",
    "整改",
    "做完",
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

# Governed keywords identify work that should stay in the governed path
# even if no explicit flags are passed.
GOVERNED_WORK_KEYWORDS: tuple[str, ...] = (
    "implement",
    "develop",
    "fix",
    "refactor",
    "rewrite",
    "debug",
    "migrate",
    "redesign",
    "integrate",
    "classifier",
    "classification",
    "cli",
    "gate",
    "layer",
    "init",
    "governed-start",
    "test",
    "tests",
    "pytest",
    "multi-file",
    "multiple files",
    "开发",
    "实现",
    "修复",
    "重构",
    "重写",
    "迁移",
    "集成",
    "分类器",
    "分类",
    "命令",
    "门控",
    "测试",
    "多文件",
    "多项",
)

LOW_RISK_MAINTENANCE_KEYWORDS: tuple[str, ...] = (
    "readme",
    "quickstart",
    "upgrade.md",
    "docs",
    "documentation",
    "document",
    "comment",
    "comments",
    "typo",
    "changelog",
    "文档",
    "文件",
    "说明",
    "注释",
    "错别字",
)

PROJECT_TARGET_KEYWORDS: tuple[str, ...] = (
    "readme",
    "quickstart",
    "upgrade.md",
    "changelog",
    "docs",
    "src/",
    "tests/",
    "cli",
    "classifier",
    "classification",
    "gate",
    "layer",
    "init",
    "governed-start",
    "测试",
    "文档",
    "文件",
    "分类器",
    "门控",
    "命令",
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

    mentions_edit_intent = _mentions_edit_intent(description_lc)
    mentions_project_target = _mentions_file_or_project_target(description_lc)
    mentions_governed_work = _mentions_governed_work_keyword(description_lc)
    mentions_multi_item = _mentions_multi_item_work(description_lc)
    mentions_low_risk_maintenance = _mentions_low_risk_maintenance(description_lc)
    inferred_file_changes = (
        has_file_changes
        or (mentions_edit_intent and mentions_project_target)
        or (mentions_edit_intent and mentions_governed_work)
        or (mentions_edit_intent and mentions_multi_item)
    )

    # --- STRICT keyword gate: prevents fast-path / trivial misroute ---
    # When the description contains STRICT_DETECTION_KEYWORDS (platform,
    # saas, from scratch, microservice, …), the task is inherently not
    # fast-path or trivial regardless of what flags the caller passed.
    # This guards against agents that omit --files/--external.
    mentions_strict = _mentions_strict_keyword(description_lc)
    if mentions_strict:
        if (
            not has_file_changes
            or not is_public_contract
            or not has_external_side_effect
        ):
            logger.info(
                "STRICT keyword overrides missing flags: file_changes=%s public=%s external=%s",
                has_file_changes,
                is_public_contract,
                has_external_side_effect,
            )
        inferred_file_changes = True
        is_public_contract = True

    if (
        not inferred_file_changes
        and not is_public_contract
        and not has_external_side_effect
    ):
        if not is_unclear_or_high_risk:
            logger.info("classified as fast-path")
            logger.debug(
                "fast-path flags: file_changes=%s public=%s external=%s unclear=%s edit_intent=%s target=%s governed_kw=%s",
                inferred_file_changes,
                is_public_contract,
                has_external_side_effect,
                is_unclear_or_high_risk,
                mentions_edit_intent,
                mentions_project_target,
                mentions_governed_work,
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
        inferred_file_changes
        and not is_public_contract
        and not has_external_side_effect
        and not is_unclear_or_high_risk
        and not _mentions_public_contract_keyword(description_lc)
        and not (mentions_governed_work and not mentions_low_risk_maintenance)
        and not mentions_multi_item
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
        "governed-path flags: file_changes=%s public=%s external=%s unclear=%s keyword=%s edit_intent=%s target=%s governed_kw=%s multi_item=%s",
        inferred_file_changes,
        is_public_contract,
        has_external_side_effect,
        is_unclear_or_high_risk,
        _mentions_public_contract_keyword(description_lc),
        mentions_edit_intent,
        mentions_project_target,
        mentions_governed_work,
        mentions_multi_item,
    )
    return RoutingDecision(
        path=RoutingPath.GOVERNED_PATH,
        rationale=_governed_rationale(
            has_file_changes=inferred_file_changes,
            is_public_contract=is_public_contract,
            has_external_side_effect=has_external_side_effect,
            is_unclear_or_high_risk=is_unclear_or_high_risk,
            mentions_public_keyword=_mentions_public_contract_keyword(description_lc),
            mentions_governed_work=mentions_governed_work,
            mentions_multi_item=mentions_multi_item,
        ),
        current_layer=HarnessLayer.INTAKE_ORIENTATION,
        primary_skill="harness-engineering",
        rigor_tier=resolved_rigor,
    )


def _mentions_public_contract_keyword(description_lc: str) -> bool:
    return any(keyword in description_lc for keyword in PUBLIC_CONTRACT_KEYWORDS)


def _mentions_edit_intent(description_lc: str) -> bool:
    return any(keyword in description_lc for keyword in EDIT_INTENT_KEYWORDS)


def _mentions_governed_work_keyword(description_lc: str) -> bool:
    return any(keyword in description_lc for keyword in GOVERNED_WORK_KEYWORDS)


def _mentions_file_or_project_target(description_lc: str) -> bool:
    if any(keyword in description_lc for keyword in PROJECT_TARGET_KEYWORDS):
        return True
    if re.search(
        r"[\w.-]+\.(?:md|py|toml|json|yaml|yml|txt|rst|mdc)\b", description_lc
    ):
        return True
    if re.search(
        r"(?:^|\s)(?:src|tests|docs|\.harness|\.github|\.claude)[\\/]", description_lc
    ):
        return True
    return False


def _mentions_low_risk_maintenance(description_lc: str) -> bool:
    return any(keyword in description_lc for keyword in LOW_RISK_MAINTENANCE_KEYWORDS)


def _mentions_multi_item_work(description_lc: str) -> bool:
    return bool(
        re.search(r"\b\d+\s*-\s*\d+\b", description_lc)
        or re.search(r"\bp\d+\b", description_lc)
        or re.search(r"\d+\s*项", description_lc)
    )


def _mentions_strict_keyword(description_lc: str) -> bool:
    """Return True if the description contains any STRICT_DETECTION_KEYWORDS."""
    from .rigor import STRICT_DETECTION_KEYWORDS

    return any(
        keyword.lower() in description_lc for keyword in STRICT_DETECTION_KEYWORDS
    )


def _governed_rationale(
    *,
    has_file_changes: bool,
    is_public_contract: bool,
    has_external_side_effect: bool,
    is_unclear_or_high_risk: bool,
    mentions_public_keyword: bool,
    mentions_governed_work: bool = False,
    mentions_multi_item: bool = False,
) -> str:
    reasons: list[str] = []
    if is_public_contract or mentions_public_keyword:
        reasons.append("touches a public contract surface")
    if has_external_side_effect:
        reasons.append("produces external side effects or persisted data")
    if is_unclear_or_high_risk:
        reasons.append("scope, risk, or requirements are unclear")
    if mentions_governed_work and not reasons:
        reasons.append("description implies governed file modifications")
    if mentions_multi_item and not reasons:
        reasons.append("description implies multi-item project work")
    if has_file_changes and not reasons:
        reasons.append("description implies file modifications")
    return "Governed path: " + "; ".join(reasons) + "."
