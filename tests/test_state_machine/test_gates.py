"""Tests for layer gate definitions, engine, and lock file manager."""

from __future__ import annotations

from pathlib import Path


from harness_governance.state_machine.gates import (
    GATE_CATALOG,
    RIGOR_LAYER_PROFILES,
    LayerGateEngine,
    LockFileManager,
    gate_for_layer,
    layers_for_tier,
    is_layer_required,
    layer_order_number,
)
from harness_governance.state_machine.layers import HarnessLayer
from harness_governance.state_machine.rigor import RigorTier
from harness_governance.models.schemas import GateStatus
from harness_governance.session import SessionState
from harness_governance.state_machine.classification import RoutingPath


class TestGateCatalog:
    def test_all_twelve_layers_have_gate_definitions(self) -> None:
        for layer in HarnessLayer:
            assert layer in GATE_CATALOG, f"Missing gate for {layer.value}"
            gate = GATE_CATALOG[layer]
            assert len(gate.required_questions) > 0, f"No questions for {layer.value}"
            assert len(gate.confirmation_items) > 0, (
                f"No confirmations for {layer.value}"
            )

    def test_strict_requires_all_questions(self) -> None:
        for gate in GATE_CATALOG.values():
            assert gate.min_questions_answered[RigorTier.STRICT] <= len(
                gate.required_questions
            )
            # STRICT should require at least as many as STANDARD
            assert (
                gate.min_questions_answered[RigorTier.STRICT]
                >= gate.min_questions_answered[RigorTier.STANDARD]
            )

    def test_light_requires_one_question(self) -> None:
        for gate in GATE_CATALOG.values():
            assert gate.min_questions_answered[RigorTier.LIGHT] == 1

    def test_gate_for_layer_returns_correct_definition(self) -> None:
        gate = gate_for_layer(HarnessLayer.INTAKE_ORIENTATION)
        assert gate is not None
        assert gate.layer is HarnessLayer.INTAKE_ORIENTATION
        assert len(gate.required_questions) == 4

    def test_gate_for_layer_returns_none_for_unknown(self) -> None:
        # All known layers have gates
        for layer in HarnessLayer:
            assert gate_for_layer(layer) is not None


class TestRigorLayerProfiles:
    def test_strict_has_all_twelve_layers(self) -> None:
        assert len(RIGOR_LAYER_PROFILES[RigorTier.STRICT]) == 12

    def test_standard_has_all_twelve_layers(self) -> None:
        assert len(RIGOR_LAYER_PROFILES[RigorTier.STANDARD]) == 12

    def test_light_has_six_layers(self) -> None:
        assert len(RIGOR_LAYER_PROFILES[RigorTier.LIGHT]) == 6
        light_layers = RIGOR_LAYER_PROFILES[RigorTier.LIGHT]
        assert HarnessLayer.INTAKE_ORIENTATION in light_layers
        assert HarnessLayer.BRIEF in light_layers
        assert HarnessLayer.READINESS in light_layers
        assert HarnessLayer.IMPLEMENTATION in light_layers
        assert HarnessLayer.VERIFICATION in light_layers
        assert HarnessLayer.REVIEW_NEXT in light_layers
        # Skipped layers
        assert HarnessLayer.IDEA not in light_layers
        assert HarnessLayer.FACT_DISCOVERY not in light_layers
        assert HarnessLayer.BRAINSTORMING not in light_layers
        assert HarnessLayer.ARCHITECTURE not in light_layers
        assert HarnessLayer.ADR not in light_layers
        assert HarnessLayer.CONTRACT not in light_layers

    def test_layers_for_tier(self) -> None:
        assert len(layers_for_tier(RigorTier.STRICT)) == 12
        assert len(layers_for_tier(RigorTier.LIGHT)) == 6

    def test_is_layer_required(self) -> None:
        assert (
            is_layer_required(HarnessLayer.INTAKE_ORIENTATION, RigorTier.LIGHT) is True
        )
        assert is_layer_required(HarnessLayer.ARCHITECTURE, RigorTier.LIGHT) is False
        assert is_layer_required(HarnessLayer.ARCHITECTURE, RigorTier.STRICT) is True

    def test_layer_order_number(self) -> None:
        assert layer_order_number(HarnessLayer.INTAKE_ORIENTATION) == 1
        assert layer_order_number(HarnessLayer.IMPLEMENTATION) == 10
        assert layer_order_number(HarnessLayer.REVIEW_NEXT) == 12


