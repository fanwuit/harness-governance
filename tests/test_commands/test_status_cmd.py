"""Tests for ``harness status``."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from harness_governance.cli import cli
from harness_governance.commands.status import build_status, format_markdown
from tests.conftest import seed_session


def test_status_empty_repo(tmp_repo: Path) -> None:
    payload = build_status(tmp_repo)
    assert payload.current_layer == "unknown"
    assert payload.queue_summary.total == 0
    # Uninitialized project: single informational notice, no noisy warnings.
    assert any("not initialized" in w.lower() or "未初始化" in w for w in payload.warnings)


def test_status_aggregates_queue_and_packets(tmp_repo: Path) -> None:
    seed_session(tmp_repo)
    (tmp_repo / "NEXT.md").write_text(
        "[active] Implement scaffold\n- Layer: implementation\n- Change: scaffold-cli\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    runner.invoke(cli, ["--project-root", str(tmp_repo), "packet", "init", "scaffold-cli"])
    payload = build_status(tmp_repo)
    assert payload.current_layer == "implementation"
    assert payload.queue_summary.active == 1
    assert any(p.change_id == "scaffold-cli" for p in payload.packets)


def test_status_refresh_writes_files(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "status",
            "--refresh",
        ],
    )
    assert result.exit_code == 0, result.output
    assert (tmp_repo / ".harness" / "status.md").is_file()
    assert (tmp_repo / ".harness" / "status.json").is_file()


def test_status_markdown_includes_timeline(tmp_repo: Path) -> None:
    (tmp_repo / "NEXT.md").write_text(
        "[ready] Draft ADR\n- Layer: adr\n", encoding="utf-8"
    )
    payload = build_status(tmp_repo)
    md = format_markdown(payload)
    assert "Harness:" in md
    assert "[adr]" in md  # current layer bracket
    assert "Scheduler Queue" in md


def test_status_cli_json(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "--json", "status"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert "queueSummary" in payload
    assert "verification" in payload


def test_status_aggregates_per_change_checkpoint(tmp_repo: Path) -> None:
    """Status reads checkpoint from change packet directory."""
    from harness_governance.file_ops.checkpoint import Checkpoint

    # Create a change packet with a checkpoint
    change_dir = tmp_repo / "docs" / "changes" / "feature-a"
    change_dir.mkdir(parents=True)
    cp = Checkpoint(last_worker="round 1: test task", verification="- passed")
    cp.dump(change_dir / ".checkpoint.md")

    payload = build_status(tmp_repo)
    assert payload.checkpoint.found
    assert "round 1" in (payload.checkpoint.last_worker or "")


def test_status_aggregates_per_change_invocations(tmp_repo: Path) -> None:
    """Status reads invocation log from change packet directory."""
    change_dir = tmp_repo / "docs" / "changes" / "feature-a"
    change_dir.mkdir(parents=True)
    inv_log = change_dir / ".invocations.ndjson"
    inv_log.write_text(
        '{"round": 1, "exitCode": 0, "marker": "AUTONOMOUS_READY_DONE"}\n',
        encoding="utf-8",
    )

    payload = build_status(tmp_repo)
    assert payload.runner.invocation_count == 1
    assert payload.runner.last_exit_code == 0
