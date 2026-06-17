"""Tests for the Fast/Trivial/Governed classification."""

from __future__ import annotations

from harness_governance.state_machine.classification import (
    RoutingPath,
    classify,
)
from harness_governance.state_machine.rigor import RigorTier


def test_pure_question_is_fast_path() -> None:
    decision = classify(
        "What does the harness-engineering skill do?",
        has_file_changes=False,
        is_public_contract=False,
        has_external_side_effect=False,
        is_unclear_or_high_risk=False,
    )
    assert decision.path is RoutingPath.FAST_PATH


def test_renaming_a_local_var_is_trivial_safe() -> None:
    decision = classify(
        "Rename local variable `foo` to `bar` in src/foo.py",
        has_file_changes=True,
        is_public_contract=False,
        has_external_side_effect=False,
        is_unclear_or_high_risk=False,
    )
    assert decision.path is RoutingPath.TRIVIAL_SAFE_CHANGE


def test_public_api_change_is_governed() -> None:
    decision = classify(
        "Expose new public API endpoint /v2/widgets",
        has_file_changes=True,
        is_public_contract=True,
        has_external_side_effect=False,
        is_unclear_or_high_risk=False,
    )
    assert decision.path is RoutingPath.GOVERNED_PATH
    assert decision.current_layer is not None


def test_persistence_side_effect_is_governed() -> None:
    decision = classify(
        "Add row to users table when user clicks subscribe",
        has_file_changes=True,
        is_public_contract=False,
        has_external_side_effect=True,
        is_unclear_or_high_risk=False,
    )
    assert decision.path is RoutingPath.GOVERNED_PATH


def test_unclear_task_is_governed() -> None:
    decision = classify(
        "Make the dashboard faster, somehow",
        has_file_changes=False,
        is_public_contract=False,
        has_external_side_effect=False,
        is_unclear_or_high_risk=True,
    )
    assert decision.path is RoutingPath.GOVERNED_PATH


def test_description_with_public_contract_keyword_is_governed() -> None:
    decision = classify(
        "Refactor the dependency injection layer",
        has_file_changes=True,
        is_public_contract=False,
        has_external_side_effect=False,
        is_unclear_or_high_risk=False,
    )
    assert decision.path is RoutingPath.GOVERNED_PATH


def test_disclosure_block_mentions_cli_commands() -> None:
    decision = classify(
        "Build a new microservice",
        has_file_changes=True,
        is_public_contract=True,
        has_external_side_effect=True,
        is_unclear_or_high_risk=False,
    )
    text = decision.to_disclosure(("superpowers:subagent-driven-development",))
    assert "harness governed-start" in text
    assert "layer advance" in text
    assert "gate check" in text
    assert "superpowers:subagent-driven-development" in text


def test_disclosure_mentions_harness_governance() -> None:
    """The disclosure should reference harness-governance as the entry router."""
    decision = classify(
        "Refactor the API boundary",
        has_file_changes=True,
        is_public_contract=True,
        has_external_side_effect=False,
        is_unclear_or_high_risk=False,
    )
    assert decision.primary_skill == "harness-engineering"  # internal label unchanged
    text = decision.to_disclosure()
    assert "harness-governance owns entry routing" in text


# ---------------------------------------------------------------------------
# Work action keywords (description-based file-change inference)
# ---------------------------------------------------------------------------


def test_chinese_develop_keyword_upgrades_from_fast_path() -> None:
    """Description with '开发' should NOT be fast path even without flags."""
    decision = classify(
        "这个前端设计完全没有按照原型来，需要重新对齐原型，进行开发",
        has_file_changes=False,
        is_public_contract=False,
        has_external_side_effect=False,
        is_unclear_or_high_risk=False,
    )
    assert decision.path is RoutingPath.GOVERNED_PATH
    assert "implies file modifications" in decision.rationale


def test_chinese_fix_keyword_upgrades_from_fast_path() -> None:
    """Description with '修复' should NOT be fast path even without flags."""
    decision = classify(
        "修复登录页面的样式问题",
        has_file_changes=False,
        is_public_contract=False,
        has_external_side_effect=False,
        is_unclear_or_high_risk=False,
    )
    assert decision.path is RoutingPath.GOVERNED_PATH