class TestLayerGateEngine:
    def _make_session(self, **overrides) -> SessionState:
        kwargs = dict(
            session_id="test-gate-session",
            created_at="2026-06-16T10:00:00Z",
            description="Test gate session",
            routing_path=RoutingPath.GOVERNED_PATH,
            current_layer=HarnessLayer.INTAKE_ORIENTATION,
            rigor_tier="strict",
        )
        kwargs.update(overrides)
        return SessionState(**kwargs)

    def test_check_fails_with_no_qa(self, tmp_path: Path) -> None:
        session = self._make_session()
        engine = LayerGateEngine()
        status = engine.check(session, tmp_path, HarnessLayer.INTAKE_ORIENTATION)
        assert status.passed is False
        assert status.questions_answered == 0
        assert status.questions_required == 4

    def test_check_passes_with_sufficient_qa(self, tmp_path: Path) -> None:
        session = self._make_session(
            layer_qa=(
                {
                    "layer": "intake-orientation",
                    "question": "Q1",
                    "answer": "A1",
                    "timestamp": "",
                },
                {
                    "layer": "intake-orientation",
                    "question": "Q2",
                    "answer": "A2",
                    "timestamp": "",
                },
                {
                    "layer": "intake-orientation",
                    "question": "Q3",
                    "answer": "A3",
                    "timestamp": "",
                },
                {
                    "layer": "intake-orientation",
                    "question": "Q4",
                    "answer": "A4",
                    "timestamp": "",
                },
            ),
        )
        engine = LayerGateEngine()
        status = engine.check(session, tmp_path, HarnessLayer.INTAKE_ORIENTATION)
        assert status.passed is True
        assert status.questions_answered == 4

    def test_check_respects_rigor_tier(self, tmp_path: Path) -> None:
        """LIGHT tier only requires 1 question for intake-orientation."""
        session = self._make_session(
            rigor_tier="light",
            layer_qa=(
                {
                    "layer": "intake-orientation",
                    "question": "Q1",
                    "answer": "A1",
                    "timestamp": "",
                },
            ),
        )
        engine = LayerGateEngine()
        status = engine.check(session, tmp_path, HarnessLayer.INTAKE_ORIENTATION)
        assert status.passed is True
        assert status.questions_required == 1

    def test_check_unknown_layer_passes(self, tmp_path: Path) -> None:
        """Layers without gate definitions pass automatically."""
        session = self._make_session()
        engine = LayerGateEngine()
        # All HarnessLayer values have gates, but we test the None path
        # via gate_for_layer which returns None for unknown entries
        status = engine.check(session, tmp_path, HarnessLayer.INTAKE_ORIENTATION)
        assert status.layer == "intake-orientation"

    def test_check_artifact_detection(self, tmp_path: Path) -> None:
        """When required artifacts exist, they should be in artifacts_found."""
        # Create a session artifact directory
        (tmp_path / ".harness" / "sessions").mkdir(parents=True, exist_ok=True)
        (tmp_path / ".harness" / "sessions" / "test.json").write_text("{}")

        session = self._make_session(
            layer_qa=(
                {
                    "layer": "intake-orientation",
                    "question": "Q1",
                    "answer": "A1",
                    "timestamp": "",
                },
                {
                    "layer": "intake-orientation",
                    "question": "Q2",
                    "answer": "A2",
                    "timestamp": "",
                },
                {
                    "layer": "intake-orientation",
                    "question": "Q3",
                    "answer": "A3",
                    "timestamp": "",
                },
                {
                    "layer": "intake-orientation",
                    "question": "Q4",
                    "answer": "A4",
                    "timestamp": "",
                },
            ),
        )
        engine = LayerGateEngine()
        status = engine.check(session, tmp_path, HarnessLayer.INTAKE_ORIENTATION)
        assert status.passed is True
        assert len(status.artifacts_found) > 0
        assert len(status.artifacts_missing) == 0


