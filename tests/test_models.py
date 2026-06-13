"""Tests for Pydantic schema validation."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from harness_governance.models.schemas import (
    ChangePacketInitResult,
    CheckResult,
    EntryRecord,
    HarnessConfig,
    QueueItem,
    RoutingInput,
    RoutingResult,
    StatusView,
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


def test_status_view_serializes_with_queue_items() -> None:
    item = QueueItem(raw="[active] x", active=True)
    view = StatusView(
        project_root=Path("/tmp"),
        queue_path=Path("/tmp/NEXT.md"),
        queue_items=(item,),
    )
    assert view.queue_items[0].active is True