def test_chinese_refactor_keyword_upgrades_from_trivial() -> None:
    """Description with '重构' + has_file_changes should NOT be trivial."""
    decision = classify(
        "重构用户模块的代码结构",
        has_file_changes=True,
        is_public_contract=False,
        has_external_side_effect=False,
        is_unclear_or_high_risk=False,
    )
    assert decision.path is RoutingPath.GOVERNED_PATH


def test_english_implement_keyword_upgrades_from_fast_path() -> None:
    """English 'implement' should NOT be fast path even without flags."""
    decision = classify(
        "implement the user authentication module",
        has_file_changes=False,
        is_public_contract=False,
        has_external_side_effect=False,
        is_unclear_or_high_risk=False,
    )
    assert decision.path is RoutingPath.GOVERNED_PATH


def test_no_work_keyword_still_fast_path() -> None:
    """Descriptions without work keywords should remain fast path."""
    decision = classify(
        "explain how the routing system works",
        has_file_changes=False,
        is_public_contract=False,
        has_external_side_effect=False,
        is_unclear_or_high_risk=False,
    )
    assert decision.path is RoutingPath.FAST_PATH


def test_chinese_readonly_query_still_fast_path() -> None:
    """Chinese read-only query without work keywords remains fast path."""
    decision = classify(
        "这个项目的架构是什么样的",
        has_file_changes=False,
        is_public_contract=False,
        has_external_side_effect=False,
        is_unclear_or_high_risk=False,
    )
    assert decision.path is RoutingPath.FAST_PATH


# ---------------------------------------------------------------------------
# Rigor tier integration (v0.7.0)
# ---------------------------------------------------------------------------


class TestRigorTierIntegration:
    """Rigor tier is computed during classification and attached to the decision."""

    def test_default_rigor_is_strict(self) -> None:
        decision = classify(
            "add a new feature to the application",
            has_file_changes=True,
            is_public_contract=False,
            has_external_side_effect=False,
            is_unclear_or_high_risk=False,
        )
        assert decision.rigor_tier is RigorTier.STRICT

    def test_rigor_override_via_kwarg(self) -> None:
        decision = classify(
            "build a saas platform from scratch",
            has_file_changes=True,
            is_public_contract=True,
            has_external_side_effect=True,
            is_unclear_or_high_risk=False,
            rigor="light",
        )
        # User override wins over keyword detection.
        assert decision.rigor_tier is RigorTier.LIGHT

    def test_auto_detect_strict_from_keywords(self) -> None:
        decision = classify(
            "从零构建一个微服务架构的平台",
            has_file_changes=True,
            is_public_contract=False,
            has_external_side_effect=False,
            is_unclear_or_high_risk=False,
        )
        assert decision.rigor_tier is RigorTier.STRICT

    def test_auto_detect_light_from_keywords(self) -> None:
        decision = classify(
            "fix a minor typo in the readme",
            has_file_changes=True,
            is_public_contract=False,
            has_external_side_effect=False,
            is_unclear_or_high_risk=False,
        )
        assert decision.rigor_tier is RigorTier.LIGHT

    def test_fast_path_also_gets_rigor_tier(self) -> None:
        """Even fast-path decisions carry a rigor tier."""
        decision = classify(
            "What does the harness-engineering skill do?",
            has_file_changes=False,
            is_public_contract=False,
            has_external_side_effect=False,
            is_unclear_or_high_risk=False,
        )
        assert decision.path is RoutingPath.FAST_PATH
        assert isinstance(decision.rigor_tier, RigorTier)

    def test_trivial_path_also_gets_rigor_tier(self) -> None:
        decision = classify(
            "Rename local variable foo to bar in src/foo.py",
            has_file_changes=True,
            is_public_contract=False,
            has_external_side_effect=False,
            is_unclear_or_high_risk=False,
        )
        assert decision.path is RoutingPath.TRIVIAL_SAFE_CHANGE
        assert isinstance(decision.rigor_tier, RigorTier)

    def test_routing_decision_repr_includes_rigor(self) -> None:
        decision = classify(
            "Build a new microservice",
            has_file_changes=True,
            is_public_contract=True,
            has_external_side_effect=True,
            is_unclear_or_high_risk=False,
        )
        r = repr(decision)
        assert "rigor" in r
        assert "strict" in r


