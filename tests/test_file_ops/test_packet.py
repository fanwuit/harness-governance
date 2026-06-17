"""Tests for change-packet file_ops."""

from __future__ import annotations

from pathlib import Path

import pytest

from harness_governance.file_ops.packet import (
    check_all_packets,
    check_packet,
    discover_packets,
    init_packet,
    packet_dir,
    resolve_packet_path,
)
from harness_governance.file_ops._util import validate_change_id


def test_validate_change_id_accepts_safe_names() -> None:
    validate_change_id("public-contract-fixture")
    validate_change_id("v2.api.2026")
    validate_change_id("a")


def test_validate_change_id_rejects_archive() -> None:
    with pytest.raises(ValueError):
        validate_change_id("archive")


def test_validate_change_id_rejects_empty() -> None:
    with pytest.raises(ValueError):
        validate_change_id("")


def test_validate_change_id_rejects_unsafe_chars() -> None:
    with pytest.raises(ValueError):
        validate_change_id("../escape")


def test_init_packet_creates_all_files(tmp_repo: Path) -> None:
    result = init_packet(tmp_repo, "demo")
    for filename in (
        "proposal.md",
        "design.md",
        "tasks.md",
        "contracts.md",
        "verification.md",
    ):
        assert (result.packet_dir / filename).is_file()
    assert result.change_id == "demo"
    assert set(result.created_files) == {
        "proposal.md",
        "design.md",
        "tasks.md",
        "contracts.md",
        "verification.md",
    }


def test_init_packet_replaces_change_id_placeholder(tmp_repo: Path) -> None:
    result = init_packet(tmp_repo, "demo-change")
    proposal = (result.packet_dir / "proposal.md").read_text(encoding="utf-8")
    assert "demo-change" in proposal
    assert "{{CHANGE_ID}}" not in proposal


def test_init_packet_force_does_not_overwrite_existing(tmp_repo: Path) -> None:
    init_packet(tmp_repo, "demo")
    marker = tmp_repo / "docs" / "changes" / "demo" / "tasks.md"
    marker.write_text("Custom content", encoding="utf-8")
    init_packet(tmp_repo, "demo", force=True)
    assert marker.read_text(encoding="utf-8") == "Custom content"


def test_init_packet_refuses_existing_non_empty_without_force(tmp_repo: Path) -> None:
    init_packet(tmp_repo, "demo")
    with pytest.raises(FileExistsError):
        init_packet(tmp_repo, "demo")


def _fill_valid_packet(packet_dir_path: Path) -> None:
    """Fill contracts.md and verification.md so a packet passes check."""
    (packet_dir_path / "contracts.md").write_text(
        "# Contracts\n\n- Artifact: schema\n- Path: schema.json\n",
        encoding="utf-8",
    )
    (packet_dir_path / "verification.md").write_text(
        "# Verification\n\n## Commands\n\n- pytest -q\n\n## Results\n\n- pass\n",
        encoding="utf-8",
    )


def test_check_packet_rejects_fresh_packet(tmp_repo: Path) -> None:
    """A freshly-initialized packet must fail until contracts/verification are filled.

    Matches legacy ``change-packet.test.mjs`` behavior.
    """
    init_packet(tmp_repo, "minimal")
    errors, _summary = check_packet(
        packet_dir(tmp_repo, "minimal"), project_root=tmp_repo
    )
    assert errors  # at least one error
    assert any("contracts.md" in err or "verification.md" in err for err in errors)


def test_check_packet_passes_when_filled(tmp_repo: Path) -> None:
    init_packet(tmp_repo, "minimal")
    _fill_valid_packet(packet_dir(tmp_repo, "minimal"))
    errors, _summary = check_packet(
        packet_dir(tmp_repo, "minimal"), project_root=tmp_repo
    )
    assert errors == []


def test_check_packet_flags_missing_checkbox(tmp_repo: Path) -> None:
    init_packet(tmp_repo, "no-checkbox")
    _fill_valid_packet(packet_dir(tmp_repo, "no-checkbox"))
    (tmp_repo / "docs" / "changes" / "no-checkbox" / "tasks.md").write_text(
        "# Tasks\nNo checklist items here.\n", encoding="utf-8"
    )
    errors, _summary = check_packet(
        packet_dir(tmp_repo, "no-checkbox"), project_root=tmp_repo
    )
    assert any("checkbox" in err for err in errors)


