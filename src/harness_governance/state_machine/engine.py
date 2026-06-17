"""State-machine engine.

The engine enforces the 10 transition rules (T1-T10) from
:mod:`.transitions` against proposed layer transitions. It does not
execute work — it only validates that a transition is legal given the
declared context.

The engine is intentionally side-effect free: callers collect
:class:`Violation` objects and decide what to do (abort, escalate,
warn, etc.). This makes it straightforward to unit-test all rule
permutations without touching the filesystem.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Iterable

from .layers import HarnessLayer, layer_index
from .transitions import TRANSITION_RULES

logger = logging.getLogger("harness.engine")


@dataclass(frozen=True, slots=True)
class TransitionContext:
    """Inputs the engine uses to evaluate a transition.

    Attributes
    ----------
    from_layer:
        The layer the work is leaving.
    to_layer:
        The layer the work is entering.
    is_prototype_explicit:
        Whether the user explicitly scoped the work as a throwaway
        prototype (allows skipping ``readiness`` per rule T1).
    has_persistence_or_side_effect:
        Whether the work produces persisted data or external side
        effects (disables the prototype exception per rule T2).
    is_chat_only_decision:
        Whether the proposed ADR/decision is captured only in chat
        rather than a durable artifact (violates rule T4 when long-lived
        boundaries are involved).
    touches_long_lived_boundary:
        Whether the work touches long-lived boundaries, persistence,
        deployment, ownership, or public contracts. Required for rule
        T4 to apply.
    material_unknown_present:
        Whether a material unknown was discovered at the source layer
        (forces ``fact-discovery`` per rule T5).
    implementation_reveals_uncontracted_behavior:
        Whether implementation surfaced behavior that was not covered
        by an existing contract (forces return-to-contract per rule T7).
    verification_failed:
        Whether the verification step failed (forces return-to-owner
        per rule T8).
    work_finished_or_paused:
        Whether the work is at a stopping point (forces review-next
        per rule T9).
    contract_work_repeating:
        Whether contract/check/readiness work is repeating without
        implementation progress (triggers rule T6).
    scope_drift_detected:
        Whether implementation changes exceed the declared scope boundary
        (triggers rule T10 — return to contract).
    """

    from_layer: HarnessLayer
    to_layer: HarnessLayer
    is_prototype_explicit: bool = False
    has_persistence_or_side_effect: bool = False
    is_chat_only_decision: bool = False
    touches_long_lived_boundary: bool = False
    material_unknown_present: bool = False
    implementation_reveals_uncontracted_behavior: bool = False
    verification_failed: bool = False
    work_finished_or_paused: bool = False
    contract_work_repeating: bool = False
    scope_drift_detected: bool = False


@dataclass(frozen=True, slots=True)
class Violation:
    """A single transition rule that the context violates."""

    rule_code: str
    rule_title: str
    message: str

    def format(self) -> str:
        return f"[{self.rule_code}] {self.rule_title}: {self.message}"


@dataclass(slots=True)
class TransitionVerdict:
    """Outcome of :meth:`StateMachineEngine.evaluate`."""

    allowed: bool
    violations: tuple[Violation, ...] = field(default_factory=tuple)
    notes: tuple[str, ...] = field(default_factory=tuple)

    def __bool__(self) -> bool:  # pragma: no cover - trivial
        return self.allowed


class StateMachineEngine:
    """Validates proposed transitions against the 10-rule policy (T1-T10)."""

    def evaluate(self, context: TransitionContext) -> TransitionVerdict:
        """Return a verdict describing whether ``context`` is allowed."""
        logger.debug(
            "evaluating transition: %s -> %s",
            context.from_layer.value,
            context.to_layer.value,
        )
        violations: list[Violation] = []
        notes: list[str] = []

        # Rule T1/T2: implementation before readiness.
        if context.to_layer is HarnessLayer.IMPLEMENTATION:
            if (
                context.from_layer is not HarnessLayer.READINESS
                and context.from_layer is not HarnessLayer.IMPLEMENTATION
            ):
                if not context.is_prototype_explicit:
                    violations.append(
                        Violation(
                            rule_code="T1-READINESS-BEFORE-IMPLEMENTATION",
                            rule_title="Do not enter implementation before readiness",
                            message=(
                                f"Transition {context.from_layer.value} -> "
                                f"{context.to_layer.value} skips the readiness "
                                "layer. Mark the work as an explicit prototype "
                                "to use the exception."
                            ),
                        )
                    )
                elif context.has_persistence_or_side_effect:
                    violations.append(
                        Violation(
                            rule_code="T2-PROTOTYPE-EXCEPTION",
                            rule_title="'Move fast' is not a prototype request",
                            message=(
                                "Prototype exception does not apply because "
                                "the work has persisted data, external side "
                                "effects, public contracts, or production "
                                "runtime behavior."
                            ),
                        )
                    )

        # Rule T3: contract that freezes boundaries must follow architecture/ADR.
        if context.to_layer is HarnessLayer.CONTRACT and (
            context.has_persistence_or_side_effect
            or context.touches_long_lived_boundary
        ):
            allowed_predecessors = {
                HarnessLayer.ARCHITECTURE,
                HarnessLayer.ADR,
                HarnessLayer.CONTRACT,
            }
            if context.from_layer not in allowed_predecessors:
                violations.append(
                    Violation(
                        rule_code="T3-ARCH-ADR-BEFORE-CONTRACT",
                        rule_title="Architecture/ADR before contract that freezes boundaries",
                        message=(
                            f"Transition {context.from_layer.value} -> contract "
                            "freezes ownership, deployment, persistence, or "
                            "boundary decisions. Architecture or ADR must be "
                            "entered first."
                        ),
                    )
                )

        # Rule T4: ADR must be durable and reviewable.
        if (
            context.to_layer is HarnessLayer.ADR
            and context.is_chat_only_decision
            and context.touches_long_lived_boundary
        ):
            violations.append(
                Violation(
                    rule_code="T4-ADR-MUST-BE-DURABLE",
                    rule_title="ADR state must be durable and reviewable",
                    message=(
                        "Decision state for long-lived boundaries, persistence, "
                        "deployment, ownership, or public contracts cannot be "
                        "captured in chat only. Write a durable ADR."
                    ),
                )
            )

        # Rule T5: material unknown forces fact-discovery.
        if (
            context.material_unknown_present
            and context.to_layer is not HarnessLayer.FACT_DISCOVERY
            and context.to_layer is not context.from_layer
            and layer_index(context.to_layer) > layer_index(context.from_layer)
        ):
            violations.append(
                Violation(
                    rule_code="T5-FACT-DISCOVERY-INTERRUPT",
                    rule_title="Material unknown requires fact-discovery before forward progress",
                    message=(
                        f"Transition {context.from_layer.value} -> "
                        f"{context.to_layer.value} moves forward while a material "
                        "unknown is unresolved. Enter fact-discovery first."
                    ),
                )
            )

        # Rule T6: contract work repeating without implementation progress.
        if (
            context.contract_work_repeating
            and context.to_layer is HarnessLayer.CONTRACT
            and context.from_layer
            in (
                HarnessLayer.CONTRACT,
                HarnessLayer.READINESS,
                HarnessLayer.VERIFICATION,
            )
        ):
            violations.append(
                Violation(
                    rule_code="T6-CONTRACT-GROWTH-CONTROL",
                    rule_title="Use contract-growth-control when contract work stalls",
                    message=(
                        "Contract/check/readiness work is repeating without "
                        "implementation progress. Use contract-growth-control "
                        "to diagnose the stall before continuing contract work."
                    ),
                )
            )

        # Rule T7: implementation reveals uncontracted behavior -> return to contract.
        if (
            context.implementation_reveals_uncontracted_behavior
            and context.to_layer is HarnessLayer.IMPLEMENTATION
        ):
            violations.append(
                Violation(
                    rule_code="T7-RETURN-TO-CONTRACT",
                    rule_title="Return to contract when implementation reveals uncontracted behavior",
                    message=(
                        "Implementation surfaced uncontracted behavior; return "
                        "to the contract layer before expanding product behavior."
                    ),
                )
            )

        # Rule T8: verification failure -> return to the layer that owns the cause.
        #
        # The engine has no per-failure provenance, so we approximate "lowest
        # layer that owns the failure" as the upstream layers where contracts,
        # readiness, facts, and intake live.  A verification failure may
        # legitimately return to any of these; transitioning anywhere else
        # (e.g. straight back to IMPLEMENTATION to retry, or forward to
        # REVIEW_NEXT) does not address the root cause and is blocked.
        if context.verification_failed and context.to_layer is not context.from_layer:
            _T8_OWNER_LAYERS = {
                HarnessLayer.CONTRACT,
                HarnessLayer.READINESS,
                HarnessLayer.FACT_DISCOVERY,
                HarnessLayer.INTAKE_ORIENTATION,
            }
            if context.to_layer not in _T8_OWNER_LAYERS:
                violations.append(
                    Violation(
                        rule_code="T8-VERIFICATION-FAILURE-OWNER",
                        rule_title="Return to lowest layer that owns the failure",
                        message=(
                            f"Verification failure recorded but transition "
                            f"{context.from_layer.value} -> "
                            f"{context.to_layer.value} does not address the cause. "
                            "Return to the lowest layer that owns the failure first "
                            "(contract / readiness / fact-discovery / intake)."
                        ),
                    )
                )

        # Rule T9: work finishing/pausing -> review-next.
        if (
            context.work_finished_or_paused
            and context.to_layer is not HarnessLayer.REVIEW_NEXT
        ):
            violations.append(
                Violation(
                    rule_code="T9-REVIEW-NEXT-ON-FINISH",
                    rule_title="Always enter review-next when work finishes or pauses",
                    message=(
                        "Work is finishing or pausing but the target layer is "
                        f"{context.to_layer.value}; review-next is required."
                    ),
                )
            )

        # Rule T10: scope drift detected -> return to contract.
        if (
            context.scope_drift_detected
            and context.to_layer is HarnessLayer.IMPLEMENTATION
        ):
            violations.append(
                Violation(
                    rule_code="T10-DRIFT-CONTRACT-BOUNDARY",
                    rule_title="Scope drift must return to contract before expansion",
                    message=(
                        "Implementation changes exceed the declared scope boundary. "
                        "Return to the contract layer to expand the contract before "
                        "continuing implementation."
                    ),
                )
            )

        allowed = not violations
        if violations:
            logger.info(
                "transition %s -> %s BLOCKED: %d violation(s): %s",
                context.from_layer.value,
                context.to_layer.value,
                len(violations),
                ", ".join(v.rule_code for v in violations),
            )
        else:
            logger.debug(
                "transition %s -> %s allowed",
                context.from_layer.value,
                context.to_layer.value,
            )
        return TransitionVerdict(
            allowed=allowed,
            violations=tuple(violations),
            notes=tuple(notes),
        )

    def all_rule_codes(self) -> Iterable[str]:
        """Return every registered rule code, in declaration order."""
        return tuple(rule.code for rule in TRANSITION_RULES)
