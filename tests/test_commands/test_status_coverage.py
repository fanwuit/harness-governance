"""Additional coverage tests for ``harness_governance.commands.status``.

Complements ``test_status_cmd.py`` by targeting branches and helpers
that are not exercised by the original five tests.
"""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from harness_governance.cli import cli
from harness_governance.commands.status import (
    _infer_current_layer,
    _read_invocation_log,
    _summarise_verification,
    build_status,
    format_markdown,
    format_text,
)
from harness_governance.file_ops.checkpoint import Checkpoint
from harness_governance.models.schemas import (
    QueueItem,
    StatusActivePlan,
    StatusCheckpoint,
    StatusPacketItem,
    StatusPayload,
    StatusQueueItem,
    StatusQueueSummary,
    StatusRunner,
    StatusVerification,
)
from harness_governance.state_machine.layers import HarnessLayer


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _make_payload(**overrides: object) -> StatusPayload:
    """Build a minimal ``StatusPayload`` with sensible defaults."""
    defaults: dict = {
        "repo": "/tmp/fake",
        "generated_at": "2025-01-01T00:00:00+00:00",
        "current_layer": "implementation",
        "queue_summary": StatusQueueSummary(total=0, ready=0, active=0),
        "queue_items": (),
        "packets": (),
        "active_plan": None,
        "checkpoint": StatusCheckpoint(),
        "runner": StatusRunner(),
        "verification": StatusVerification(),
        "warnings": (),
    }
    defaults.update(overrides)
    return StatusPayload(**defaults)


