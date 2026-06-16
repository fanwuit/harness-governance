"""Rigor tier classification for task governance depth.

The rigor tier controls how many layers are required and how many
author questions must be answered per layer before advancing.

Default: STRICT (all 12 layers, all questions required).
"""

from __future__ import annotations

import logging
from enum import Enum

logger = logging.getLogger("harness.rigor")


class RigorTier(str, Enum):
    """Governance depth tier.

    LIGHT:   6 core layers, 1 question per layer (~10-15 rounds)
    STANDARD: 12 layers with flexibility, half questions (~20-30 rounds)
    STRICT:  12 layers enforced, all questions required (~40-50 rounds)
    """

    LIGHT = "light"
    STANDARD = "standard"
    STRICT = "strict"


# Keywords that force STRICT tier when found in a task description.
# Both English and Chinese keywords are included.
STRICT_DETECTION_KEYWORDS: tuple[str, ...] = (
    # Chinese — large scope indicators
    "平台",
    "从零",
    "从头",
    "整套",
    "系统架构",
    "系统设计",
    "系统重构",
    "架构重构",
    "架构变更",
    "架构设计",
    "微服务",
    "分布式",
    "数据迁移",
    # English — large scope indicators
    "platform",
    "saas",
    "build from scratch",
    "from scratch",
    "system architecture",
    "architecture redesign",
    "architecture change",
    "full system",
    "monolith",
    "microservice",
    "distributed system",
    "data migration",
    "greenfield",
    "rewrite",
    "overhaul",
    # High-risk domain indicators
    "payment",
    "billing",
    "authentication system",
    "authorization system",
    "compliance",
    "audit trail",
    "multi-tenant",
    "auth system",
)

# Keywords that suggest LIGHT tier (small, isolated changes).
LIGHT_DETECTION_KEYWORDS: tuple[str, ...] = (
    "typo",
    "spelling",
    "readme",
    "comment",
    "formatting",
    "lint",
    "style fix",
    "minor fix",
    "trivial",
    "one-line",
    "config tweak",
    "bump version",
    "version bump",
    "错别字",
    "拼写",
    "格式化",
    "小修",
    "微小",
)


def detect_rigor(description: str) -> RigorTier:
    """Auto-detect the appropriate rigor tier from a task description.

    Scanning order:
    1. STRICT keywords → STRICT
    2. LIGHT keywords → LIGHT
    3. Default → STRICT (fail-safe: always default strict)
    """
    description_lc = description.lower()

    for keyword in STRICT_DETECTION_KEYWORDS:
        if keyword.lower() in description_lc:
            logger.debug("rigor auto-detected as STRICT (keyword: %r)", keyword)
            return RigorTier.STRICT

    for keyword in LIGHT_DETECTION_KEYWORDS:
        if keyword.lower() in description_lc:
            logger.debug("rigor auto-detected as LIGHT (keyword: %r)", keyword)
            return RigorTier.LIGHT

    # Default to STRICT — the safe default per user requirement.
    logger.debug("rigor defaulting to STRICT")
    return RigorTier.STRICT


def resolve_rigor(user_override: str | None, description: str) -> RigorTier:
    """Resolve the rigor tier, preferring user override over auto-detection.

    Parameters
    ----------
    user_override:
        Explicit tier from ``--rigor`` flag, or None.
    description:
        Task description for auto-detection when no override is given.

    Returns
    -------
    RigorTier
        The resolved tier.

    Raises
    ------
    ValueError
        When *user_override* is not a valid RigorTier value.
    """
    if user_override is not None:
        try:
            tier = RigorTier(user_override.lower().strip())
            logger.info("rigor tier overridden: %s", tier.value)
            return tier
        except ValueError:
            valid = ", ".join(t.value for t in RigorTier)
            raise ValueError(
                f"Invalid rigor tier: {user_override!r}. Use: {valid}."
            ) from None

    tier = detect_rigor(description)
    logger.info("rigor tier resolved: %s", tier.value)
    return tier


__all__ = [
    "RigorTier",
    "STRICT_DETECTION_KEYWORDS",
    "LIGHT_DETECTION_KEYWORDS",
    "detect_rigor",
    "resolve_rigor",
]
