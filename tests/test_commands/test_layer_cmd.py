"""Tests for ``harness layer advance``, ``harness layer show``, and ``harness layer guide``."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from harness_governance.cli import cli
from harness_governance.commands.layer import _extract_guide_section
from harness_governance.session import SessionState, create_session
from harness_governance.state_machine.classification import RoutingPath
from harness_governance.state_machine.layers import HarnessLayer


_MOCK_INTAKE_QA: tuple[dict[str, str], ...] = (
    {
        "layer": "intake-orientation",
        "question": "Q1",
        "answer": "A1",
        "timestamp": "2026-06-16T10:00:00Z",
    },
    {
        "layer": "intake-orientation",
        "question": "Q2",
        "answer": "A2",
        "timestamp": "2026-06-16T10:00:01Z",
    },
    {
        "layer": "intake-orientation",
        "question": "Q3",
        "answer": "A3",
        "timestamp": "2026-06-16T10:00:02Z",
    },
    {
        "layer": "intake-orientation",
        "question": "Q4",
        "answer": "A4",
        "timestamp": "2026-06-16T10:00:03Z",
    },
)


def _seed_session(
    tmp_path: Path,
    *,
    session_id: str = "20260616-test",
    current_layer: HarnessLayer = HarnessLayer.INTAKE_ORIENTATION,
) -> str:
    state = SessionState(
        session_id=session_id,
        created_at="2026-06-16T10:00:00+00:00",
        description="Test",
        routing_path=RoutingPath.GOVERNED_PATH,
        current_layer=current_layer,
        layer_qa=_MOCK_INTAKE_QA,
    )
    create_session(tmp_path, state)
    return session_id


class TestLayerAdvance:
    def test_advance_allowed(self, tmp_path: Path) -> None:
        _seed_session(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "layer", "advance", "idea"],
        )
        assert result.exit_code == 0, result.output
        assert "idea" in result.output.lower() or "advanced" in result.output.lower()

    def test_advance_blocked(self, tmp_path: Path) -> None:
        _seed_session(tmp_path, current_layer=HarnessLayer.IDEA)
        runner = CliRunner()
        # IDEA -> IMPLEMENTATION should be blocked by T1.
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "layer", "advance", "implementation"],
        )
        assert result.exit_code != 0

    def test_advance_same_layer(self, tmp_path: Path) -> None:
        _seed_session(tmp_path, current_layer=HarnessLayer.IDEA)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "layer", "advance", "idea"],
        )
        assert result.exit_code == 0
        assert "already" in result.output.lower() or "已在" in result.output

    def test_advance_no_session(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "layer", "advance", "idea"],
        )
        assert result.exit_code != 0

    def test_advance_json_output(self, tmp_path: Path) -> None:
        _seed_session(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "--json", "layer", "advance", "idea"],
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["allowed"] is True
        assert data["to_layer"] == "idea"

    def test_advance_with_context_flags(self, tmp_path: Path) -> None:
        _seed_session(tmp_path, current_layer=HarnessLayer.ARCHITECTURE)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root",
                str(tmp_path),
                "layer",
                "advance",
                "contract",
                "--boundary-touch",
                "--skip-gate",
                "--confirmed",
            ],
        )
        assert result.exit_code == 0, result.output

    def test_advance_records_transition(self, tmp_path: Path) -> None:
        sid = _seed_session(tmp_path)
        runner = CliRunner()
        runner.invoke(
            cli, ["--project-root", str(tmp_path), "layer", "advance", "idea"]
        )
        # Verify the session file was updated with the transition.
        from harness_governance.session import load_session

        state = load_session(tmp_path, sid)
        assert len(state.transitions) == 1
        assert state.transitions[0].from_layer == HarnessLayer.INTAKE_ORIENTATION
        assert state.transitions[0].to_layer == HarnessLayer.IDEA


class TestLayerShow:
    def test_show_active(self, tmp_path: Path) -> None:
        _seed_session(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "layer", "show"],
        )
        assert result.exit_code == 0
        assert "intake-orientation" in result.output

    def test_show_no_session(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "layer", "show"],
        )
        assert result.exit_code != 0

    def test_show_json(self, tmp_path: Path) -> None:
        _seed_session(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "--json", "layer", "show"],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["current_layer"] == "intake-orientation"


class TestLayerGuide:
    def test_guide_for_active_session_layer(self, tmp_path: Path) -> None:
        _seed_session(tmp_path, current_layer=HarnessLayer.ARCHITECTURE)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "layer", "guide"],
        )
        assert result.exit_code == 0, result.output
        assert "architecture" in result.output.lower()
        assert "boundar" in result.output.lower()  # boundaries

    def test_guide_for_specific_layer(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "layer", "guide", "adr"],
        )
        assert result.exit_code == 0, result.output
        assert "adr" in result.output.lower()
        assert "decision" in result.output.lower()

    def test_guide_no_session_no_arg(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "layer", "guide"],
        )
        assert result.exit_code != 0

    def test_guide_json_output(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "--json", "layer", "guide", "idea"],
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["layer"] == "idea"
        assert data["found"] is True
        assert "intent" in data["guide"].lower()

    def test_guide_invalid_layer(self, tmp_path: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "layer", "guide", "not-a-real-layer"],
        )
        assert result.exit_code != 0

    def test_guide_all_twelve_layers_have_sections(self) -> None:
        """Every layer's author_guide key should resolve to a section in the guide file."""
        from harness_governance.commands.layer import _load_guide_file
        from harness_governance.state_machine.layers import LAYER_MAP

        guide_text = _load_guide_file()
        assert guide_text is not None, "layer-author-guide.md not found in package data"

        for entry in LAYER_MAP:
            section = _extract_guide_section(guide_text, entry.author_guide)
            assert section is not None, (
                f"No guide section found for layer {entry.layer.value!r} "
                f"(key: {entry.author_guide!r})"
            )
            assert len(section) > 50, (
                f"Guide section for {entry.layer.value!r} is too short"
            )


