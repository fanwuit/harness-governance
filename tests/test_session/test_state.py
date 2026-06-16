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
