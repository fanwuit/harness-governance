"""Tests for NEXT.md queue parsing."""

from __future__ import annotations

from pathlib import Path

from harness_governance.file_ops.queue import format_queue, parse_queue, read_queue
from harness_governance.state_machine.layers import HarnessLayer


SAMPLE = """\
[active] Ship CLI scaffolding
- Layer: implementation
- Change: scaffold-cli
- Packetization: docs/changes/scaffold-cli
- Evidence: harness --help works

[ready] Lock plan attestation
- Layer: brief
- Change: scaffold-cli
- Packetization: docs/changes/scaffold-cli
- Evidence: task_plan.md present

[blocked] Draft ADR
- Layer: adr
- Change: scaffold-cli
- Packetization: docs/changes/scaffold-cli
- Evidence: missing upstream schema
"""


def test_parse_queue_extracts_layer() -> None:
    items = parse_queue(SAMPLE)
    assert len(items) == 3
    assert items[0].active is True
    assert items[0].layer is HarnessLayer.IMPLEMENTATION
    assert items[0].change_id == "scaffold-cli"
    assert items[1].ready is True
    assert items[2].layer is HarnessLayer.ADR


def test_parse_queue_handles_empty_input() -> None:
    assert parse_queue("") == []


def test_parse_queue_handles_unknown_layer() -> None:
    items = parse_queue("[active] Mystery\n- Layer: not-a-real-layer\n")
    assert len(items) == 1
    assert items[0].layer is None


def test_read_queue_missing_file(tmp_path: Path) -> None:
    assert read_queue(tmp_path / "NEXT.md") == []


def test_read_queue_returns_items(tmp_path: Path) -> None:
    (tmp_path / "NEXT.md").write_text(SAMPLE, encoding="utf-8")
    items = read_queue(tmp_path / "NEXT.md")
    assert len(items) == 3


def test_format_queue_round_trip() -> None:
    items = parse_queue(SAMPLE)
    rendered = format_queue(items)
    reparsed = parse_queue(rendered)
    assert [item.raw for item in reparsed] == [item.raw for item in items]