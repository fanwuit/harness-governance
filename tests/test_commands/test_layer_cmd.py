"""Tests for ``harness layer advance``, ``harness layer show``, and ``harness layer guide``."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from harness_governance.cli import cli
from harness_governance.commands.layer import (
    _extract_author_questions,
    _extract_guide_section,
    _format_choice_menu,
)
from harness_governance.session import SessionState, create_session, load_session
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
    layer_qa: tuple[dict[str, str], ...] = _MOCK_INTAKE_QA,
    rigor_tier: str = "standard",
) -> str:
    state = SessionState(
        session_id=session_id,
        created_at="2026-06-16T10:00:00+00:00",
        description="Test",
        routing_path=RoutingPath.GOVERNED_PATH,
        current_layer=current_layer,
        rigor_tier=rigor_tier,
        layer_qa=layer_qa,
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

    def test_answer_records_qa_for_gate(self, tmp_path: Path) -> None:
        session_id = _seed_session(
            tmp_path,
            session_id="20260616-answer-test",
            layer_qa=(),
            rigor_tier="strict",
        )
        runner = CliRunner()

        for idx in range(1, 5):
            result = runner.invoke(
                cli,
                [
                    "--project-root",
                    str(tmp_path),
                    "layer",
                    "answer",
                    "intake-orientation",
                    "--question",
                    f"Q{idx}",
                    "--answer",
                    f"A{idx}",
                ],
            )
            assert result.exit_code == 0, result.output

        state = load_session(tmp_path, session_id)
        assert len(state.layer_qa) == 4
        assert all(qa["layer"] == "intake-orientation" for qa in state.layer_qa)

        gate = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "gate", "check", "intake-orientation"],
        )
        assert gate.exit_code == 0, gate.output

    def test_answer_replaces_existing_layer_question(self, tmp_path: Path) -> None:
        session_id = _seed_session(
            tmp_path,
            session_id="20260616-answer-replace-test",
            layer_qa=(),
            rigor_tier="strict",
        )
        runner = CliRunner()

        first = runner.invoke(
            cli,
            [
                "--project-root",
                str(tmp_path),
                "layer",
                "answer",
                "idea",
                "--question",
                "Core problem?",
                "--answer",
                "First answer",
            ],
        )
        assert first.exit_code == 0, first.output
        second = runner.invoke(
            cli,
            [
                "--project-root",
                str(tmp_path),
                "layer",
                "answer",
                "idea",
                "--question",
                "Core problem?",
                "--answer",
                "Updated answer",
            ],
        )
        assert second.exit_code == 0, second.output
        assert "1 answer" in second.output or "1 answer(s)" in second.output

        state = load_session(tmp_path, session_id)
        idea_answers = [qa for qa in state.layer_qa if qa["layer"] == "idea"]
        assert len(idea_answers) == 1
        assert idea_answers[0]["answer"] == "Updated answer"

    def test_ask_records_author_questions_interactively(self, tmp_path: Path) -> None:
        session_id = _seed_session(
            tmp_path,
            session_id="20260616-ask-test",
            layer_qa=(),
            rigor_tier="strict",
        )
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root",
                str(tmp_path),
                "layer",
                "ask",
                "intake-orientation",
            ],
            input="A1\nA2\nA3\nA4\n",
        )
        assert result.exit_code == 0, result.output

        state = load_session(tmp_path, session_id)
        assert len(state.layer_qa) == 4
        assert all(qa["layer"] == "intake-orientation" for qa in state.layer_qa)

    def test_ask_skips_already_answered_questions(self, tmp_path: Path) -> None:
        session_id = _seed_session(
            tmp_path,
            session_id="20260616-ask-skip-test",
            layer_qa=(
                {
                    "layer": "idea",
                    "question": "Can you state the core problem in one sentence? / 你能用一句话描述核心问题或意图吗？",
                    "answer": "Existing",
                    "timestamp": "2026-06-16T10:00:00Z",
                },
            ),
            current_layer=HarnessLayer.IDEA,
            rigor_tier="strict",
        )
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "layer", "ask", "idea"],
            input="Feature\n",
        )
        assert result.exit_code == 0, result.output

        state = load_session(tmp_path, session_id)
        idea_answers = [qa for qa in state.layer_qa if qa["layer"] == "idea"]
        assert len(idea_answers) == 2
        assert idea_answers[0]["answer"] == "Existing"
        assert idea_answers[1]["answer"] == "Feature"

    def test_ask_reports_abort_guidance_for_noninteractive_input(
        self, tmp_path: Path
    ) -> None:
        _seed_session(
            tmp_path,
            session_id="20260616-ask-abort-test",
            layer_qa=(),
            rigor_tier="strict",
        )
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "layer", "ask", "intake-orientation"],
            input="",
        )

        assert result.exit_code != 0
        assert "Question prompt aborted" in result.output
        assert "harness layer answer" in result.output

    def test_wizard_json_reports_state_without_prompting(self, tmp_path: Path) -> None:
        _seed_session(
            tmp_path,
            session_id="20260616-wizard-json-test",
            layer_qa=(),
            rigor_tier="strict",
        )
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root",
                str(tmp_path),
                "--json",
                "layer",
                "wizard",
                "intake-orientation",
            ],
            input="",
        )

        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["layer"] == "intake-orientation"
        assert payload["questions_recorded"] == 0
        assert payload["gate_passed"] is False

    def test_wizard_can_record_answers_and_advance(self, tmp_path: Path) -> None:
        session_id = _seed_session(
            tmp_path,
            session_id="20260616-wizard-advance-test",
            layer_qa=(),
            rigor_tier="strict",
        )
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "layer", "wizard", "intake-orientation"],
            input="1\n1\n1\n1\n1\n",
        )

        assert result.exit_code == 0, result.output
        assert "Suggested answer" in result.output
        assert "Gate passed" in result.output
        assert "Layer advanced" in result.output
        state = load_session(tmp_path, session_id)
        assert state.current_layer == HarnessLayer.IDEA
        assert len(state.layer_qa) == 4
        assert state.layer_qa[0]["answer"] == "Test"

    def test_wizard_edit_records_edited_answer(self, tmp_path: Path) -> None:
        session_id = _seed_session(
            tmp_path,
            session_id="20260616-wizard-edit-test",
            current_layer=HarnessLayer.IDEA,
            layer_qa=(),
            rigor_tier="strict",
        )
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "layer", "wizard", "idea"],
            input="2\nEdited core problem\n1\n2\n",
        )

        assert result.exit_code == 0, result.output
        state = load_session(tmp_path, session_id)
        assert state.current_layer == HarnessLayer.IDEA
        assert len(state.layer_qa) == 2
        assert state.layer_qa[0]["answer"] == "Edited core problem"

    def test_wizard_skip_does_not_record_or_pass_gate(self, tmp_path: Path) -> None:
        session_id = _seed_session(
            tmp_path,
            session_id="20260616-wizard-skip-test",
            current_layer=HarnessLayer.IDEA,
            layer_qa=(),
            rigor_tier="strict",
        )
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "layer", "wizard", "idea"],
            input="3\n1\n",
        )

        assert result.exit_code == 0, result.output
        assert "FAILED" in result.output
        state = load_session(tmp_path, session_id)
        assert state.current_layer == HarnessLayer.IDEA
        assert len(state.layer_qa) == 1
        assert state.layer_qa[0]["question"].startswith("Feature, bug fix")

    def test_wizard_back_revisits_previous_question(self, tmp_path: Path) -> None:
        session_id = _seed_session(
            tmp_path,
            session_id="20260616-wizard-back-test",
            current_layer=HarnessLayer.IDEA,
            layer_qa=(),
            rigor_tier="strict",
        )
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "layer", "wizard", "idea"],
            input="1\n4\n2\nRevised core problem\n1\n2\n",
        )

        assert result.exit_code == 0, result.output
        state = load_session(tmp_path, session_id)
        assert state.current_layer == HarnessLayer.IDEA
        assert len(state.layer_qa) == 2
        assert state.layer_qa[0]["answer"] == "Revised core problem"

    def test_choice_menu_formats_selected_row_with_highlight(self) -> None:
        lines = _format_choice_menu(
            (
                ("confirm", "confirm - use suggested answer"),
                ("edit", "edit - type a different answer"),
                ("skip", "skip - leave unanswered"),
                ("back", "back - return to previous question"),
            ),
            selected_index=1,
        )

        assert lines[0] == "  1. confirm - use suggested answer"
        assert lines[1] == "> \x1b[7m2. edit - type a different answer\x1b[0m"
        assert lines[3] == "  4. back - return to previous question"

    def test_wizard_defaults_to_stop_when_selection_input_ends(
        self, tmp_path: Path
    ) -> None:
        session_id = _seed_session(
            tmp_path,
            session_id="20260616-wizard-no-choice-test",
            layer_qa=(),
            rigor_tier="strict",
        )
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "layer", "wizard", "intake-orientation"],
            input="1\n1\n1\n1\n",
        )

        assert result.exit_code == 0, result.output
        assert "harness layer advance idea --confirmed" in result.output
        state = load_session(tmp_path, session_id)
        assert state.current_layer == HarnessLayer.INTAKE_ORIENTATION
        assert len(state.layer_qa) == 4

    def test_intake_alias_records_author_questions(self, tmp_path: Path) -> None:
        session_id = _seed_session(
            tmp_path,
            session_id="20260616-intake-test",
            layer_qa=(),
            rigor_tier="strict",
        )
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_path), "layer", "intake"],
            input="A1\nA2\nA3\nA4\n",
        )
        assert result.exit_code == 0, result.output

        state = load_session(tmp_path, session_id)
        assert len(state.layer_qa) == 4

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

    def test_extract_author_questions(self) -> None:
        section = """
### Purpose / 目的
Context.

### Author Questions / 作者问题
1. What is the task? / 当前任务是什么？
2. What are the risks? / 风险是什么？

### Interaction Pattern / 交互模式
One at a time.
"""
        assert _extract_author_questions(section) == [
            "What is the task? / 当前任务是什么？",
            "What are the risks? / 风险是什么？",
        ]

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
        assert "Questions answered: 0/4" in result.output
        assert "Red flags we do not accept" in result.output
        assert "Required actions" in result.output
        assert "harness layer guide intake-orientation" in result.output
        assert "harness gate check intake-orientation" in result.output

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
