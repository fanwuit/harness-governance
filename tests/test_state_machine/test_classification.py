"""Tests for the Fast/Trivial/Governed classification."""

from __future__ import annotations

from harness_governance.state_machine.classification import (
    RoutingPath,
    classify,
)


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


def test_disclosure_block_mentions_harness_engineering() -> None:
    decision = classify(
        "Build a new microservice",
        has_file_changes=True,
        is_public_contract=True,
        has_external_side_effect=True,
        is_unclear_or_high_risk=False,
    )
    text = decision.to_disclosure(("superpowers:subagent-driven-development",))
    assert "skill-use-transparency" in text
    assert "harness-engineering" in text
    assert "superpowers:subagent-driven-development" in text


def test_disclosure_does_not_duplicate_primary_skill() -> None:
    """When the primary skill is the router itself, do not list it twice in the local skills line."""
    decision = classify(
        "Refactor the API boundary",
        has_file_changes=True,
        is_public_contract=True,
        has_external_side_effect=False,
        is_unclear_or_high_risk=False,
    )
    # primary_skill for a governed path is always ``harness-engineering``.
    assert decision.primary_skill == "harness-engineering"
    text = decision.to_disclosure()
    local_line = next(line for line in text.splitlines() if line.startswith("Local governance skills:"))
    assert local_line.count("harness-engineering") == 1