class TestLayerAdvanceConfirmed:
    def test_advance_with_confirmed_flag(self, tmp_path: Path) -> None:
        _seed_session(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root",
                str(tmp_path),
                "layer",
                "advance",
                "idea",
                "--confirmed",
            ],
        )
        assert result.exit_code == 0, result.output

    def test_advance_without_confirmed_still_works(self, tmp_path: Path) -> None:
        """--confirmed is optional — advance still succeeds without it."""
        _seed_session(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "layer", "advance", "idea"],
        )
        assert result.exit_code == 0, result.output

    def test_confirmed_recorded_in_transition(self, tmp_path: Path) -> None:
        sid = _seed_session(tmp_path)
        runner = CliRunner()
        runner.invoke(
            cli,
            [
                "--project-root",
                str(tmp_path),
                "layer",
                "advance",
                "idea",
                "--confirmed",
            ],
        )
        from harness_governance.session import load_session

        state = load_session(tmp_path, sid)
        assert state.transitions[-1].context_flags.get("author_confirmed") is True

    def test_unconfirmed_not_in_flags(self, tmp_path: Path) -> None:
        sid = _seed_session(tmp_path)
        runner = CliRunner()
        runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "layer", "advance", "idea"],
        )
        from harness_governance.session import load_session

        state = load_session(tmp_path, sid)
        assert "author_confirmed" not in state.transitions[-1].context_flags


# ---------------------------------------------------------------------------
# Gate enforcement (v0.7.0)
# ---------------------------------------------------------------------------