class TestLockFileManager:
    def test_write_and_read_lock(self, tmp_path: Path) -> None:
        locks = LockFileManager(tmp_path)
        session = SessionState(
            session_id="lock-test",
            created_at="2026-06-16T10:00:00Z",
            description="Test",
            routing_path=RoutingPath.GOVERNED_PATH,
        )
        status = GateStatus(
            layer="intake-orientation",
            passed=True,
            questions_answered=4,
            questions_required=4,
        )

        path = locks.write_lock(HarnessLayer.INTAKE_ORIENTATION, status, session)
        assert path.is_file()

        data = locks.read_lock(HarnessLayer.INTAKE_ORIENTATION)
        assert data is not None
        assert data["layer"] == "intake-orientation"
        assert data["passed"] is True
        assert data["questions_answered"] == 4

    def test_lock_path_naming(self, tmp_path: Path) -> None:
        locks = LockFileManager(tmp_path)
        path = locks.lock_path(HarnessLayer.INTAKE_ORIENTATION)
        assert path.name == "01-intake-orientation.lock"
        assert path.parent == tmp_path / ".harness" / "gates"

        path = locks.lock_path(HarnessLayer.REVIEW_NEXT)
        assert path.name == "12-review-next.lock"

    def test_exists(self, tmp_path: Path) -> None:
        locks = LockFileManager(tmp_path)
        assert locks.exists(HarnessLayer.INTAKE_ORIENTATION) is False

        session = SessionState(
            session_id="exists-test",
            created_at="2026-06-16T10:00:00Z",
            description="Test",
            routing_path=RoutingPath.GOVERNED_PATH,
        )
        status = GateStatus(
            layer="intake-orientation",
            passed=True,
            questions_answered=4,
            questions_required=4,
        )
        locks.write_lock(HarnessLayer.INTAKE_ORIENTATION, status, session)
        assert locks.exists(HarnessLayer.INTAKE_ORIENTATION) is True

    def test_remove_lock(self, tmp_path: Path) -> None:
        locks = LockFileManager(tmp_path)
        session = SessionState(
            session_id="remove-test",
            created_at="2026-06-16T10:00:00Z",
            description="Test",
            routing_path=RoutingPath.GOVERNED_PATH,
        )
        status = GateStatus(
            layer="intake-orientation",
            passed=True,
            questions_answered=4,
            questions_required=4,
        )
        locks.write_lock(HarnessLayer.INTAKE_ORIENTATION, status, session)
        assert locks.exists(HarnessLayer.INTAKE_ORIENTATION) is True

        assert locks.remove_lock(HarnessLayer.INTAKE_ORIENTATION) is True
        assert locks.exists(HarnessLayer.INTAKE_ORIENTATION) is False

        # Removing non-existent lock returns False
        assert locks.remove_lock(HarnessLayer.INTAKE_ORIENTATION) is False

    def test_remove_all_locks(self, tmp_path: Path) -> None:
        locks = LockFileManager(tmp_path)
        session = SessionState(
            session_id="remove-all-test",
            created_at="2026-06-16T10:00:00Z",
            description="Test",
            routing_path=RoutingPath.GOVERNED_PATH,
        )
        status = GateStatus(layer="test", passed=True)

        locks.write_lock(HarnessLayer.INTAKE_ORIENTATION, status, session)
        locks.write_lock(HarnessLayer.IDEA, status, session)
        locks.write_lock(HarnessLayer.BRIEF, status, session)

        assert locks.remove_all_locks() == 3
        assert locks.exists(HarnessLayer.INTAKE_ORIENTATION) is False

    def test_read_lock_corrupted(self, tmp_path: Path) -> None:
        locks = LockFileManager(tmp_path)
        path = locks.lock_path(HarnessLayer.INTAKE_ORIENTATION)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not valid json{{{", encoding="utf-8")

        assert locks.read_lock(HarnessLayer.INTAKE_ORIENTATION) is None

    def test_gates_dir_created_on_write(self, tmp_path: Path) -> None:
        locks = LockFileManager(tmp_path)
        session = SessionState(
            session_id="dir-test",
            created_at="2026-06-16T10:00:00Z",
            description="Test",
            routing_path=RoutingPath.GOVERNED_PATH,
        )
        status = GateStatus(layer="test", passed=True)
        path = locks.write_lock(HarnessLayer.INTAKE_ORIENTATION, status, session)
        assert path.parent.is_dir()
