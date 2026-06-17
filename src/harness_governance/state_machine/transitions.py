"""The 9 canonical transition rules.

Rules are encoded as :class:`TransitionRule` dataclasses carrying a
machine-readable ``code`` (so violations can be referenced in error
messages), the affected layer pair, and a human-readable rationale.
The rule text matches ``harness-engineering/references/layer-progression.md``
§ Transition Rules verbatim so that quoting the source remains
authoritative.
"""

from __future__ import annotations

from dataclasses import dataclass

from .layers import HarnessLayer


@dataclass(frozen=True, slots=True)
class TransitionRule:
    """One entry of the 9-rule transition policy."""

    code: str
    title: str
    rule: str
    target_layer: HarnessLayer
    source: str = "harness-engineering/references/layer-progression.md § Transition Rules"


# The 9 rules, in canonical order. ``target_layer`` is the layer the
# rule constrains entry into; ``requires_layer`` (if set) is the
# layer that must be reached first.
TRANSITION_RULES: tuple[TransitionRule, ...] = (
    TransitionRule(
        code="T1-READINESS-BEFORE-IMPLEMENTATION",
        title="Do not enter implementation before readiness",
        rule=(
            "Do not enter `implementation` before `readiness` unless the "
            "user explicitly asks for a throwaway prototype or the target "
            "project already supplies equivalent readiness rules."
        ),
        target_layer=HarnessLayer.IMPLEMENTATION,
    ),
    TransitionRule(
        code="T2-PROTOTYPE-EXCEPTION",
        title="'Move fast' is not a prototype request",
        rule=(
            "A request to move fast, implement now, or finish the real "
            "integration is not a throwaway prototype request. Persisted "
            "data, external side effects, public contracts, or production "
            "runtime behavior exclude the prototype exception unless the "
            "user explicitly scopes the work as isolated throwaway "
            "exploration."
        ),
        target_layer=HarnessLayer.IMPLEMENTATION,
    ),
    TransitionRule(
        code="T3-ARCH-ADR-BEFORE-CONTRACT",
        title="Architecture/ADR before contract that freezes boundaries",
        rule=(
            "Do not enter `contract` before `architecture` or `adr` when "
            "the contract would freeze ownership, deployment, persistence, "
            "or boundary decisions."
        ),
        target_layer=HarnessLayer.CONTRACT,
    ),
    TransitionRule(
        code="T4-ADR-MUST-BE-DURABLE",
        title="ADR state must be durable and reviewable",
        rule=(
            "ADR or decision state must be durable and reviewable. "
            "Chat-only agreement does not satisfy a layer exit condition "
            "when long-lived boundaries, persistence, deployment, "
            "ownership, or public contracts are involved."
        ),
        target_layer=HarnessLayer.ADR,
    ),
    TransitionRule(
        code="T5-FACT-DISCOVERY-INTERRUPT",
        title="Material unknown requires fact-discovery",
        rule=(
            "When a material unknown appears, move to `fact-discovery`, "
            "record evidence, then return to the blocked layer."
        ),
        target_layer=HarnessLayer.FACT_DISCOVERY,
    ),
    TransitionRule(
        code="T6-CONTRACT-GROWTH-CONTROL",
        title="Use contract-growth-control when contract work stalls",
        rule=(
            "When contract/check/readiness work repeats without "
            "implementation progress, use `contract-growth-control`."
        ),
        target_layer=HarnessLayer.CONTRACT,
    ),
    TransitionRule(
        code="T7-RETURN-TO-CONTRACT",
        title="Return to contract when implementation reveals uncontracted behavior",
        rule=(
            "When implementation reveals uncontracted behavior, return to "
            "`contract` before expanding product behavior."
        ),
        target_layer=HarnessLayer.IMPLEMENTATION,
    ),
    TransitionRule(
        code="T8-VERIFICATION-FAILURE-OWNER",
        title="Return to lowest layer that owns the failure",
        rule=(
            "When verification fails, return to the lowest layer that "
            "owns the failure cause."
        ),
        target_layer=HarnessLayer.VERIFICATION,
    ),
    TransitionRule(
        code="T9-REVIEW-NEXT-ON-FINISH",
        title="Always enter review-next when work finishes or pauses",
        rule=(
            "When work finishes or pauses, always enter `review-next` "
            "to record evidence, risks, and next ready layer."
        ),
        target_layer=HarnessLayer.REVIEW_NEXT,
    ),
    TransitionRule(
        code="T10-DRIFT-CONTRACT-BOUNDARY",
        title="Scope drift must return to contract before expansion",
        rule=(
            "When implementation touches files or behaviour beyond the "
            "approved scope boundary, return to `contract` to expand the "
            "contract before continuing implementation."
        ),
        target_layer=HarnessLayer.IMPLEMENTATION,
    ),
)


def rules_for_target(layer: HarnessLayer) -> tuple[TransitionRule, ...]:
    """Return all rules whose ``target_layer`` matches ``layer``."""
    return tuple(rule for rule in TRANSITION_RULES if rule.target_layer is layer)