class TestLayerAdvanceGateEnforcement:
    """``layer advance`` must pass the current layer's gate before advancing."""

    def test_advance_blocked_by_gate_when_qa_insufficient(self, tmp_path: Path) -> None:
        """Without enough Q&A, the gate fails and advance is blocked."""
        # Create session with NO layer_qa — gate should fail.
        state = SessionState(
            session_id="gate-block-test",
            created_at="2026-06-16T10:00:00+00:00",
            description="Gate block test",
            routing_path=RoutingPath.GOVERNED_PATH,
            current_layer=HarnessLayer.INTAKE_ORIENTATION,
            rigor_tier="strict",
            # No layer_qa — gate requires 4 questions for STRICT intake.
        )
        create_session(tmp_path, state)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "layer", "advance", "idea"],
        )
        assert result.exit_code != 0, (
            f"Gate should have blocked advance, got: {result.output}"
        )

    def test_advance_passes_gate_with_sufficient_qa(self, tmp_path: Path) -> None:
        """With enough Q&A, the gate passes and writes a lock file."""
        _seed_session(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "layer", "advance", "idea"],
        )
        assert result.exit_code == 0, result.output
        # Verify lock file was written for the passed layer.
        lock = tmp_path / ".harness" / "gates" / "01-intake-orientation.lock"
        assert lock.is_file(), f"Expected lock file at {lock}"
        data = json.loads(lock.read_text(encoding="utf-8"))
        assert data["passed"] is True
        assert data["layer"] == "intake-orientation"

    def test_skip_gate_without_confirmed_raises(self, tmp_path: Path) -> None:
        """--skip-gate requires --confirmed (safety interlock)."""
        _seed_session(tmp_path)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root",
                str(tmp_path),
                "layer",
                "advance",
                "idea",
                "--skip-gate",
            ],
        )
        assert result.exit_code != 0, "Should require --confirmed with --skip-gate"

    def test_skip_gate_with_confirmed_bypasses_gate(self, tmp_path: Path) -> None:
        """--skip-gate --confirmed allows advance even with insufficient QA."""
        state = SessionState(
            session_id="skip-gate-confirmed-test",
            created_at="2026-06-16T10:00:00+00:00",
            description="Skip gate test",
            routing_path=RoutingPath.GOVERNED_PATH,
            current_layer=HarnessLayer.INTAKE_ORIENTATION,
            rigor_tier="strict",
            # No layer_qa — would fail gate, but --skip-gate --confirmed bypasses it.
        )
        create_session(tmp_path, state)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root",
                str(tmp_path),
                "layer",
                "advance",
                "idea",
                "--skip-gate",
                "--confirmed",
            ],
        )
        assert result.exit_code == 0, result.output

    def test_gate_failure_json_output(self, tmp_path: Path) -> None:
        """When gate fails, JSON output includes failure details."""
        state = SessionState(
            session_id="gate-json-test",
            created_at="2026-06-16T10:00:00+00:00",
            description="Gate JSON test",
            routing_path=RoutingPath.GOVERNED_PATH,
            current_layer=HarnessLayer.INTAKE_ORIENTATION,
            rigor_tier="strict",
        )
        create_session(tmp_path, state)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "--json", "layer", "advance", "idea"],
        )
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["allowed"] is False
        assert data["reason"] == "gate_failed"
        assert data["questions_answered"] == 0
        assert data["questions_required"] == 4

    def test_light_tier_requires_fewer_questions(self, tmp_path: Path) -> None:
        """LIGHT tier only requires 1 question for intake."""
        state = SessionState(
            session_id="light-gate-test",
            created_at="2026-06-16T10:00:00+00:00",
            description="Light tier gate",
            routing_path=RoutingPath.GOVERNED_PATH,
            current_layer=HarnessLayer.INTAKE_ORIENTATION,
            rigor_tier="light",
            layer_qa=(
                {
                    "layer": "intake-orientation",
                    "question": "Q1",
                    "answer": "A1",
                    "timestamp": "2026-06-16T10:00:00Z",
                },
            ),
        )
        create_session(tmp_path, state)
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "layer", "advance", "idea"],
        )
        assert result.exit_code == 0, result.output

    def test_rigor_override_flag(self, tmp_path: Path) -> None:
        """--rigor override changes the tier used for gate check."""
        state = SessionState(
            session_id="rigor-override-test",
            created_at="2026-06-16T10:00:00+00:00",
            description="Rigor override",
            routing_path=RoutingPath.GOVERNED_PATH,
            current_layer=HarnessLayer.INTAKE_ORIENTATION,
            rigor_tier="strict",
            layer_qa=(
                {
                    "layer": "intake-orientation",
                    "question": "Q1",
                    "answer": "A1",
                    "timestamp": "2026-06-16T10:00:00Z",
                },
            ),
        )
        create_session(tmp_path, state)
        # Override to light — 1 Q&A is enough.
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root",
                str(tmp_path),
                "layer",
                "advance",
                "idea",
                "--rigor",
                "light",
            ],
        )
        assert result.exit_code == 0, result.output

    def test_gate_skipped_for_non_required_layer(self, tmp_path: Path) -> None:
        """LIGHT tier: IDEA is not a required layer, gate is skipped when advancing FROM idea."""
        # First advance from intake to idea (with --skip-gate, since intake has no QA)
        state = SessionState(
            session_id="light-skip-test",
            created_at="2026-06-16T10:00:00+00:00",
            description="Light skip",
            routing_path=RoutingPath.GOVERNED_PATH,
            current_layer=HarnessLayer.INTAKE_ORIENTATION,
            rigor_tier="light",
            layer_qa=(
                {
                    "layer": "intake-orientation",
                    "question": "Q1",
                    "answer": "A1",
                    "timestamp": "2026-06-16T10:00:00Z",
                },
            ),
        )
        create_session(tmp_path, state)
        runner = CliRunner()
        # Advance intake→idea: intake's gate passes (1 QA in LIGHT mode).
        r = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "layer", "advance", "idea"],
        )
        assert r.exit_code == 0, f"intake→idea should pass: {r.output}"

        # Now advance idea→brief: idea is NOT in LIGHT required layers,
        # so gate is skipped even with no QA for the idea layer.
        r2 = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "layer", "advance", "brief"],
        )
        assert r2.exit_code == 0, (
            f"idea→brief should pass (idea gate skipped): {r2.output}"
        )
