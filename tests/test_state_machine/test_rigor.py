"""Tests for rigor tier detection and resolution."""

from __future__ import annotations

import pytest

from harness_governance.state_machine.rigor import (
    RigorTier,
    STRICT_DETECTION_KEYWORDS,
    LIGHT_DETECTION_KEYWORDS,
    detect_rigor,
    resolve_rigor,
)


class TestRigorTier:
    def test_enum_values(self) -> None:
        assert RigorTier.LIGHT.value == "light"
        assert RigorTier.STANDARD.value == "standard"
        assert RigorTier.STRICT.value == "strict"

    def test_enum_from_string(self) -> None:
        assert RigorTier("light") is RigorTier.LIGHT
        assert RigorTier("standard") is RigorTier.STANDARD
        assert RigorTier("strict") is RigorTier.STRICT

    def test_enum_from_uppercase(self) -> None:
        """resolve_rigor lowercases input, so RigorTier("LIGHT") should work."""
        # RigorTier(str, Enum) uses str.__new__, so case matters at construction.
        # But resolve_rigor does .lower().strip() first.
        with pytest.raises(ValueError):
            RigorTier("LIGHT")


class TestDetectRigor:
    def test_platform_keyword_detected_as_strict(self) -> None:
        assert detect_rigor("帮我从零构建一个 SaaS 平台") is RigorTier.STRICT

    def test_english_saas_detected_as_strict(self) -> None:
        assert detect_rigor("build a saas platform from scratch") is RigorTier.STRICT

    def test_microservice_detected_as_strict(self) -> None:
        assert detect_rigor("design a distributed microservice architecture") is RigorTier.STRICT

    def test_greenfield_detected_as_strict(self) -> None:
        assert detect_rigor("greenfield project, building everything from scratch") is RigorTier.STRICT

    def test_payment_detected_as_strict(self) -> None:
        assert detect_rigor("add payment and billing system") is RigorTier.STRICT

    def test_typo_detected_as_light(self) -> None:
        assert detect_rigor("fix a typo in readme") is RigorTier.LIGHT

    def test_formatting_detected_as_light(self) -> None:
        assert detect_rigor("fix code formatting and lint issues") is RigorTier.LIGHT

    def test_minor_fix_detected_as_light(self) -> None:
        assert detect_rigor("minor fix for the login button") is RigorTier.LIGHT

    def test_chinese_typo_detected_as_light(self) -> None:
        assert detect_rigor("修复一个错别字") is RigorTier.LIGHT

    def test_defaults_to_strict(self) -> None:
        """Unknown descriptions default to STRICT (safe default)."""
        assert detect_rigor("add a new feature to the application") is RigorTier.STRICT

    def test_strict_keyword_takes_priority_over_light(self) -> None:
        """STRICT keywords win when both are present."""
        assert detect_rigor("fix a typo in the payment platform") is RigorTier.STRICT

    def test_chinese_keywords(self) -> None:
        assert detect_rigor("从零开始构建平台") is RigorTier.STRICT
        assert detect_rigor("系统架构重构") is RigorTier.STRICT
        assert detect_rigor("微服务架构设计") is RigorTier.STRICT


class TestResolveRigor:
    def test_user_override_wins(self) -> None:
        assert resolve_rigor("light", "build a saas platform") is RigorTier.LIGHT

    def test_auto_detect_when_no_override(self) -> None:
        assert resolve_rigor(None, "build a saas platform") is RigorTier.STRICT

    def test_default_strict_when_no_override_and_no_match(self) -> None:
        assert resolve_rigor(None, "some random task") is RigorTier.STRICT

    def test_invalid_override_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid rigor tier"):
            resolve_rigor("extreme", "some task")

    def test_override_case_insensitive(self) -> None:
        assert resolve_rigor("Light", "some task") is RigorTier.LIGHT
        assert resolve_rigor("STANDARD", "some task") is RigorTier.STANDARD

    def test_override_with_spaces(self) -> None:
        assert resolve_rigor("  strict  ", "some task") is RigorTier.STRICT
