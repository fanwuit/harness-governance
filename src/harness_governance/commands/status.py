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

from ..file_ops import packet as packet_ops
from ..file_ops import plan as plan_ops
from ..file_ops.checkpoint import Checkpoint
from ..file_ops.queue import read_queue
from ..models.schemas import QueueItem, StatusView
from ..state_machine.layers import canonical_progression

DEFAULT_CONFIG_PATH = Path(".harness/harness-status.config.json")
DEFAULT_PROJECT_CONFIG: dict[str, str] = {
    "queue": "NEXT.md",
    "checkpoint": ".harness/run-checkpoint.md",
    "invocationLog": ".harness/codex-exec-invocations.ndjson",
    "changes": "docs/changes",
    "archive": "docs/changes/archive",
    "statusMd": ".harness/status.md",
    "statusJson": ".harness/status.json",
}


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
) -> dict:
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
    return {
        "summary": summary,
        "stale": (not summary) or has_fail or not has_pass,
        "failed": has_fail,
        "source": "invocation-log" if last and (last.get("verificationSummary") or last.get("verification")) else (
            "checkpoint" if checkpoint.verification else "missing"
        ),
    }


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


def build_status(repo_root: Path) -> dict:
    """Build the status payload (mirrors the legacy script, text subset)."""
    queue_path = repo_root / DEFAULT_PROJECT_CONFIG["queue"]
    items = read_queue(queue_path)
    queue_present = queue_path.is_file()

    warnings: list[str] = []
    if not queue_present:
        warnings.append(f"Queue file not found: {queue_path}")

    packet_dirs = packet_ops.discover_packets(repo_root)
    summaries = [
        packet_ops.check_packet(d, project_root=repo_root)[1]
        for d in packet_dirs
    ]

    active_plan = plan_ops.resolve_active_plan(repo_root)
    checkpoint_path = repo_root / DEFAULT_PROJECT_CONFIG["checkpoint"]
    checkpoint = Checkpoint.load(checkpoint_path)
    if not checkpoint_path.is_file():
        warnings.append(f"Checkpoint not found: {checkpoint_path}")

    invocations, log_warnings = _read_invocation_log(
        repo_root / DEFAULT_PROJECT_CONFIG["invocationLog"]
    )
    warnings.extend(log_warnings)
    if not invocations:
        warnings.append(
            f"Invocation log not found or empty: {DEFAULT_PROJECT_CONFIG['invocationLog']}"
        )

    verification = _summarise_verification(checkpoint, invocations)
    if verification["stale"]:
        warnings.append("Verification is missing, failed, or stale.")

    current_layer = _infer_current_layer(items) or "unknown"

    return {
        "repo": str(repo_root),
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "currentLayer": current_layer,
        "queueSummary": {
            "total": len(items),
            "ready": sum(1 for i in items if i.ready),
            "active": sum(1 for i in items if i.active),
        },
        "queueItems": [
            {
                "raw": i.raw,
                "active": i.active,
                "ready": i.ready,
                "layer": i.layer.value if i.layer else None,
                "change_id": i.change_id,
            }
            for i in items
        ],
        "packets": [
            {
                "change_id": s.change_id,
                "path": str(s.path),
                "status": s.status,
            }
            for s in summaries
        ],
        "activePlan": (
            {
                "plan_id": active_plan.plan_id,
                "attested": active_plan.attested,
                "task_plan_path": str(active_plan.task_plan_path),
            }
            if active_plan
            else None
        ),
        "checkpoint": {
            "found": checkpoint_path.is_file(),
            "path": str(checkpoint_path),
            "last_worker": checkpoint.last_worker,
            "verification": checkpoint.verification,
            "stop_reason": checkpoint.stop_reason,
        },
        "runner": {
            "invocationCount": len(invocations),
            "lastRound": (invocations[-1].get("round") if invocations else None),
            "lastExitCode": (
                invocations[-1].get("exitCode")
                if invocations and isinstance(invocations[-1].get("exitCode"), int)
                else None
            ),
        },
        "verification": verification,
        "warnings": warnings,
    }


