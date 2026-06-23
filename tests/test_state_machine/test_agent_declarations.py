"""Tests for agent capability-tier declaration discovery."""

from __future__ import annotations

import json
from pathlib import Path

from harness_governance.models.schemas import (
    AdapterRoute,
    AgentCapabilityDeclaration,
)
from harness_governance.state_machine.agent_declarations import (
    all_adapters_from_declarations,
    discover_declarations,
    resolve_adapter_from_declarations,
)


class TestDiscoverDeclarations:
    def test_no_tiers_json_returns_empty(self, tmp_path: Path) -> None:
        decls = discover_declarations(tmp_path)
        assert decls == []

    def test_discovers_tiers_json_in_agent_dir(self, tmp_path: Path) -> None:
        agent_dir = tmp_path / ".agents"
        agent_dir.mkdir()
        (agent_dir / "tiers.json").write_text(
            json.dumps(
                {
                    "platform": "opencode",
                    "adapters": [
                        {
                            "role": "implementer",
                            "required_tier": "execution",
                            "adapter": "subagent",
                            "model_label": "deepseek-v4-flash",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        decls = discover_declarations(tmp_path)
        assert len(decls) == 1
        assert decls[0].platform == "opencode"
        assert len(decls[0].adapters) == 1
        assert decls[0].adapters[0].role == "implementer"

    def test_multiple_agent_dirs(self, tmp_path: Path) -> None:
        for d in (".claude", ".agents", ".opencode"):
            (tmp_path / d).mkdir()
            (tmp_path / d / "tiers.json").write_text(
                json.dumps(
                    {
                        "platform": d.lstrip("."),
                        "adapters": [],
                    }
                ),
                encoding="utf-8",
            )
        decls = discover_declarations(tmp_path)
        assert len(decls) == 3

    def test_skip_invalid_json(self, tmp_path: Path) -> None:
        agent_dir = tmp_path / ".agents"
        agent_dir.mkdir()
        (agent_dir / "tiers.json").write_text("not valid json", encoding="utf-8")
        decls = discover_declarations(tmp_path)
        assert decls == []


class TestResolveAdapterFromDeclarations:
    def test_match_found(self) -> None:
        decl = AgentCapabilityDeclaration(
            platform="opencode",
            adapters=(
                AdapterRoute(
                    role="implementer",
                    required_tier="execution",
                    adapter="subagent",
                    model_label="deepseek-v4-flash",
                ),
            ),
        )
        result = resolve_adapter_from_declarations("implementer", "execution", [decl])
        assert result is not None
        assert result["adapter"] == "subagent"
        assert result["model_label"] == "deepseek-v4-flash"
        assert result["platform"] == "opencode"

    def test_no_match(self) -> None:
        decl = AgentCapabilityDeclaration(
            platform="opencode",
            adapters=(
                AdapterRoute(
                    role="implementer",
                    required_tier="execution",
                    adapter="subagent",
                ),
            ),
        )
        result = resolve_adapter_from_declarations("planner", "strong", [decl])
        assert result is None

    def test_empty_declarations(self) -> None:
        assert resolve_adapter_from_declarations("implementer", "execution", []) is None

    def test_first_match_wins(self) -> None:
        d1 = AgentCapabilityDeclaration(
            platform="claude-code",
            adapters=(
                AdapterRoute(
                    role="implementer",
                    required_tier="execution",
                    adapter="claude-agent",
                    model_label="claude-sonnet-4",
                ),
            ),
        )
        d2 = AgentCapabilityDeclaration(
            platform="opencode",
            adapters=(
                AdapterRoute(
                    role="implementer",
                    required_tier="execution",
                    adapter="subagent",
                    model_label="deepseek-v4-flash",
                ),
            ),
        )
        result = resolve_adapter_from_declarations("implementer", "execution", [d1, d2])
        assert result is not None
        assert result["adapter"] == "claude-agent"
        assert result["platform"] == "claude-code"


class TestAllAdaptersFromDeclarations:
    def test_grouped_by_role(self) -> None:
        d1 = AgentCapabilityDeclaration(
            platform="opencode",
            adapters=(
                AdapterRoute(
                    role="implementer",
                    required_tier="execution",
                    adapter="subagent",
                    model_label="deepseek-v4-flash",
                ),
            ),
        )
        d2 = AgentCapabilityDeclaration(
            platform="opencode",
            adapters=(
                AdapterRoute(
                    role="verifier",
                    required_tier="strong",
                    adapter="subagent",
                    model_label="deepseek-v4-flash",
                ),
            ),
        )
        by_role = all_adapters_from_declarations([d1, d2])
        assert "implementer" in by_role
        assert "verifier" in by_role
        assert len(by_role["implementer"]) == 1
        assert len(by_role["verifier"]) == 1
