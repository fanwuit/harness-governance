"""Tests for the transition rules and engine."""

from __future__ import annotations

import pytest

from harness_governance.state_machine.engine import (
    StateMachineEngine,
    TransitionContext,
)
from harness_governance.state_machine.layers import HarnessLayer
from harness_governance.state_machine.transitions import (
    TRANSITION_RULES,
    rules_for_target,
)


def test_nine_rules_registered() -> None:
    assert len(TRANSITION_RULES) == 9
    codes = [rule.code for rule in TRANSITION_RULES]
    # Codes start with T1..T9.
    assert codes[0].startswith("T1-")
    assert codes[-1].startswith("T9-")


def test_rules_for_target_filters_by_layer() -> None:
    impl_rules = rules_for_target(HarnessLayer.IMPLEMENTATION)
    assert any(rule.code == "T1-READINESS-BEFORE-IMPLEMENTATION" for rule in impl_rules)
    assert any(rule.code == "T2-PROTOTYPE-EXCEPTION" for rule in impl_rules)
    assert any(rule.code == "T7-RETURN-TO-CONTRACT" for rule in impl_rules)


@pytest.fixture
def engine() -> StateMachineEngine:
    return StateMachineEngine()


def test_implementation_after_readiness_allowed(engine: StateMachineEngine) -> None:
    ctx = TransitionContext(
        from_layer=HarnessLayer.READINESS,
        to_layer=HarnessLayer.IMPLEMENTATION,
    )
    verdict = engine.evaluate(ctx)
    assert verdict.allowed
    assert verdict.violations == ()


def test_implementation_after_brief_blocked(engine: StateMachineEngine) -> None:
    ctx = TransitionContext(
        from_layer=HarnessLayer.BRIEF,
        to_layer=HarnessLayer.IMPLEMENTATION,
    )
    verdict = engine.evaluate(ctx)
    assert not verdict.allowed
    assert any(v.rule_code == "T1-READINESS-BEFORE-IMPLEMENTATION" for v in verdict.violations)


def test_prototype_exception_only_when_safe(engine: StateMachineEngine) -> None:
    safe_ctx = TransitionContext(
        from_layer=HarnessLayer.IDEA,
        to_layer=HarnessLayer.IMPLEMENTATION,
        is_prototype_explicit=True,
    )
    assert engine.evaluate(safe_ctx).allowed

    unsafe_ctx = TransitionContext(
        from_layer=HarnessLayer.IDEA,
        to_layer=HarnessLayer.IMPLEMENTATION,
        is_prototype_explicit=True,
        has_persistence_or_side_effect=True,
    )
    verdict = engine.evaluate(unsafe_ctx)
    assert not verdict.allowed
    assert any(v.rule_code == "T2-PROTOTYPE-EXCEPTION" for v in verdict.violations)


def test_contract_freezing_boundaries_requires_arch_or_adr(engine: StateMachineEngine) -> None:
    bad_ctx = TransitionContext(
        from_layer=HarnessLayer.BRAINSTORMING,
        to_layer=HarnessLayer.CONTRACT,
        has_persistence_or_side_effect=True,
    )
    assert not engine.evaluate(bad_ctx).allowed

    good_ctx = TransitionContext(
        from_layer=HarnessLayer.ARCHITECTURE,
        to_layer=HarnessLayer.CONTRACT,
        has_persistence_or_side_effect=True,
    )
    assert engine.evaluate(good_ctx).allowed


def test_adr_chat_only_with_long_lived_boundary_blocked(engine: StateMachineEngine) -> None:
    ctx = TransitionContext(
        from_layer=HarnessLayer.ARCHITECTURE,
        to_layer=HarnessLayer.ADR,
        is_chat_only_decision=True,
        touches_long_lived_boundary=True,
    )
    verdict = engine.evaluate(ctx)
    assert not verdict.allowed
    assert any(v.rule_code == "T4-ADR-MUST-BE-DURABLE" for v in verdict.violations)


def test_fact_discovery_note_appended(engine: StateMachineEngine) -> None:
    ctx = TransitionContext(
        from_layer=HarnessLayer.BRIEF,
        to_layer=HarnessLayer.ARCHITECTURE,
        material_unknown_present=True,
    )
    verdict = engine.evaluate(ctx)
    assert verdict.allowed
    assert any("fact-discovery" in note for note in verdict.notes)


def test_implementation_uncontracted_returns_to_contract(engine: StateMachineEngine) -> None:
    ctx = TransitionContext(
        from_layer=HarnessLayer.IMPLEMENTATION,
        to_layer=HarnessLayer.IMPLEMENTATION,
        implementation_reveals_uncontracted_behavior=True,
    )
    # We can model the return-to-contract as a same-layer self transition
    # plus the flag; the engine surfaces the violation regardless.
    verdict = engine.evaluate(ctx)
    assert not verdict.allowed
    assert any(v.rule_code == "T7-RETURN-TO-CONTRACT" for v in verdict.violations)


def test_review_next_required_on_finish(engine: StateMachineEngine) -> None:
    ctx = TransitionContext(
        from_layer=HarnessLayer.IMPLEMENTATION,
        to_layer=HarnessLayer.IMPLEMENTATION,
        work_finished_or_paused=True,
    )
    verdict = engine.evaluate(ctx)
    assert not verdict.allowed
    assert any(v.rule_code == "T9-REVIEW-NEXT-ON-FINISH" for v in verdict.violations)


def test_engine_lists_nine_rule_codes(engine: StateMachineEngine) -> None:
    codes = list(engine.all_rule_codes())
    assert len(codes) == 9