def test_check_packet_flags_invalid_status(tmp_repo: Path) -> None:
    init_packet(tmp_repo, "bad-status")
    _fill_valid_packet(packet_dir(tmp_repo, "bad-status"))
    (tmp_repo / "docs" / "changes" / "bad-status" / "proposal.md").write_text(
        "# Proposal\n\nStatus: bogus\n", encoding="utf-8"
    )
    errors, _summary = check_packet(
        packet_dir(tmp_repo, "bad-status"), project_root=tmp_repo
    )
    assert any("invalid status" in err for err in errors)


def test_check_packet_flags_missing_contracts_artifact(tmp_repo: Path) -> None:
    init_packet(tmp_repo, "no-artifact")
    _fill_valid_packet(packet_dir(tmp_repo, "no-artifact"))
    (tmp_repo / "docs" / "changes" / "no-artifact" / "contracts.md").write_text(
        "# Contracts\n\nCurrent behavior: TBD.\n", encoding="utf-8"
    )
    errors, _ = check_packet(packet_dir(tmp_repo, "no-artifact"), project_root=tmp_repo)
    assert any("contract artifact" in err for err in errors)


def test_check_packet_allows_blocked_reason(tmp_repo: Path) -> None:
    init_packet(tmp_repo, "blocked")
    (tmp_repo / "docs" / "changes" / "blocked" / "contracts.md").write_text(
        "# Contracts\n\n- Blocked reason: missing upstream schema\n", encoding="utf-8"
    )
    (tmp_repo / "docs" / "changes" / "blocked" / "verification.md").write_text(
        "# Verification\n\n## Commands\n\n- pytest -q\n\n## Results\n\n- pass\n",
        encoding="utf-8",
    )
    errors, _ = check_packet(packet_dir(tmp_repo, "blocked"), project_root=tmp_repo)
    assert not any("contract artifact" in err for err in errors)


def test_check_packet_flags_missing_verification_evidence(tmp_repo: Path) -> None:
    init_packet(tmp_repo, "no-verify")
    (tmp_repo / "docs" / "changes" / "no-verify" / "contracts.md").write_text(
        "# Contracts\n\n- Artifact: schema\n- Path: schema.json\n", encoding="utf-8"
    )
    (tmp_repo / "docs" / "changes" / "no-verify" / "verification.md").write_text(
        "# Verification\n\nNothing here.\n", encoding="utf-8"
    )
    errors, _ = check_packet(packet_dir(tmp_repo, "no-verify"), project_root=tmp_repo)
    assert any("verification" in err for err in errors)


def test_check_packet_allows_unable_to_verify(tmp_repo: Path) -> None:
    init_packet(tmp_repo, "no-verify-ok")
    (tmp_repo / "docs" / "changes" / "no-verify-ok" / "contracts.md").write_text(
        "# Contracts\n\n- Artifact: schema\n- Path: schema.json\n", encoding="utf-8"
    )
    (tmp_repo / "docs" / "changes" / "no-verify-ok" / "verification.md").write_text(
        "# Verification\n\n## Unable To Verify\n\n- Reason: env offline\n",
        encoding="utf-8",
    )
    errors, _ = check_packet(
        packet_dir(tmp_repo, "no-verify-ok"), project_root=tmp_repo
    )
    assert not any("verification" in err for err in errors)


def test_discover_packets_returns_live_and_archived(tmp_repo: Path) -> None:
    init_packet(tmp_repo, "live")
    archive = tmp_repo / "docs" / "changes" / "archive" / "2026-06-09-old"
    archive.mkdir(parents=True)
    found = discover_packets(tmp_repo)
    names = {p.name for p in found}
    assert "live" in names
    assert "2026-06-09-old" in names


def test_resolve_packet_path_accepts_id(tmp_repo: Path) -> None:
    init_packet(tmp_repo, "by-id")
    resolved = resolve_packet_path(tmp_repo, "by-id")
    assert resolved.name == "by-id"


def test_resolve_packet_path_accepts_relative_path(tmp_repo: Path) -> None:
    init_packet(tmp_repo, "relpath")
    resolved = resolve_packet_path(tmp_repo, "docs/changes/relpath")
    assert resolved.name == "relpath"


def test_resolve_packet_path_raises_for_missing(tmp_repo: Path) -> None:
    with pytest.raises(FileNotFoundError):
        resolve_packet_path(tmp_repo, "missing")


def test_check_all_packets_aggregates(tmp_repo: Path) -> None:
    init_packet(tmp_repo, "ok1")
    init_packet(tmp_repo, "ok2")
    _fill_valid_packet(packet_dir(tmp_repo, "ok1"))
    _fill_valid_packet(packet_dir(tmp_repo, "ok2"))
    errors, summaries = check_all_packets(tmp_repo)
    assert errors == []
    assert {s.change_id for s in summaries} == {"ok1", "ok2"}
