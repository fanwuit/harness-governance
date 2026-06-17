"""Tests for the runner checkpoint helper."""

from __future__ import annotations

from pathlib import Path

from harness_governance.file_ops.checkpoint import Checkpoint


SAMPLE = """\
# Harness Runner Checkpoint

## Last Worker

codex-exec worker #12

## Durable State Updated

- 2026-06-13 docs/changes/scaffold-cli/

## Verification

- pytest: 42 passed

## Next Resume Source

NEXT.md [ready] entry: scaffold-cli

## Stop Reason

none
"""


def test_checkpoint_round_trip(tmp_path: Path) -> None:
    target = tmp_path / "run-checkpoint.md"
    cp = Checkpoint.from_markdown(SAMPLE)
    cp.dump(target)
    reloaded = Checkpoint.load(target)
    assert reloaded.last_worker == "codex-exec worker #12"
    assert reloaded.verification == "- pytest: 42 passed"
    assert reloaded.stop_reason == "none"


def test_checkpoint_load_missing_file(tmp_path: Path) -> None:
    cp = Checkpoint.load(tmp_path / "missing.md")
    assert cp.last_worker == ""
    assert cp.stop_reason == ""


def test_checkpoint_dump_creates_parent(tmp_path: Path) -> None:
    target = tmp_path / "nested" / "run-checkpoint.md"
    cp = Checkpoint(last_worker="w1", stop_reason="paused")
    cp.dump(target)
    assert target.is_file()
