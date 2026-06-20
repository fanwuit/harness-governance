"""Tests for runner/adapters/registry.py — adapter registry and dispatch resolution."""

from __future__ import annotations

from pathlib import Path

from harness_governance.models.schemas import (
    AdapterRoute,
    AgentCapabilityDeclaration,
    CapabilityTier,
)
from harness_governance.runner.adapters.registry import (
    available_executors,
    resolve_executor,
)


class TestResolveExecutor:
    def test_no_declarations_returns_none(self) -> None:
        assert resolve_executor("implementer", CapabilityTier.EXECUTION) is None

    def test_empty_declarations_returns_none(self) -> None:
        assert (
            resolve_executor("implementer", CapabilityTier.EXECUTION, declarations=[])
            is None
        )

    def test_known_adapter_returns_executor(self) -> None:
        decl = AgentCapabilityDeclaration(
            platform="test",
            adapters=(
                AdapterRoute(
                    role="implementer",
                    required_tier=CapabilityTier.EXECUTION,
                    adapter="subprocess",
                    model_label="python3",
                ),
            ),
        )
        executor = resolve_executor(
            "implementer", CapabilityTier.EXECUTION, declarations=[decl]
        )
        assert executor is not None
        assert "python3" in executor.name

    def test_subagent_adapter_returns_executor(self) -> None:
        decl = AgentCapabilityDeclaration(
            platform="test",
            adapters=(
                AdapterRoute(
                    role="implementer",
                    required_tier=CapabilityTier.EXECUTION,
                    adapter="subagent",
                    model_label="python3",
                ),
            ),
        )
        executor = resolve_executor(
            "implementer", CapabilityTier.EXECUTION, declarations=[decl]
        )
        assert executor is not None
        assert "python3" in executor.name or "subprocess" in executor.name

    def test_unknown_adapter_returns_none(self) -> None:
        decl = AgentCapabilityDeclaration(
            platform="test",
            adapters=(
                AdapterRoute(
                    role="implementer",
                    required_tier=CapabilityTier.EXECUTION,
                    adapter="nonexistent-adapter",
                ),
            ),
        )
        executor = resolve_executor(
            "implementer", CapabilityTier.EXECUTION, declarations=[decl]
        )
        assert executor is None

    def test_wrong_role_returns_none(self) -> None:
        decl = AgentCapabilityDeclaration(
            platform="test",
            adapters=(
                AdapterRoute(
                    role="verifier",
                    required_tier=CapabilityTier.STRONG,
                    adapter="subprocess",
                ),
            ),
        )
        executor = resolve_executor(
            "implementer", CapabilityTier.EXECUTION, declarations=[decl]
        )
        assert executor is None


class TestAvailableExecutors:
    def test_no_declarations(self) -> None:
        assert available_executors([]) == []

    def test_lists_all_declarations(self) -> None:
        decl = AgentCapabilityDeclaration(
            platform="test-platform",
            adapters=(
                AdapterRoute(
                    role="implementer",
                    required_tier=CapabilityTier.EXECUTION,
                    adapter="subagent",
                    model_label="python3",
                ),
                AdapterRoute(
                    role="verifier",
                    required_tier=CapabilityTier.STRONG,
                    adapter="subagent",
                    model_label="python3",
                ),
            ),
        )
        result = available_executors([decl])
        assert len(result) == 2
        roles = {r["role"] for r in result}
        assert roles == {"implementer", "verifier"}
