"""Tests for Implementation Entry Record parsing."""

from __future__ import annotations

from pathlib import Path

import pytest

from harness_governance.file_ops.entry import (
    has_entry_record_header,
    parse_entry_record,
    render_entry_record,
)
from harness_governance.state_machine.layers import HarnessLayer


SAMPLE_BLOCK = """\
# Implementation Entry Record

- Current layer: implementation
- Target: src/harness_governance/cli.py
- Scope: wire click groups
- Contract evidence: docs/changes/scaffold-cli/contracts.md
- Readiness gate: harness plan attest
- Packetization: docs/changes/scaffold-cli
- Verification command: pytest -q
- Review/Next state file: docs/changes/scaffold-cli/tasks.md
- Stop conditions: 3 consecutive pytest failures
"""


def test_parse_entry_record_extracts_all_fields() -> None:
    record = parse_entry_record(SAMPLE_BLOCK)
    assert record.current_layer is HarnessLayer.IMPLEMENTATION
    assert record.target == "src/harness_governance/cli.py"
    assert record.verification_command == "pytest -q"
    assert record.stop_conditions == "3 consecutive pytest failures"


def test_parse_entry_record_rejects_missing_field() -> None:
    bad = SAMPLE_BLOCK.replace("- Target: src/harness_governance/cli.py\n", "")
    with pytest.raises(ValueError):
        parse_entry_record(bad)


def test_parse_entry_record_rejects_invalid_layer() -> None:
    bad = SAMPLE_BLOCK.replace("- Current layer: implementation\n", "- Current layer: not-real\n")
    with pytest.raises(ValueError):
        parse_entry_record(bad)


def test_has_entry_record_header_detects_block() -> None:
    assert has_entry_record_header(SAMPLE_BLOCK)
    assert not has_entry_record_header("# Just a normal heading")


def test_render_entry_record_round_trip() -> None:
    record = parse_entry_record(SAMPLE_BLOCK)
    rendered = render_entry_record(record)
    parsed = parse_entry_record(rendered)
    assert parsed == record


def test_parse_entry_record_from_fixture(tmp_repo: Path) -> None:
    fixture = Path("src/harness_governance/data/fixtures/valid-entry-record.md")
    if not fixture.is_file():
        pytest.skip("Fixture not available")
    record = parse_entry_record(fixture.read_text(encoding="utf-8"))
    assert record.current_layer is HarnessLayer.IMPLEMENTATION