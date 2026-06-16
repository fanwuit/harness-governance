"""Tests for skill file version sentinels and required content across all 24 files.

Phase 6 hardening check: every skill file (8 platforms × 3 tiers) must contain:
1. ``<!-- harness-skill-version: 0.7.1 -->``
2. ``harness gate check implementation`` (hard gate instruction)
4. ``## Subagent Dispatch`` section (v0.7.1)
"""

from __future__ import annotations

import re
from importlib import resources
from pathlib import Path

import pytest

from harness_governance.config.defaults import GOVERNANCE_TIERS
from harness_governance.commands.init import extract_skill_version

_SKILLS_PACKAGE = "harness_governance.data.skills"

# Platforms with their expected extensions.
_PLATFORM_EXTS: dict[str, str] = {
    "claude-code": ".md",
    "codex": ".md",
    "cline": ".md",
    "cursor": ".mdc",
    "opencode": ".md",
    "windsurf": ".md",
    "qoderwork": ".md",
    "generic": ".md",
}


def _list_skill_files() -> list[tuple[str, str, str]]:
    """Return (tier, platform, content) for every tiered skill template."""
    results: list[tuple[str, str, str]] = []
    for tier in GOVERNANCE_TIERS:
        tier_dir = resources.files(_SKILLS_PACKAGE).joinpath(tier)
        if not tier_dir.is_dir():
            continue
        for platform, ext in _PLATFORM_EXTS.items():
            file_name = f"{platform}{ext}"
            resource = tier_dir.joinpath(file_name)
            if resource.is_file():
                results.append((tier, platform, resource.read_text(encoding="utf-8")))
    return results


# ---------------------------------------------------------------------------
# Collect once at import time so failures are clear and fast.
# ---------------------------------------------------------------------------

_ALL_SKILLS = _list_skill_files()


def test_all_24_skill_files_exist() -> None:
    """8 platforms × 3 tiers = 24 tiered skill files."""
    assert len(_ALL_SKILLS) == 24, f"Expected 24 skill files, found {len(_ALL_SKILLS)}"

    # Verify every combination is covered.
    found = {(t, p) for t, p, _ in _ALL_SKILLS}
    for tier in GOVERNANCE_TIERS:
        for platform in _PLATFORM_EXTS:
            assert (tier, platform) in found, f"Missing: {tier}/{platform}"


class TestSkillVersionSentinels:
    """Every skill file must carry ``<!-- harness-skill-version: X.Y.Z -->``."""

    @pytest.mark.parametrize("tier,platform,content", _ALL_SKILLS)
    def test_has_version_sentinel(self, tier: str, platform: str, content: str) -> None:
        ver = extract_skill_version(content)
        assert ver is not None, f"{tier}/{platform} missing version sentinel"
        assert ver == "0.7.1", (
            f"{tier}/{platform} version is {ver!r}, expected '0.7.1'"
        )


class TestGateCheckInstruction:
    """Every skill file must contain the hard gate check instruction."""

    @pytest.mark.parametrize("tier,platform,content", _ALL_SKILLS)
    def test_has_gate_check_instruction(self, tier: str, platform: str, content: str) -> None:
        assert "harness gate check implementation" in content, (
            f"{tier}/{platform} missing 'harness gate check implementation'"
        )


class TestYamlFrontmatter:
    """Every skill file must start with valid YAML frontmatter."""

    @pytest.mark.parametrize("tier,platform,content", _ALL_SKILLS)
    def test_has_yaml_frontmatter(self, tier: str, platform: str, content: str) -> None:
        stripped = content.lstrip()
        # Strip BOM defensively.
        if stripped.startswith("﻿"):
            stripped = stripped[1:]
        assert stripped.startswith("---"), (
            f"{tier}/{platform} does not start with YAML frontmatter"
        )
        # Check there's a closing --- after the opening.
        end = stripped.find("---", 3)
        assert end != -1, f"{tier}/{platform} YAML frontmatter not closed"

    @pytest.mark.parametrize("tier,platform,content", _ALL_SKILLS)
    def test_frontmatter_has_name(self, tier: str, platform: str, content: str) -> None:
        stripped = content.lstrip()
        if stripped.startswith("﻿"):
            stripped = stripped[1:]
        end = stripped.find("---", 3)
        frontmatter = stripped[3:end]
        assert "name:" in frontmatter, (
            f"{tier}/{platform} YAML frontmatter missing 'name'"
        )
        assert "description:" in frontmatter, (
            f"{tier}/{platform} YAML frontmatter missing 'description'"
        )


class TestTierSpecificContent:
    """Each tier has distinguishing content."""

    @pytest.mark.parametrize("platform", list(_PLATFORM_EXTS))
    def test_strict_mentions_all_12_layers(self, platform: str) -> None:
        content = _get_skill_content("strict", platform)
        assert content is not None, f"strict/{platform} not found"
        assert ("12 层" in content or "12 layers" in content.lower() or
                "All 12 layers" in content or "全部 12 层" in content or
                "STRICT MODE" in content), (
            f"strict/{platform} should mention strict enforcement"
        )

    @pytest.mark.parametrize("platform", list(_PLATFORM_EXTS))
    def test_light_mentions_6_layers(self, platform: str) -> None:
        content = _get_skill_content("light", platform)
        assert content is not None, f"light/{platform} not found"
        assert ("6 层" in content or "6 layers" in content.lower() or
                "LIGHT MODE" in content or "快速通道" in content or
                "轻量" in content), (
            f"light/{platform} should mention light/six-layer scope"
        )

    @pytest.mark.parametrize("platform", list(_PLATFORM_EXTS))
    def test_standard_mentions_standard_mode(self, platform: str) -> None:
        content = _get_skill_content("standard", platform)
        assert content is not None, f"standard/{platform} not found"
        assert ("standard" in content.lower() or "标准" in content), (
            f"standard/{platform} should mention standard governance"
        )


class TestSubagentDispatch:
    """Every skill file must contain the Subagent Dispatch section (v0.7.1)."""

    @pytest.mark.parametrize("tier,platform,content", _ALL_SKILLS)
    def test_has_subagent_dispatch_section(
        self, tier: str, platform: str, content: str
    ) -> None:
        assert "## Subagent Dispatch" in content, (
            f"{tier}/{platform} missing '## Subagent Dispatch' section"
        )

    @pytest.mark.parametrize("tier,platform,content", _ALL_SKILLS)
    def test_has_context_isolation_rules(
        self, tier: str, platform: str, content: str
    ) -> None:
        assert "harness runner render" in content, (
            f"{tier}/{platform} missing pre-render guidance"
        )
        assert "上下文污染" in content or "context pollution" in content.lower(), (
            f"{tier}/{platform} should mention context pollution risk"
        )


def _get_skill_content(tier: str, platform: str) -> str | None:
    """Read one skill file by tier+platform; return None if missing."""
    ext = _PLATFORM_EXTS.get(platform, ".md")
    resource = resources.files(_SKILLS_PACKAGE).joinpath(tier).joinpath(f"{platform}{ext}")
    if resource.is_file():
        return resource.read_text(encoding="utf-8")
    return None
