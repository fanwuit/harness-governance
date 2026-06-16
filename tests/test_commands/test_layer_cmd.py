"""Tests for ``harness layer advance``, ``harness layer show``, and ``harness layer guide``."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from harness_governance.cli import cli
from harness_governance.commands.layer import _extract_guide_section
from harness_governance.session import SessionState, create_session
from harness_governance.state_machine.classification import RoutingPath
from harness_governance.state_machine.layers import HarnessLayer


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
                "--project-root", str(tmp_path),
                "layer", "advance", "contract",
                "--boundary-touch",
            ],
        )
        assert result.exit_code == 0, result.output

    def test_advance_records_transition(self, tmp_path: Path) -> None:
        sid = _seed_session(tmp_path)
        runner = CliRunner()
        runner.invoke(cli, ["--project-root", str(tmp_path), "layer", "advance", "idea"])
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
            ["--project-root", str(tmp_path), "layer", "advance", "idea", "--confirmed"],
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
            ["--project-root", str(tmp_path), "layer", "advance", "idea", "--confirmed"],
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