def format_text(status: dict) -> str:
    lines = [
        f"Harness status for {status['repo']}",
        f"Generated: {status['generatedAt']}",
        f"Current layer: {status['currentLayer']}",
        "",
        f"Scheduler queue: total={status['queueSummary']['total']} "
        f"ready={status['queueSummary']['ready']} "
        f"active={status['queueSummary']['active']}",
    ]

    if status["queueItems"]:
        lines.append("")
        lines.append("Queue items:")
        for item in status["queueItems"]:
            details = " ".join(
                part for part in (
                    f"layer={item['layer']}" if item["layer"] else "",
                    f"change={item['change_id']}" if item["change_id"] else "",
                ) if part
            )
            tag = "active" if item["active"] else "ready" if item["ready"] else "other"
            lines.append(f"- [{tag}] {item['raw'].splitlines()[0]}{(' (' + details + ')') if details else ''}")

    if status["packets"]:
        lines.append("")
        lines.append("Change packets:")
        for p in status["packets"]:
            lines.append(f"- [{p['status']}] {p['change_id']}")

    if status["activePlan"]:
        plan = status["activePlan"]
        attested = "attested" if plan["attested"] else "not attested"
        lines.append("")
        lines.append(f"Active plan: {plan['plan_id']} ({attested})")

    if status["checkpoint"]["found"]:
        ck = status["checkpoint"]
        lines.append("")
        lines.append("Checkpoint:")
        if ck["last_worker"]:
            lines.append(f"- last worker: {ck['last_worker']}")
        if ck["stop_reason"]:
            lines.append(f"- stop reason: {ck['stop_reason']}")

    lines.append("")
    lines.append(
        f"Verification: "
        f"{'stale' if status['verification']['stale'] else 'fresh'} "
        f"({status['verification']['summary'] or 'missing'})"
    )

    if status["warnings"]:
        lines.append("")
        lines.append("Warnings:")
        for w in status["warnings"]:
            lines.append(f"- {w}")

    return "\n".join(lines) + "\n"


def format_markdown(status: dict) -> str:
    """Markdown view (subset of the legacy ``formatMarkdown``)."""
    progression = canonical_progression()
    try:
        current_index = progression.index(status["currentLayer"])
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
        f"Generated: {status['generatedAt']}",
        f"Repo: {status['repo']}",
        "",
        f"Harness: {timeline}",
        f"Current layer: {status['currentLayer']}",
        "",
        "## Scheduler Queue",
        "",
        f"Scheduler total: {status['queueSummary']['total']}; "
        f"ready: {status['queueSummary']['ready']}; "
        f"active: {status['queueSummary']['active']}",
        "",
    ]
    if not status["queueItems"]:
        lines.append("- No scheduler items found.")
    else:
        for item in status["queueItems"]:
            tag = "active" if item["active"] else "ready" if item["ready"] else "other"
            lines.append(f"- [{tag}] {item['raw'].splitlines()[0]}")
    lines.append("")
    lines.append("## Change Packets")
    lines.append("")
    if not status["packets"]:
        lines.append("- No change packets found.")
    else:
        for p in status["packets"]:
            lines.append(f"- [{p['status']}] {p['change_id']}")
    lines.append("")
    lines.append("## Runner")
    lines.append("")
    ck = status["checkpoint"]
    lines.append(f"- Checkpoint: {ck['path']} ({'found' if ck['found'] else 'missing'})")
    lines.append(f"- Last worker: {ck['last_worker'] or 'unknown'}")
    lines.append(f"- Stop reason: {ck['stop_reason'] or 'none'}")
    lines.append(f"- Invocation count: {status['runner']['invocationCount']}")
    lines.append("")
    lines.append("## Verification")
    lines.append("")
    lines.append(f"- Source: {status['verification']['source']}")
    lines.append(f"- Stale: {'yes' if status['verification']['stale'] else 'no'}")
    lines.append(f"- Summary: {status['verification']['summary'] or 'missing'}")
    lines.append("")
    lines.append("## Warnings")
    lines.append("")
    if not status["warnings"]:
        lines.append("- none")
    else:
        for w in status["warnings"]:
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
    status = build_status(project_root)

    if refresh:
        status_md = project_root / DEFAULT_PROJECT_CONFIG["statusMd"]
        status_json = project_root / DEFAULT_PROJECT_CONFIG["statusJson"]
        status_md.parent.mkdir(parents=True, exist_ok=True)
        status_md.write_text(format_markdown(status), encoding="utf-8")
        status_json.write_text(_json.dumps(status, indent=2), encoding="utf-8")
        click.echo(f"Wrote {status_md}")
        click.echo(f"Wrote {status_json}")

    if ctx.obj.get("json_output") or fmt == "json":
        click.echo(_json.dumps(status, indent=2))
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
]