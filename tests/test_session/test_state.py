"""Tests for session state Pydantic models."""

from __future__ import annotations

import json

from harness_governance.session.state import SessionState, TransitionRecord
from harness_governance.state_machine.classification import RoutingPath
from harness_governance.state_machine.layers import HarnessLayer


class TestTransitionRecord:
    def test_serialize_roundtrip(self) -> None:
        rec = TransitionRecord(
            from_layer=HarnessLayer.INTAKE_ORIENTATION,
            to_layer=HarnessLayer.IDEA,
            timestamp="2026-06-16T10:00:00+00:00",
            context_flags={},
            engine_verdict=True,
            violations=(),
        )
        raw = json.loads(rec.model_dump_json())
        assert raw["from_layer"] == "intake-orientation"
        assert raw["to_layer"] == "idea"
        assert raw["engine_verdict"] is True

    def test_with_violations(self) -> None:
        rec = TransitionRecord(
            from_layer=HarnessLayer.IDEA,
            to_layer=HarnessLayer.IMPLEMENTATION,
            timestamp="2026-06-16T10:00:00+00:00",
            engine_verdict=False,
            violations=("[T1] blocked",),
        )
        assert rec.engine_verdict is False
        assert len(rec.violations) == 1


class TestSessionState:
    def test_minimal(self) -> None:
        state = SessionState(
            session_id="20260616-test",
            created_at="2026-06-16T10:00:00+00:00",
            description="Test",
            routing_path=RoutingPath.GOVERNED_PATH,
        )
        assert state.current_layer is None
        assert state.status == "active"
        assert state.transitions == ()

    def test_full_roundtrip(self) -> None:
        rec = TransitionRecord(
            from_layer=HarnessLayer.INTAKE_ORIENTATION,
            to_layer=HarnessLayer.IDEA,
            timestamp="2026-06-16T10:00:00+00:00",
            engine_verdict=True,
        )
        state = SessionState(
            session_id="20260616-full",
            created_at="2026-06-16T10:00:00+00:00",
            description="Full test",
            routing_path=RoutingPath.GOVERNED_PATH,
            current_layer=HarnessLayer.IDEA,
            change_id="my-change",
            companion_skills=("skill-a",),
            transitions=(rec,),
        )
        raw = json.loads(state.model_dump_json())
        restored = SessionState.model_validate(raw)
        assert restored.session_id == state.session_id
        assert restored.current_layer == HarnessLayer.IDEA
        assert restored.change_id == "my-change"
        assert len(restored.transitions) == 1

    def test_extra_forbidden(self) -> None:
        import pytest

        with pytest.raises(Exception):
            SessionState(
                session_id="test",
                created_at="2026-06-16T10:00:00+00:00",
                description="test",
                routing_path=RoutingPath.GOVERNED_PATH,
                unknown_field="bad",
            )


class TestRigorTierAndLayerQA:
    """v0.7.0: SessionState carries rigor_tier and layer_qa."""

    def test_default_rigor_is_strict(self) -> None:
        state = SessionState(
            session_id="20260616-rigor",
            created_at="2026-06-16T10:00:00+00:00",
            description="Test rigor defaults",
            routing_path=RoutingPath.GOVERNED_PATH,
        )
        assert state.rigor_tier == "strict"

    def test_explicit_rigor_light(self) -> None:
        state = SessionState(
            session_id="20260616-light",
            created_at="2026-06-16T10:00:00+00:00",
            description="Light session",
            routing_path=RoutingPath.GOVERNED_PATH,
            rigor_tier="light",
        )
        assert state.rigor_tier == "light"

    def test_default_layer_qa_is_empty(self) -> None:
        state = SessionState(
            session_id="20260616-qa",
            created_at="2026-06-16T10:00:00+00:00",
            description="Test QA defaults",
            routing_path=RoutingPath.GOVERNED_PATH,
        )
        assert state.layer_qa == ()

    def test_layer_qa_roundtrip(self) -> None:
        state = SessionState(
            session_id="20260616-qa2",
            created_at="2026-06-16T10:00:00+00:00",
            description="Test QA roundtrip",
            routing_path=RoutingPath.GOVERNED_PATH,
            rigor_tier="strict",
            layer_qa=(
                {
                    "layer": "intake-orientation",
                    "question": "What is the task?",
                    "answer": "Build X",
                    "timestamp": "2026-06-16T10:00:00Z",
                },
                {
                    "layer": "intake-orientation",
                    "question": "Any constraints?",
                    "answer": "No",
                    "timestamp": "2026-06-16T10:00:01Z",
                },
            ),
        )
        raw = json.loads(state.model_dump_json())
        restored = SessionState.model_validate(raw)
        assert restored.rigor_tier == "strict"
        assert len(restored.layer_qa) == 2
        assert restored.layer_qa[0]["layer"] == "intake-orientation"
        assert restored.layer_qa[0]["question"] == "What is the task?"

    def test_backward_compat_no_layer_qa_in_json(self) -> None:
        """Old sessions without layer_qa still load correctly."""
        old_json = {
            "session_id": "20260616-old",
            "created_at": "2026-06-16T10:00:00+00:00",
            "description": "Old session",
            "routing_path": "governed-path",
            "current_layer": "intake-orientation",
            "status": "active",
            "transitions": [],
        }
        # Old JSON has no rigor_tier or layer_qa — should default.
        state = SessionState.model_validate(old_json)
        assert state.rigor_tier == "strict"  # default
        assert state.layer_qa == ()  # default
