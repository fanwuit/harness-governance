"""Tests for capability-tier subagent routing."""

from __future__ import annotations

from harness_governance.models.schemas import (
    AdapterRoute,
    CapabilityTier,
    HarnessConfig,
    RoleCapabilityOverride,
    ROLE_CAPABILITY_POLICY,
)
from harness_governance.state_machine.capability_routing import (
    build_provenance,
    resolve_adapter,
    resolve_required_tier,
    role_policy_summary,
    verifier_required_for_tier,
)


class TestCapabilityTier:
    def test_enum_values(self) -> None:
        assert CapabilityTier.STRONG.value == "strong"
        assert CapabilityTier.EXECUTION.value == "execution"
        assert CapabilityTier.MECHANICAL.value == "mechanical"

    def test_strong_is_default_for_unknown_role(self) -> None:
        assert resolve_required_tier("unknown-role") == CapabilityTier.STRONG


class TestRoleCapabilityPolicy:
    def test_implementer_is_execution(self) -> None:
        assert ROLE_CAPABILITY_POLICY["implementer"] == CapabilityTier.EXECUTION

    def test_product_implementer_is_execution(self) -> None:
        assert ROLE_CAPABILITY_POLICY["product-implementer"] == CapabilityTier.EXECUTION

    def test_spec_writer_is_strong(self) -> None:
        assert ROLE_CAPABILITY_POLICY["spec-writer"] == CapabilityTier.STRONG

    def test_test_writer_is_strong(self) -> None:
        assert ROLE_CAPABILITY_POLICY["test-writer"] == CapabilityTier.STRONG

    def test_document_gardener_is_mechanical(self) -> None:
        assert (
            ROLE_CAPABILITY_POLICY["document-gardener"]
            == CapabilityTier.MECHANICAL
        )

    def test_planner_is_strong(self) -> None:
        assert ROLE_CAPABILITY_POLICY["planner"] == CapabilityTier.STRONG

    def test_verifier_is_strong(self) -> None:
        assert ROLE_CAPABILITY_POLICY["verifier"] == CapabilityTier.STRONG

    def test_reviewer_is_strong(self) -> None:
        assert ROLE_CAPABILITY_POLICY["reviewer"] == CapabilityTier.STRONG

    def test_contract_writer_is_strong(self) -> None:
        assert (
            ROLE_CAPABILITY_POLICY["contract-writer"]
            == CapabilityTier.STRONG
        )

    def test_resolve_required_tier_default(self) -> None:
        assert resolve_required_tier("implementer") == CapabilityTier.EXECUTION
        assert resolve_required_tier("planner") == CapabilityTier.STRONG
        assert (
            resolve_required_tier("document-gardener")
            == CapabilityTier.MECHANICAL
        )

    def test_resolve_required_tier_with_config_override(self) -> None:
        config = HarnessConfig(
            agent_platform="generic",
            role_capability_overrides=(
                RoleCapabilityOverride(
                    role="implementer",
                    required_tier=CapabilityTier.STRONG,
                ),
            ),
        )
        assert resolve_required_tier("implementer", config) == CapabilityTier.STRONG
        # Other roles unaffected
        assert resolve_required_tier("planner", config) == CapabilityTier.STRONG


class TestVerifierRequirement:
    def test_strong_does_not_need_verifier(self) -> None:
        assert verifier_required_for_tier(CapabilityTier.STRONG) is False

    def test_execution_needs_verifier(self) -> None:
        assert verifier_required_for_tier(CapabilityTier.EXECUTION) is True

    def test_mechanical_needs_verifier(self) -> None:
        assert verifier_required_for_tier(CapabilityTier.MECHANICAL) is True


class TestResolveAdapter:
    def test_no_declarations_returns_none(self) -> None:
        assert resolve_adapter("implementer", CapabilityTier.EXECUTION) is None

    def test_matching_route_from_declarations(self) -> None:
        from harness_governance.models.schemas import AgentCapabilityDeclaration

        decl = AgentCapabilityDeclaration(
            platform="opencode",
            adapters=(
                AdapterRoute(
                    role="implementer",
                    required_tier=CapabilityTier.EXECUTION,
                    adapter="subagent",
                    model_label="deepseek-v4-flash",
                ),
            ),
        )
        route = resolve_adapter(
            "implementer", CapabilityTier.EXECUTION, declarations=[decl]
        )
        assert route is not None
        assert route["adapter"] == "subagent"
        assert route["model_label"] == "deepseek-v4-flash"

    def test_non_matching_tier_returns_none(self) -> None:
        from harness_governance.models.schemas import AgentCapabilityDeclaration

        decl = AgentCapabilityDeclaration(
            platform="opencode",
            adapters=(
                AdapterRoute(
                    role="implementer",
                    required_tier=CapabilityTier.EXECUTION,
                    adapter="subagent",
                ),
            ),
        )
        route = resolve_adapter(
            "implementer", CapabilityTier.STRONG, declarations=[decl]
        )
        assert route is None


class TestBuildProvenance:
    def test_basic_provenance(self) -> None:
        p = build_provenance(
            role="implementer",
            required_tier=CapabilityTier.EXECUTION,
            platform="codex",
            model_label="claude-sonnet-4",
            adapter="subagent",
        )
        assert p.role == "implementer"
        assert p.required_tier == CapabilityTier.EXECUTION
        assert p.actual_tier == CapabilityTier.EXECUTION
        assert p.platform == "codex"
        assert p.model_label == "claude-sonnet-4"
        assert p.adapter == "subagent"
        assert p.verifier_required is True

    def test_strong_provenance_no_verifier(self) -> None:
        p = build_provenance(
            role="planner",
            required_tier=CapabilityTier.STRONG,
        )
        assert p.verifier_required is False

    def test_actual_tier_override(self) -> None:
        p = build_provenance(
            role="implementer",
            required_tier=CapabilityTier.STRONG,
            actual_tier=CapabilityTier.EXECUTION,
        )
        assert p.actual_tier == CapabilityTier.EXECUTION
        assert p.verifier_required is True


class TestRolePolicySummary:
    def test_summary_includes_all_default_roles(self) -> None:
        summary = role_policy_summary()
        roles = {entry["role"] for entry in summary}
        for role in ROLE_CAPABILITY_POLICY:
            assert role in roles

    def test_summary_reflects_override(self) -> None:
        config = HarnessConfig(
            agent_platform="generic",
            role_capability_overrides=(
                RoleCapabilityOverride(
                    role="implementer",
                    required_tier=CapabilityTier.STRONG,
                ),
            ),
        )
        summary = role_policy_summary(config)
        impl = next(e for e in summary if e["role"] == "implementer")
        assert impl["required_tier"] == "strong"
        assert impl["verifier_required"] == "False"