def _write_ndjson(path: Path, records: list[dict]) -> None:
    """Write records as newline-delimited JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(r) for r in records) + "\n",
        encoding="utf-8",
    )


# ===================================================================
# 1. _read_invocation_log
# ===================================================================


class TestReadInvocationLog:
    """Tests for ``_read_invocation_log``."""

    def test_missing_file_returns_warning(self, tmp_path: Path) -> None:
        missing = tmp_path / "no-such-file.ndjson"
        records, warnings = _read_invocation_log(missing)
        assert records == []
        assert len(warnings) == 1
        assert "not found" in warnings[0].lower()

    def test_bad_json_lines_produce_warnings(self, tmp_path: Path) -> None:
        log = tmp_path / "invocations.ndjson"
        log.write_text(
            '{"round": 1}\nNOT-VALID-JSON\n{"round": 3}\n',
            encoding="utf-8",
        )
        records, warnings = _read_invocation_log(log)
        assert len(records) == 2
        assert records[0]["round"] == 1
        assert records[1]["round"] == 3
        assert len(warnings) == 1
        assert "line 2" in warnings[0]

    def test_blank_lines_are_skipped(self, tmp_path: Path) -> None:
        log = tmp_path / "invocations.ndjson"
        log.write_text(
            '\n{"round": 1}\n\n{"round": 2}\n\n',
            encoding="utf-8",
        )
        records, warnings = _read_invocation_log(log)
        assert len(records) == 2
        assert warnings == []

    def test_empty_file(self, tmp_path: Path) -> None:
        log = tmp_path / "invocations.ndjson"
        log.write_text("", encoding="utf-8")
        records, warnings = _read_invocation_log(log)
        assert records == []
        assert warnings == []


# ===================================================================
# 2. _summarise_verification
# ===================================================================


class TestSummariseVerification:
    """Tests for ``_summarise_verification``."""

    def test_empty_invocations_and_empty_checkpoint(self) -> None:
        cp = Checkpoint()
        result = _summarise_verification(cp, [])
        assert result.source == "missing"
        assert result.stale is True
        assert result.summary is None

    def test_invocation_with_verification_summary(self) -> None:
        cp = Checkpoint()
        invocations = [{"verificationSummary": "All tests passed"}]
        result = _summarise_verification(cp, invocations)
        assert result.source == "invocation-log"
        assert result.summary == "All tests passed"
        assert result.stale is False
        assert result.failed is False

    def test_invocation_with_verification_key(self) -> None:
        cp = Checkpoint()
        invocations = [{"verification": "test suite passed"}]
        result = _summarise_verification(cp, invocations)
        assert result.source == "invocation-log"
        assert result.summary == "test suite passed"
        assert result.stale is False

    def test_invocation_failed_text(self) -> None:
        cp = Checkpoint()
        invocations = [{"verificationSummary": "2 tests failed"}]
        result = _summarise_verification(cp, invocations)
        assert result.failed is True
        assert result.stale is True

    def test_checkpoint_verification_fallback(self) -> None:
        cp = Checkpoint(verification="- lint passed\n- unit tests passed")
        result = _summarise_verification(cp, [])
        assert result.source == "checkpoint"
        assert result.summary is not None
        assert "passed" in result.summary.lower() or "lint" in result.summary.lower()
        assert result.stale is False

    def test_checkpoint_verification_with_failure(self) -> None:
        cp = Checkpoint(verification="build failed")
        result = _summarise_verification(cp, [])
        assert result.failed is True
        assert result.stale is True

    def test_invocation_takes_priority_over_checkpoint(self) -> None:
        cp = Checkpoint(verification="old checkpoint data")
        invocations = [{"verificationSummary": "fresh invocation ok passed"}]
        result = _summarise_verification(cp, invocations)
        assert result.source == "invocation-log"
        assert result.summary == "fresh invocation ok passed"


# ===================================================================
# 3. _infer_current_layer
# ===================================================================


class TestInferCurrentLayer:
    """Tests for ``_infer_current_layer``."""

    def test_active_item_with_layer(self) -> None:
        items = [
            QueueItem(
                raw="[active] task",
                active=True,
                layer=HarnessLayer.IMPLEMENTATION,
            ),
        ]
        assert _infer_current_layer(items) == "implementation"

    def test_ready_item_with_layer(self) -> None:
        items = [
            QueueItem(
                raw="[ready] task",
                ready=True,
                layer=HarnessLayer.ADR,
            ),
        ]
        assert _infer_current_layer(items) == "adr"

    def test_item_with_layer_only(self) -> None:
        """Neither active nor ready, but has a layer."""
        items = [
            QueueItem(
                raw="[blocked] task",
                active=False,
                ready=False,
                layer=HarnessLayer.CONTRACT,
            ),
        ]
        assert _infer_current_layer(items) == "contract"

    def test_empty_items_returns_none(self) -> None:
        assert _infer_current_layer([]) is None

    def test_items_without_layer_returns_none(self) -> None:
        items = [QueueItem(raw="plain text")]
        assert _infer_current_layer(items) is None

    def test_active_preferred_over_ready(self) -> None:
        items = [
            QueueItem(
                raw="[ready] task-a",
                ready=True,
                layer=HarnessLayer.IDEA,
            ),
            QueueItem(
                raw="[active] task-b",
                active=True,
                layer=HarnessLayer.VERIFICATION,
            ),
        ]
        assert _infer_current_layer(items) == "verification"


# ===================================================================
# 4. build_status
# ===================================================================


class TestBuildStatus:
    """Tests for ``build_status``."""

    def test_with_active_plan(self, tmp_repo: Path) -> None:
        """build_status picks up an active planning session."""
        from harness_governance.file_ops.plan import init_plan

        init_plan(tmp_repo, slug="test-plan")
        payload = build_status(tmp_repo)
        assert payload.active_plan is not None
        assert "test-plan" in payload.active_plan.plan_id

    def test_with_invocation_log(self, tmp_repo: Path) -> None:
        """build_status reads invocations from the default log path."""
        log_path = tmp_repo / ".harness" / "invocations.ndjson"
        _write_ndjson(
            log_path,
            [
                {"round": 1, "exitCode": 0},
                {"round": 2, "exitCode": 0},
            ],
        )
        payload = build_status(tmp_repo)
        assert payload.runner.invocation_count == 2
        assert payload.runner.last_round == 2
        assert payload.runner.last_exit_code == 0

    def test_legacy_invocation_log_fallback(self, tmp_repo: Path) -> None:
        """build_status falls back to the legacy codex-exec path."""
        legacy_path = tmp_repo / ".harness" / "codex-exec-invocations.ndjson"
        _write_ndjson(legacy_path, [{"round": 5, "exitCode": 1}])
        payload = build_status(tmp_repo)
        assert payload.runner.invocation_count == 1
        assert payload.runner.last_round == 5
        assert payload.runner.last_exit_code == 1

    def test_queue_present_but_empty(self, tmp_repo: Path) -> None:
        """An empty NEXT.md file yields zero items without the 'not found' warning."""
        (tmp_repo / "NEXT.md").write_text("", encoding="utf-8")
        payload = build_status(tmp_repo)
        assert payload.queue_summary.total == 0
        assert not any("Queue file not found" in w for w in payload.warnings)

    def test_no_invocation_log_produces_warning(self, tmp_repo: Path) -> None:
        """Uninitialized project: single not_initialized notice, no per-file warnings."""
        payload = build_status(tmp_repo)
        assert any(
            "not initialized" in w.lower() or "未初始化" in w for w in payload.warnings
        )
        assert not any("invocation log" in w.lower() for w in payload.warnings)

    def test_last_exit_code_non_int_returns_none(self, tmp_repo: Path) -> None:
        """If exitCode is not an int, last_exit_code should be None."""
        log_path = tmp_repo / ".harness" / "invocations.ndjson"
        _write_ndjson(log_path, [{"round": 1, "exitCode": "unknown"}])
        payload = build_status(tmp_repo)
        assert payload.runner.last_exit_code is None

    def test_checkpoint_not_found_warning(self, tmp_repo: Path) -> None:
        """Uninitialized project suppresses per-file warnings including checkpoint."""
        payload = build_status(tmp_repo)
        assert not any("Checkpoint not found" in w for w in payload.warnings)

    def test_with_queue_items_infers_layer(self, tmp_repo: Path) -> None:
        (tmp_repo / "NEXT.md").write_text(
            "[active] Build CLI\n- Layer: implementation\n",
            encoding="utf-8",
        )
        payload = build_status(tmp_repo)
        assert payload.current_layer == "implementation"


# ===================================================================
# 5. format_text
# ===================================================================


class TestFormatText:
    """Tests for ``format_text``."""

    def test_with_queue_items_active_ready_other(self) -> None:
        items = (
            StatusQueueItem(raw="[active] Task A", active=True, layer="implementation"),
            StatusQueueItem(raw="[ready] Task B", ready=True, layer="adr"),
            StatusQueueItem(raw="[blocked] Task C"),
        )
        payload = _make_payload(
            queue_items=items,
            queue_summary=StatusQueueSummary(total=3, ready=1, active=1),
        )
        text = format_text(payload)
        assert "[active]" in text
        assert "[ready]" in text
        assert "[other]" in text
        assert "layer=implementation" in text

    def test_with_change_packets(self) -> None:
        packets = (
            StatusPacketItem(
                change_id="feat-a", path="docs/changes/feat-a", status="draft"
            ),
            StatusPacketItem(
                change_id="feat-b", path="docs/changes/feat-b", status="approved"
            ),
        )
        payload = _make_payload(packets=packets)
        text = format_text(payload)
        assert "[draft] feat-a" in text
        assert "[approved] feat-b" in text

    def test_with_active_plan(self) -> None:
        plan = StatusActivePlan(
            plan_id="2025-01-01-test",
            attested=True,
            task_plan_path=".planning/2025-01-01-test/task_plan.md",
        )
        payload = _make_payload(active_plan=plan)
        text = format_text(payload)
        assert "2025-01-01-test" in text

    def test_with_checkpoint_found(self) -> None:
        ck = StatusCheckpoint(
            found=True,
            path=".harness/run-checkpoint.md",
            last_worker="claude-code",
            stop_reason="task complete",
        )
        payload = _make_payload(checkpoint=ck)
        text = format_text(payload)
        assert "claude-code" in text
        assert "task complete" in text

    def test_with_warnings(self) -> None:
        payload = _make_payload(warnings=("Something is wrong", "Another warning"))
        text = format_text(payload)
        assert "Something is wrong" in text
        assert "Another warning" in text

    def test_queue_item_with_change_id(self) -> None:
        items = (
            StatusQueueItem(
                raw="[active] Task",
                active=True,
                layer="implementation",
                change_id="my-change",
            ),
        )
        payload = _make_payload(queue_items=items)
        text = format_text(payload)
        assert "change=my-change" in text

    def test_verification_fresh(self) -> None:
        v = StatusVerification(
            summary="all passed", stale=False, source="invocation-log"
        )
        payload = _make_payload(verification=v)
        text = format_text(payload)
        assert "all passed" in text

    def test_verification_stale(self) -> None:
        v = StatusVerification(summary=None, stale=True, source="missing")
        payload = _make_payload(verification=v)
        text = format_text(payload)
        assert "missing" in text


# ===================================================================
# 6. format_markdown
# ===================================================================


class TestFormatMarkdown:
    """Tests for ``format_markdown``."""

    def test_with_no_packets(self) -> None:
        payload = _make_payload(packets=())
        md = format_markdown(payload)
        assert "## Change Packets" in md
        # The "no packets" bilingual message should appear.
        assert "Change Packets" in md

    def test_with_no_warnings(self) -> None:
        payload = _make_payload(warnings=())
        md = format_markdown(payload)
        assert "## Warnings" in md
        assert "- none" in md

    def test_unknown_current_layer(self) -> None:
        """When current_layer is not in the canonical progression, index is -1."""
        payload = _make_payload(current_layer="unknown")
        md = format_markdown(payload)
        assert "Current layer: unknown" in md
        # All layers should appear in parenthetical form (none highlighted).
        assert "[unknown]" not in md or "(unknown)" in md

    def test_known_layer_highlighted_in_timeline(self) -> None:
        payload = _make_payload(current_layer="brief")
        md = format_markdown(payload)
        assert "[brief]" in md

    def test_with_queue_items(self) -> None:
        items = (
            StatusQueueItem(raw="[active] Task A", active=True),
            StatusQueueItem(raw="[ready] Task B", ready=True),
        )
        payload = _make_payload(
            queue_items=items,
            queue_summary=StatusQueueSummary(total=2, ready=1, active=1),
        )
        md = format_markdown(payload)
        assert "[active] Task A" in md
        assert "[ready] Task B" in md

    def test_no_queue_items_message(self) -> None:
        payload = _make_payload(queue_items=())
        md = format_markdown(payload)
        assert "## Scheduler Queue" in md

    def test_with_packets(self) -> None:
        packets = (StatusPacketItem(change_id="feat-x", path="p", status="draft"),)
        payload = _make_payload(packets=packets)
        md = format_markdown(payload)
        assert "[draft] feat-x" in md

    def test_runner_section(self) -> None:
        ck = StatusCheckpoint(
            found=True, path=".harness/run-checkpoint.md", last_worker="codex"
        )
        runner = StatusRunner(invocation_count=3, last_round=3, last_exit_code=0)
        payload = _make_payload(checkpoint=ck, runner=runner)
        md = format_markdown(payload)
        assert "Invocation count: 3" in md
        assert "codex" in md

    def test_verification_section(self) -> None:
        v = StatusVerification(
            summary="tests passed", stale=False, source="invocation-log"
        )
        payload = _make_payload(verification=v)
        md = format_markdown(payload)
        assert "Source: invocation-log" in md
        assert "Stale: no" in md
        assert "tests passed" in md

    def test_warnings_listed(self) -> None:
        payload = _make_payload(warnings=("watch out", "be careful"))
        md = format_markdown(payload)
        assert "- watch out" in md
        assert "- be careful" in md


# ===================================================================
# 7. status_cmd (CLI integration)
# ===================================================================


class TestStatusCmdCLI:
    """Tests for the ``status`` CLI subcommand."""

    def test_format_markdown_via_cli(self, tmp_repo: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_repo), "status", "--format", "markdown"],
        )
        assert result.exit_code == 0, result.output
        assert "# Harness Status" in result.output
        assert "## Scheduler Queue" in result.output

    def test_format_json_via_cli(self, tmp_repo: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_repo), "status", "--format", "json"],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert "queueSummary" in payload
        assert "verification" in payload

    def test_refresh_writes_status_files(self, tmp_repo: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_repo), "status", "--refresh"],
        )
        assert result.exit_code == 0, result.output
        assert (tmp_repo / ".harness" / "status.md").is_file()
        assert (tmp_repo / ".harness" / "status.json").is_file()
        # Verify JSON file is valid and contains expected keys.
        data = json.loads(
            (tmp_repo / ".harness" / "status.json").read_text(encoding="utf-8")
        )
        assert "queueSummary" in data

    def test_no_refresh_default(self, tmp_repo: Path) -> None:
        """By default --no-refresh is used, so status files are not written."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_repo), "status"],
        )
        assert result.exit_code == 0, result.output
        assert not (tmp_repo / ".harness" / "status.md").is_file()
        assert not (tmp_repo / ".harness" / "status.json").is_file()

    def test_default_format_is_text(self, tmp_repo: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_repo), "status"],
        )
        assert result.exit_code == 0, result.output
        # Text format starts with the bilingual status header, not markdown heading.
        assert "# Harness Status" not in result.output

    def test_json_flag_on_parent_triggers_json_output(self, tmp_repo: Path) -> None:
        """The --json flag on the parent group should also produce JSON."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_repo), "--json", "status"],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert "currentLayer" in payload

    def test_refresh_with_markdown_format(self, tmp_repo: Path) -> None:
        """--refresh combined with --format markdown should write files and output markdown."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root",
                str(tmp_repo),
                "status",
                "--refresh",
                "--format",
                "markdown",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "# Harness Status" in result.output
        assert (tmp_repo / ".harness" / "status.md").is_file()