# ---------------------------------------------------------------------------
# STRICT keyword gate (prevents fast-path misroute when agent omits flags)
# ---------------------------------------------------------------------------


class TestStrictKeywordGate:
    """STRICT_DETECTION_KEYWORDS in description force governed-path
    regardless of missing --files/--external flags.

    This guards against agents that call ``harness governed-start``
    without the necessary flags, causing large tasks to be misrouted
    as fast-path.
    """

    def test_saas_platform_no_flags_is_governed(self) -> None:
        """Exact bug scenario: 'SaaS 平台' without --files/--external."""
        decision = classify(
            "SaaS 平台 - 用户与认证系统",
            has_file_changes=False,
            is_public_contract=False,
            has_external_side_effect=False,
            is_unclear_or_high_risk=False,
        )
        assert decision.path is RoutingPath.GOVERNED_PATH
        assert decision.rigor_tier is RigorTier.STRICT

    def test_platform_keyword_no_flags_is_governed(self) -> None:
        decision = classify(
            "Build a platform for user management",
            has_file_changes=False,
            is_public_contract=False,
            has_external_side_effect=False,
            is_unclear_or_high_risk=False,
        )
        assert decision.path is RoutingPath.GOVERNED_PATH

    def test_from_scratch_no_flags_is_governed(self) -> None:
        decision = classify(
            "从零构建一个新项目",
            has_file_changes=False,
            is_public_contract=False,
            has_external_side_effect=False,
            is_unclear_or_high_risk=False,
        )
        assert decision.path is RoutingPath.GOVERNED_PATH

    def test_microservice_no_flags_is_governed(self) -> None:
        decision = classify(
            "Design a microservice for order processing",
            has_file_changes=False,
            is_public_contract=False,
            has_external_side_effect=False,
            is_unclear_or_high_risk=False,
        )
        assert decision.path is RoutingPath.GOVERNED_PATH

    def test_strict_keyword_with_flags_still_governed(self) -> None:
        """STRICT keyword + correct flags → still governed (no regression)."""
        decision = classify(
            "SaaS 平台 - 用户与认证系统",
            has_file_changes=True,
            is_public_contract=True,
            has_external_side_effect=True,
            is_unclear_or_high_risk=False,
        )
        assert decision.path is RoutingPath.GOVERNED_PATH

    def test_no_strict_keyword_pure_qa_still_fast(self) -> None:
        """Pure Q&A without STRICT keywords still gets fast-path."""
        decision = classify(
            "What does the harness-engineering skill do?",
            has_file_changes=False,
            is_public_contract=False,
            has_external_side_effect=False,
            is_unclear_or_high_risk=False,
        )
        assert decision.path is RoutingPath.FAST_PATH

    def test_no_strict_keyword_trivial_still_trivial(self) -> None:
        """Trivial change without STRICT keywords still gets trivial-safe-change."""
        decision = classify(
            "Rename local variable foo to bar in src/foo.py",
            has_file_changes=True,
            is_public_contract=False,
            has_external_side_effect=False,
            is_unclear_or_high_risk=False,
        )
        assert decision.path is RoutingPath.TRIVIAL_SAFE_CHANGE

    def test_rigor_light_overrides_strict_keyword_gate(self) -> None:
        """When user explicitly passes --rigor light, respect it for routing.
        The STRICT keyword gate still forces governed-path (because the
        description implies real work), but the rigor tier is LIGHT."""
        decision = classify(
            "SaaS 平台 - 用户与认证系统",
            has_file_changes=False,
            is_public_contract=False,
            has_external_side_effect=False,
            is_unclear_or_high_risk=False,
            rigor="light",
        )
        # Keyword gate still forces governed-path
        assert decision.path is RoutingPath.GOVERNED_PATH
        # But rigor is overridden to LIGHT
        assert decision.rigor_tier is RigorTier.LIGHT
