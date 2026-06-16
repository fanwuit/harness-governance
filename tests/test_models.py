"""Tests for Pydantic schema validation."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from harness_governance.models.schemas import (
    ChangePacketInitResult,
    CheckFinding,
    CheckResult,
    EntryRecord,
    GateCheckInput,
    GateResult,
    GateStatus,
    HarnessConfig,
    QAPair,
    QueueItem,
    RigorProfile,
    RoutingInput,
    RoutingResult,
    StatusPayload,
    StatusQueueItem,
    StatusQueueSummary,
)
from harness_governance.state_machine.classification import RoutingPath
from harness_governance.state_machine.layers import HarnessLayer


def test_harness_config_defaults() -> None:
    config = HarnessConfig()
    assert config.agent_platform == "claude-code"
    assert config.queue_file == Path("NEXT.md")
    assert config.changes_root == Path("docs/changes")


def test_harness_config_forbids_unknown_keys() -> None:
    with pytest.raises(ValidationError):
        HarnessConfig.model_validate({"unknown": "value"})


def test_change_packet_init_result_validates_paths() -> None:
    payload = {
        "change_id": "demo",
        "packet_dir": Path("/tmp/demo"),
        "created_files": ("proposal.md",),
        "today": "2026-06-13",
    }
    result = ChangePacketInitResult.model_validate(payload)
    assert result.change_id == "demo"


def test_check_result_serialization() -> None:
    result = CheckResult(check="packet", passed=True, inspected=2)
    data = result.model_dump()
    assert data["check"] == "packet"
    assert data["passed"] is True


def test_entry_record_validates_layers() -> None:
    record = EntryRecord(
        current_layer=HarnessLayer.IMPLEMENTATION,
        target="src/a.py",
        scope="wire CLI",
        contract_evidence="docs/changes/x/contracts.md",
        readiness_gate="harness plan attest",
        packetization="docs/changes/x",
        verification_command="pytest -q",
        review_next_state="docs/changes/x/tasks.md",
        stop_conditions="3 consecutive pytest failures",
    )
    assert record.current_layer is HarnessLayer.IMPLEMENTATION


def test_entry_record_requires_stop_conditions() -> None:
    with pytest.raises(ValidationError):
        EntryRecord(
            current_layer=HarnessLayer.IMPLEMENTATION,
            target="x",
            scope="x",
            contract_evidence="x",
            readiness_gate="x",
            packetization="x",
            verification_command="x",
            review_next_state="x",
            stop_conditions="   ",
        )


def test_routing_input_forbids_extra() -> None:
    with pytest.raises(ValidationError):
        RoutingInput.model_validate({"description": "x", "unknown": 1})


def test_routing_result_round_trip() -> None:
    result = RoutingResult(
        path=RoutingPath.GOVERNED_PATH,
        rationale="touchy",
        current_layer=HarnessLayer.INTAKE_ORIENTATION,
        primary_skill="harness-engineering",
        disclosure="Local governance skills: skill-use-transparency, harness-engineering",
        recommended_next_command="harness packet init <id>",
    )
    data = result.model_dump()
    assert data["path"] == "governed-path"


def test_status_payload_serializes_with_queue_items() -> None:
    payload = StatusPayload(
        repo="/tmp",
        generated_at="2026-06-13T00:00:00Z",
        current_layer="implementation",
        queue_summary=StatusQueueSummary(total=1, ready=0, active=1),
        queue_items=(StatusQueueItem(raw="[active] x", active=True),),
    )
    assert payload.queue_items[0].active is True
    # Verify JSON backward compatibility: camelCase keys.
    data = payload.model_dump(by_alias=True)
    assert data["queueSummary"]["total"] == 1
    assert data["generatedAt"] == "2026-06-13T00:00:00Z"


# ---------------------------------------------------------------------------
# v0.7.0 rigor tier and gate models
# ---------------------------------------------------------------------------


class TestQAPair:
    def test_minimal_qa_pair(self) -> None:
        qa = QAPair(
            layer="intake-orientation",
            question="What is the current task?",
            answer="Build a SaaS platform",
            timestamp="2026-06-16T10:00:00Z",
        )
        assert qa.layer == "intake-orientation"
        assert qa.question == "What is the current task?"
        assert qa.answer == "Build a SaaS platform"

    def test_qa_pair_forbids_extra(self) -> None:
        with pytest.raises(ValidationError):
            QAPair.model_validate({
                "layer": "idea",
                "question": "Q",
                "answer": "A",
                "timestamp": "2026-06-16T10:00:00Z",
                "extra": "nope",
            })


class TestGateStatus:
    def test_minimal(self) -> None:
        gs = GateStatus(layer="intake-orientation", passed=True)
        assert gs.passed is True
        assert gs.questions_answered == 0
        assert gs.questions_required == 0

    def test_with_counts(self) -> None:
        gs = GateStatus(
            layer="intake-orientation",
            passed=True,
            questions_answered=4,
            questions_required=4,
            artifacts_found=(".harness/sessions/test.json",),
            artifacts_missing=(),
            confirmation_items_met=("Routing decision acknowledged",),
        )
        data = gs.model_dump()
        assert data["questions_answered"] == 4
        assert data["questions_required"] == 4
        assert len(data["artifacts_found"]) == 1

    def test_failed_gate(self) -> None:
        gs = GateStatus(
            layer="implementation",
            passed=False,
            questions_answered=0,
            questions_required=3,
            artifacts_missing=(".harness/gates/10-implementation.lock",),
        )
        assert gs.passed is False
        assert len(gs.artifacts_missing) == 1


class TestGateResult:
    def test_passed_result(self) -> None:
        gr = GateResult(
            layer="intake-orientation",
            passed=True,
        )
        data = gr.model_dump()
        assert data["check"] == "layer-gate"
        assert data["passed"] is True

    def test_failed_with_findings(self) -> None:
        finding = CheckFinding(
            check="layer-gate",
            target="intake-orientation",
            level="error",
            message="Questions: 0/4",
        )
        gr = GateResult(
            layer="intake-orientation",
            passed=False,
            findings=(finding,),
        )
        assert len(gr.findings) == 1
        assert gr.findings[0].level == "error"


class TestRigorProfile:
    def test_minimal(self) -> None:
        rp = RigorProfile(tier="strict")
        assert rp.tier == "strict"
        assert rp.required_layers == ()

    def test_full_profile(self) -> None:
        rp = RigorProfile(
            tier="light",
            required_layers=("intake-orientation", "brief", "readiness", "implementation", "verification", "review-next"),
            min_questions_per_layer={"intake-orientation": 1},
            auto_interrupt_on_unknowns=False,
        )
        data = rp.model_dump()
        assert len(data["required_layers"]) == 6
        assert data["auto_interrupt_on_unknowns"] is False


class TestGateCheckInput:
    def test_minimal(self) -> None:
        gci = GateCheckInput(layer="implementation")
        assert gci.layer == "implementation"
        assert gci.session_id is None

    def test_with_session(self) -> None:
        gci = GateCheckInput(layer="idea", session_id="20260616-test")
        assert gci.session_id == "20260616-test"


class TestRoutingInputRigor:
    def test_routing_input_accepts_rigor(self) -> None:
        ri = RoutingInput(
            description="Build a platform",
            has_file_changes=True,
            rigor_tier="strict",
        )
        assert ri.rigor_tier == "strict"

    def test_routing_input_rigor_defaults_none(self) -> None:
        ri = RoutingInput(description="test")
        assert ri.rigor_tier is None


class TestRoutingResultRigor:
    def test_routing_result_includes_rigor(self) -> None:
        rr = RoutingResult(
            path=RoutingPath.GOVERNED_PATH,
            rationale="test",
            disclosure="test",
            recommended_next_command="test",
            rigor_tier="strict",
        )
        assert rr.rigor_tier == "strict"

    def test_routing_result_rigor_nullable(self) -> None:
        rr = RoutingResult(
            path=RoutingPath.FAST_PATH,
            rationale="fast",
            disclosure="test",
            recommended_next_command="test",
        )
        assert rr.rigor_tier is None
