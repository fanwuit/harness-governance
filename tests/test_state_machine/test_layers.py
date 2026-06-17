"""Tests for the layer map."""

from __future__ import annotations

import pytest

from harness_governance.state_machine.layers import (
    HarnessLayer,
    LAYER_MAP,
    canonical_progression,
    layer_index,
    resolve_layer,
)


def test_canonical_progression_has_twelve_layers() -> None:
    assert len(LAYER_MAP) == 12
    assert len(canonical_progression()) == 12


def test_canonical_progression_order() -> None:
    expected = (
        HarnessLayer.INTAKE_ORIENTATION,
        HarnessLayer.IDEA,
        HarnessLayer.FACT_DISCOVERY,
        HarnessLayer.BRAINSTORMING,
        HarnessLayer.BRIEF,
        HarnessLayer.ARCHITECTURE,
        HarnessLayer.ADR,
        HarnessLayer.CONTRACT,
        HarnessLayer.READINESS,
        HarnessLayer.IMPLEMENTATION,
        HarnessLayer.VERIFICATION,
        HarnessLayer.REVIEW_NEXT,
    )
    assert canonical_progression() == expected


def test_layer_values_match_queue_labels() -> None:
    expected_values = {
        "intake-orientation",
        "idea",
        "fact-discovery",
        "brainstorming",
        "brief",
        "architecture",
        "adr",
        "contract",
        "readiness",
        "implementation",
        "verification",
        "review-next",
    }
    assert {layer.value for layer in HarnessLayer} == expected_values


def test_resolve_layer_accepts_known_forms() -> None:
    assert resolve_layer("intake-orientation") is HarnessLayer.INTAKE_ORIENTATION
    assert resolve_layer("INTAKE-ORIENTATION") is HarnessLayer.INTAKE_ORIENTATION
    assert resolve_layer("Intake / Orientation") is HarnessLayer.INTAKE_ORIENTATION


def test_resolve_layer_rejects_unknown() -> None:
    with pytest.raises(ValueError):
        resolve_layer("not-a-layer")


def test_layer_entries_have_primary_skill() -> None:
    for entry in LAYER_MAP:
        assert entry.primary_skill
        assert entry.required_output


def test_layer_index() -> None:
    assert layer_index(HarnessLayer.INTAKE_ORIENTATION) == 0
    assert layer_index(HarnessLayer.REVIEW_NEXT) == 11


def test_layer_entries_have_author_guide() -> None:
    """Every LayerEntry must have a non-empty author_guide key."""
    for entry in LAYER_MAP:
        assert entry.author_guide, f"Layer {entry.layer.value} is missing author_guide"
