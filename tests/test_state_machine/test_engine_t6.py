"""Tests for rule T6 (contract-growth-control) enforcement in the state machine engine."""

from harness_governance.state_machine.engine import (
    StateMachineEngine,
    TransitionContext,
)
from harness_governance.state_machine.layers import HarnessLayer


def _evaluate(context: TransitionContext):
    """Helper: return the verdict from a fresh engine."""
    return StateMachineEngine().evaluate(context)


def test_t6_fires_when_contract_work_repeating():
    """T6 must fire when looping CONTRACT->CONTRACT with repeating flag set."""
    ctx = TransitionContext(
        from_layer=HarnessLayer.CONTRACT,
        to_layer=HarnessLayer.CONTRACT,
        contract_work_repeating=True,
    )
    verdict = _evaluate(ctx)
    codes = [v.rule_code for v in verdict.violations]
    assert "T6-CONTRACT-GROWTH-CONTROL" in codes


def test_t6_does_not_fire_when_not_repeating():
    """T6 must NOT fire when the repeating flag is False."""
    ctx = TransitionContext(
        from_layer=HarnessLayer.CONTRACT,
        to_layer=HarnessLayer.CONTRACT,
        contract_work_repeating=False,
    )
    verdict = _evaluate(ctx)
    codes = [v.rule_code for v in verdict.violations]
    assert "T6-CONTRACT-GROWTH-CONTROL" not in codes


def test_t6_does_not_fire_for_implementation_target():
    """T6 must NOT fire when to_layer is IMPLEMENTATION (not CONTRACT)."""
    ctx = TransitionContext(
        from_layer=HarnessLayer.CONTRACT,
        to_layer=HarnessLayer.IMPLEMENTATION,
        contract_work_repeating=True,
    )
    verdict = _evaluate(ctx)
    codes = [v.rule_code for v in verdict.violations]
    assert "T6-CONTRACT-GROWTH-CONTROL" not in codes


def test_t6_fires_from_readiness_to_contract():
    """T6 must fire when looping READINESS->CONTRACT with repeating flag."""
    ctx = TransitionContext(
        from_layer=HarnessLayer.READINESS,
        to_layer=HarnessLayer.CONTRACT,
        contract_work_repeating=True,
    )
    verdict = _evaluate(ctx)
    codes = [v.rule_code for v in verdict.violations]
    assert "T6-CONTRACT-GROWTH-CONTROL" in codes


def test_t6_fires_from_verification_to_contract():
    """T6 must fire when looping VERIFICATION->CONTRACT with repeating flag."""
    ctx = TransitionContext(
        from_layer=HarnessLayer.VERIFICATION,
        to_layer=HarnessLayer.CONTRACT,
        contract_work_repeating=True,
    )
    verdict = _evaluate(ctx)
    codes = [v.rule_code for v in verdict.violations]
    assert "T6-CONTRACT-GROWTH-CONTROL" in codes


def test_t6_does_not_fire_from_architecture_to_contract():
    """T6 must NOT fire when coming from ARCHITECTURE (a valid predecessor)."""
    ctx = TransitionContext(
        from_layer=HarnessLayer.ARCHITECTURE,
        to_layer=HarnessLayer.CONTRACT,
        contract_work_repeating=True,
    )
    verdict = _evaluate(ctx)
    codes = [v.rule_code for v in verdict.violations]
    assert "T6-CONTRACT-GROWTH-CONTROL" not in codes


def test_t6_all_rule_codes_includes_t6():
    """all_rule_codes() must include the T6 rule code."""
    engine = StateMachineEngine()
    assert "T6-CONTRACT-GROWTH-CONTROL" in engine.all_rule_codes()
