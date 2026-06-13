"""Public re-exports for the state_machine subpackage."""

from .classification import (
    PUBLIC_CONTRACT_KEYWORDS,
    RoutingDecision,
    RoutingPath,
    classify,
)
from .engine import StateMachineEngine, TransitionContext, TransitionVerdict, Violation
from .layers import (
    HarnessLayer,
    LAYER_MAP,
    canonical_progression,
    layer_index,
    resolve_layer,
)
from .transitions import TRANSITION_RULES, TransitionRule, rules_for_target

__all__ = [
    "HarnessLayer",
    "LAYER_MAP",
    "canonical_progression",
    "layer_index",
    "resolve_layer",
    "TransitionRule",
    "TRANSITION_RULES",
    "rules_for_target",
    "StateMachineEngine",
    "TransitionContext",
    "TransitionVerdict",
    "Violation",
    "RoutingPath",
    "RoutingDecision",
    "PUBLIC_CONTRACT_KEYWORDS",
    "classify",
]