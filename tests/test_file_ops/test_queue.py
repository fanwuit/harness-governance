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


def test_parse_queue_ignores_html_comment_blocks() -> None:
    items = parse_queue(
        "<!--\n"
        "[ready] Example task\n"
        "- Id: example\n"
        "- Role: implementer\n"
        "-->\n\n"
        "[ready] Real task\n"
        "- Id: real\n"
        "- Role: implementer\n"
    )

    assert len(items) == 1
    assert items[0].id == "real"


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


NUMBERED_SAMPLE = """\
1. [ready] Ship CLI scaffolding
- Layer: implementation
- Change: scaffold-cli

2. [active] Lock plan attestation
- Layer: brief

3. [blocked] Draft ADR
- Layer: adr
"""

BULLET_SAMPLE = """\
- [ready] Ship CLI scaffolding
- Layer: implementation

* [active] Lock plan attestation
- Layer: brief
"""


def test_parse_queue_numbered_list() -> None:
    items = parse_queue(NUMBERED_SAMPLE)
    assert len(items) == 3
    assert items[0].ready is True
    assert items[0].layer is HarnessLayer.IMPLEMENTATION
    assert items[0].change_id == "scaffold-cli"
    assert items[1].active is True
    assert items[2].layer is HarnessLayer.ADR


def test_parse_queue_bullet_list() -> None:
    items = parse_queue(BULLET_SAMPLE)
    assert len(items) == 2
    assert items[0].ready is True
    assert items[1].active is True


def test_parse_queue_mixed_formats() -> None:
    mixed = "[ready] Plain entry\n- Layer: brief\n\n1. [active] Numbered entry\n- Layer: adr\n"
    items = parse_queue(mixed)
    assert len(items) == 2
    assert items[0].ready is True
    assert items[1].active is True


def test_parse_queue_structured_role_fields() -> None:
    items = parse_queue(
        "[planned] Review implementation\n"
        "- Id: review-1\n"
        "- Status: ready\n"
        "- Layer: verification\n"
        "- Role: reviewer-verifier\n"
        "- GateId: review\n"
        "- ChangeId: change-1\n"
        "- DependsOn: impl-1, contract-1\n"
        "- OwnerFiles: src/app.py, tests/test_app.py\n"
        "- SessionId: review-session\n"
        "- Verification: pytest -q\n"
        "- StopConditions: no skipped tests\n"
        "- HandoffFrom: impl-1\n"
    )

    assert len(items) == 1
    assert items[0].id == "review-1"
    assert items[0].status == "ready"
    assert items[0].role == "reviewer-verifier"
    assert items[0].gate_id == "review"
    assert items[0].change_id == "change-1"
    assert items[0].depends_on == ("impl-1", "contract-1")
    assert items[0].owner_files == ("src/app.py", "tests/test_app.py")
    assert items[0].session_id == "review-session"


def test_parse_queue_governance_hard_gate_fields() -> None:
    items = parse_queue(
        "[ready] Implement governed task\n"
        "- Id: impl-1\n"
        "- RolePlan: planner -> contract-test-writer -> implementer -> reviewer-verifier\n"
        "- TestPlan: tests/test_app.py::test_contract\n"
        "- FailingTestEvidence: pytest tests/test_app.py::test_contract failed\n"
        "- TddNotApplicable: docs-only\n"
    )

    assert items[0].role_plan == (
        "planner",
        "contract-test-writer",
        "implementer",
        "reviewer-verifier",
    )
    assert items[0].test_plan == "tests/test_app.py::test_contract"
    assert "failed" in (items[0].failing_test_evidence or "")
    assert items[0].tdd_not_applicable == "docs-only"


def test_parse_queue_structured_fields_are_case_insensitive() -> None:
    items = parse_queue(
        "[ready] Review implementation\n"
        "- id: review-1\n"
        "- status: ready\n"
        "- layer: verification\n"
        "- role: reviewer-verifier\n"
        "- gateID: review\n"
        "- changeId: change-1\n"
        "- dependsOn: impl-1\n"
        "- ownerFiles: src/app.py\n"
        "- sessionId: review-session\n"
        "- verification: pytest -q\n"
        "- stopConditions: no skipped tests\n"
        "- handoffFrom: impl-1\n"
    )

    assert len(items) == 1
    assert items[0].id == "review-1"
    assert items[0].status == "ready"
    assert items[0].layer is HarnessLayer.VERIFICATION
    assert items[0].role == "reviewer-verifier"
    assert items[0].gate_id == "review"
    assert items[0].change_id == "change-1"
    assert items[0].depends_on == ("impl-1",)
    assert items[0].owner_files == ("src/app.py",)
    assert items[0].session_id == "review-session"
    assert items[0].verification == "pytest -q"
    assert items[0].stop_conditions == "no skipped tests"
    assert items[0].handoff_from == "impl-1"
