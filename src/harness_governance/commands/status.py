"""``harness status`` command.

Aggregates queue, change packets, planning session, checkpoint, and
invocation log into a single Markdown / JSON view. Mirrors the legacy
``harness-visualization/scripts/harness-status.mjs`` (text subset).
"""

from __future__ import annotations

import json as _json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import click

from ..config.settings import load_config
from ..file_ops import packet as packet_ops
from ..file_ops import plan as plan_ops
from ..file_ops.checkpoint import Checkpoint
from ..file_ops.queue import read_queue
from ..logging_setup import get_logger
from ..messages import bilingual
from ..models.schemas import (
    HarnessConfig,
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
from ..state_machine.layers import canonical_progression

logger = get_logger("status")

DEFAULT_CONFIG_PATH = Path(".harness/harness-status.config.json")
DEFAULT_PROJECT_CONFIG: dict[str, str] = {
    "queue": "NEXT.md",
    "checkpoint": ".harness/run-checkpoint.md",
    "invocationLog": ".harness/invocations.ndjson",
    "changes": "docs/changes",
    "archive": "docs/changes/archive",
    "statusMd": ".harness/status.md",
    "statusJson": ".harness/status.json",
}

# Legacy paths for backward compatibility (de-codex migration).
_LEGACY_INVOCATION_LOG = ".harness/codex-exec-invocations.ndjson"


def _read_invocation_log(path: Path) -> tuple[list[dict], list[str]]:
    warnings: list[str] = []
    if not path.is_file():
        return [], [f"Invocation log not found or empty: {path}"]
    records: list[dict] = []
    for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        try:
            records.append(_json.loads(line))
        except _json.JSONDecodeError as exc:
            warnings.append(f"Could not parse invocation log line {index}: {exc}")
    return records, warnings


def _summarise_verification(
    checkpoint: Checkpoint,
    invocations: list[dict],
) -> StatusVerification:
    last = invocations[-1] if invocations else None
    summary = None
    if last:
        summary = last.get("verificationSummary") or last.get("verification")
    text = (summary or " ".join(["- " + v for v in (checkpoint.verification or "").splitlines() if v.strip()])).lower()
    if not summary and checkpoint.verification:
        # Use the first non-empty line.
        for line in checkpoint.verification.splitlines():
            stripped = line.strip().lstrip("-").strip()
            if stripped:
                summary = stripped
                break
    has_pass = bool(re.search(r"\bpass(?:ed)?\b|->\s*pass\b", text))
    has_fail = bool(re.search(r"\bfail(?:ed)?\b|->\s*fail\b", text))
    return StatusVerification(
        summary=summary,
        stale=(not summary) or has_fail or not has_pass,
        failed=has_fail,
        source="invocation-log" if last and (last.get("verificationSummary") or last.get("verification")) else (
            "checkpoint" if checkpoint.verification else "missing"
        ),
    )


def _infer_current_layer(items: Iterable[QueueItem]) -> str | None:
    for item in items:
        if item.active and item.layer:
            return item.layer.value
    for item in items:
        if item.ready and item.layer:
            return item.layer.value
    for item in items:
        if item.layer:
            return item.layer.value
    return None


def build_status(
    repo_root: Path,
    *,
    config: HarnessConfig | None = None,
) -> StatusPayload:
    """Build the status payload (mirrors the legacy script, text subset).

    When *config* is provided, path fields from
    :class:`~harness_governance.models.schemas.HarnessConfig` are used
    instead of the hardcoded :data:`DEFAULT_PROJECT_CONFIG`.  When
    ``None``, the config is loaded automatically from *repo_root*.

    Gracefully degrades when the project is not initialized (no
    ``.harness/config.toml``): returns a clean empty state with a
    single informational notice instead of noisy warnings.
    """
    if config is None:
        config = load_config(repo_root)
    logger.debug("using config: queue_file=%s changes_root=%s harness_dir=%s",
                 config.queue_file, config.changes_root, config.harness_dir)

    # Detect uninitialized project: no config file and no .harness directory.
    harness_dir = config.harness_dir
    config_file = harness_dir / "config.toml"
    initialized = config_file.is_file() or harness_dir.is_dir()

    queue_path = config.queue_file  # already absolute after load_config
    items = read_queue(queue_path)

    warnings: list[str] = []
    if not initialized:
        warnings.append(bilingual("status.not_initialized"))
    # Clean: no queue items is a valid state — no warning needed.

    packet_dirs = packet_ops.discover_packets(repo_root)
    summaries = [
        packet_ops.check_packet(d, project_root=repo_root)[1]
        for d in packet_dirs
    ]

    active_plan = plan_ops.resolve_active_plan(repo_root)

    checkpoint_path = harness_dir / "run-checkpoint.md"
    checkpoint = Checkpoint.load(checkpoint_path)

    inv_log_path = harness_dir / "invocations.ndjson"
    invocations: list[dict] = []
    # Backward compatibility: fall back to legacy codex-exec path.
    if not inv_log_path.is_file():
        legacy = repo_root / _LEGACY_INVOCATION_LOG
        if legacy.is_file():
            inv_log_path = legacy
    if inv_log_path.is_file():
        invocations, log_warnings = _read_invocation_log(inv_log_path)
        warnings.extend(log_warnings)

    verification = _summarise_verification(checkpoint, invocations)
    # Only flag verification staleness if the project is initialized.
    if initialized and verification.stale:
        warnings.append("Verification is missing, failed, or stale.")

    current_layer = _infer_current_layer(items) or "unknown"

    return StatusPayload(
        repo=str(repo_root),
        generated_at=datetime.now(timezone.utc).isoformat(),
        current_layer=current_layer,
        queue_summary=StatusQueueSummary(
            total=len(items),
            ready=sum(1 for i in items if i.ready),
            active=sum(1 for i in items if i.active),
        ),
        queue_items=tuple(
            StatusQueueItem(
                raw=i.raw,
                active=i.active,
                ready=i.ready,
                layer=i.layer.value if i.layer else None,
                change_id=i.change_id,
            )
            for i in items
        ),
        packets=tuple(
            StatusPacketItem(
                change_id=s.change_id,
                path=str(s.path),
                status=s.status,
            )
            for s in summaries
        ),
        active_plan=(
            StatusActivePlan(
                plan_id=active_plan.plan_id,
                attested=active_plan.attested,
                task_plan_path=str(active_plan.task_plan_path),
            )
            if active_plan
            else None
        ),
        checkpoint=StatusCheckpoint(
            found=checkpoint_path.is_file(),
            path=str(checkpoint_path),
            last_worker=checkpoint.last_worker,
            verification=checkpoint.verification,
            stop_reason=checkpoint.stop_reason,
        ),
        runner=StatusRunner(
            invocation_count=len(invocations),
            last_round=(invocations[-1].get("round") if invocations else None),
            last_exit_code=(
                invocations[-1].get("exitCode")
                if invocations and isinstance(invocations[-1].get("exitCode"), int)
                else None
            ),
        ),
        verification=verification,
        warnings=tuple(warnings),
    )


def format_text(status: StatusPayload) -> str:
    lines = [
        bilingual("status.header", path=status.repo),
        bilingual("status.generated", ts=status.generated_at),
        bilingual("status.current_layer", layer=status.current_layer),
        "",
        bilingual(
            "status.scheduler_queue",
            total=status.queue_summary.total,
            ready=status.queue_summary.ready,
            active=status.queue_summary.active,
        ),
    ]

    if status.queue_items:
        lines.append("")
        lines.append(bilingual("status.queue_items"))
        for item in status.queue_items:
            details = " ".join(
                part for part in (
                    f"layer={item.layer}" if item.layer else "",
                    f"change={item.change_id}" if item.change_id else "",
                ) if part
            )
            tag = "active" if item.active else "ready" if item.ready else "other"
            lines.append(f"- [{tag}] {item.raw.splitlines()[0]}{(' (' + details + ')') if details else ''}")

    if status.packets:
        lines.append("")
        lines.append(bilingual("status.change_packets"))
        for p in status.packets:
            lines.append(f"- [{p.status}] {p.change_id}")

    if status.active_plan is not None:
        plan = status.active_plan
        state = bilingual("status.plan_state_attested") if plan.attested else bilingual("status.plan_state_unattested")
        lines.append("")
        lines.append(bilingual("status.active_plan", plan_id=plan.plan_id, state=state))

    if status.checkpoint.found:
        ck = status.checkpoint
        lines.append("")
        lines.append(bilingual("status.checkpoint_header"))
        if ck.last_worker:
            lines.append("- " + bilingual("status.last_worker", value=ck.last_worker))
        if ck.stop_reason:
            lines.append("- " + bilingual("status.stop_reason", value=ck.stop_reason))

    state = bilingual("status.verification_stale") if status.verification.stale else bilingual("status.verification_fresh")
    lines.append("")
    lines.append(
        bilingual(
            "status.verification_line",
            state=state,
            summary=status.verification.summary or "missing",
        )
    )

    if status.warnings:
        lines.append("")
        lines.append(bilingual("status.warnings_header"))
        for w in status.warnings:
            lines.append(f"- {w}")

    return "\n".join(lines) + "\n"


def format_markdown(status: StatusPayload) -> str:
    """Markdown view (subset of the legacy ``formatMarkdown``)."""
    progression = canonical_progression()
    try:
        current_index = progression.index(status.current_layer)
    except ValueError:
        current_index = -1
    timeline_parts: list[str] = []
    for idx, label in enumerate(progression):
        if idx == current_index:
            timeline_parts.append(f"[{label.value}]")
        elif current_index >= 0 and idx < current_index:
            timeline_parts.append(label.value)
        else:
            timeline_parts.append(f"({label.value})")
    timeline = " -> ".join(timeline_parts)

    lines = [
        "# Harness Status",
        "",
        f"Generated: {status.generated_at}",
        f"Repo: {status.repo}",
        "",
        f"Harness: {timeline}",
        f"Current layer: {status.current_layer}",
        "",
        "## Scheduler Queue",
        "",
        f"Scheduler total: {status.queue_summary.total}; "
        f"ready: {status.queue_summary.ready}; "
        f"active: {status.queue_summary.active}",
        "",
    ]
    if not status.queue_items:
        lines.append("- " + bilingual("status.no_scheduled_items"))
    else:
        for item in status.queue_items:
            tag = "active" if item.active else "ready" if item.ready else "other"
            lines.append(f"- [{tag}] {item.raw.splitlines()[0]}")
    lines.append("")
    lines.append("## Change Packets")
    lines.append("")
    if not status.packets:
        lines.append("- " + bilingual("status.no_change_packets"))
    else:
        for p in status.packets:
            lines.append(f"- [{p.status}] {p.change_id}")
    lines.append("")
    lines.append("## Runner")
    lines.append("")
    ck = status.checkpoint
    lines.append(f"- Checkpoint: {ck.path} ({'found' if ck.found else 'missing'})")
    lines.append(f"- Last worker: {ck.last_worker or 'unknown'}")
    lines.append(f"- Stop reason: {ck.stop_reason or 'none'}")
    lines.append(f"- Invocation count: {status.runner.invocation_count}")
    lines.append("")
    lines.append("## Verification")
    lines.append("")
    lines.append(f"- Source: {status.verification.source}")
    lines.append(f"- Stale: {'yes' if status.verification.stale else 'no'}")
    lines.append(f"- Summary: {status.verification.summary or 'missing'}")
    lines.append("")
    lines.append("## Warnings")
    lines.append("")
    if not status.warnings:
        lines.append("- none")
    else:
        for w in status.warnings:
            lines.append(f"- {w}")
    return "\n".join(lines) + "\n"


@click.command("status")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["text", "markdown", "json"]),
    default="text",
    show_default=True,
    help="Output format.",
)
@click.option("--refresh/--no-refresh", default=False, help="Write .harness/status.{md,json}.")
@click.pass_context
def status_cmd(ctx: click.Context, fmt: str, refresh: bool) -> None:
    """Aggregate queue, packets, checkpoint, and verification."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    config = load_config(project_root)
    status = build_status(project_root, config=config)

    if refresh:
        status_md = config.harness_dir / "status.md"
        status_json = config.harness_dir / "status.json"
        status_md.parent.mkdir(parents=True, exist_ok=True)
        status_md.write_text(format_markdown(status), encoding="utf-8")
        status_json.write_text(status.model_dump_json(indent=2, by_alias=True), encoding="utf-8")
        click.echo(bilingual("status.wrote_md", path=str(status_md)))
        click.echo(bilingual("status.wrote_md", path=str(status_json)))

    if ctx.obj.get("json_output") or fmt == "json":
        click.echo(status.model_dump_json(indent=2, by_alias=True))
        return
    if fmt == "markdown":
        click.echo(format_markdown(status), nl=False)
        return
    click.echo(format_text(status), nl=False)


__all__ = [
    "status_cmd",
    "build_status",
    "format_markdown",
    "format_text",
    "StatusPayload",
]
