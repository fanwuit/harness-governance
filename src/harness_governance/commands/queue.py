"""``harness queue`` commands."""

from __future__ import annotations

from typing import Any

from datetime import datetime, timezone
from pathlib import Path

import click

from ..config import load_config
from ..file_ops.queue import (
    append_structured_queue_item,
    mark_queue_item_done,
    mark_queue_item_status,
    read_queue,
)
from ..messages import bilingual
from ..session import find_active_session
from ..queue_validation import validate_queue
from .check import _emit


def _queue_path(project_root: Path) -> Path:
    return load_config(project_root).queue_file


def _find_item(items, item_id: str):
    lowered = item_id.lower()
    for item in items:
        if item.id and item.id.lower() == lowered:
            return item
        if item.session_id and item.session_id.lower() == lowered:
            return item
        if item.change_id and item.change_id.lower() == lowered:
            return item
    return None


def _validate_review_start(items, item, session_id: str) -> None:
    if item is None or item.role != "reviewer-verifier":
        return
    by_id: dict[str, Any] = {}
    for candidate in items:
        for key in (candidate.id, candidate.session_id, candidate.change_id):
            if key:
                by_id.setdefault(key, candidate)
    deps = [by_id.get(dep_id) for dep_id in item.depends_on]
    impl_deps = [dep for dep in deps if dep and dep.role == "implementer"]
    if not impl_deps:
        raise click.ClickException(
            "reviewer-verifier queue item must dependOn an implementer item."
        )
    for dep in impl_deps:
        if dep.status != "done":
            raise click.ClickException(
                f"dependsOn implementation item '{dep.id or dep.session_id}' "
                "must be done before review."
            )
        if dep.session_id and dep.session_id == session_id:
            raise click.ClickException(
                "reviewer-verifier sessionId must differ from implementation."
            )


def _echo_items(ctx: click.Context, items) -> None:
    if ctx.obj.get("json_output"):
        import json

        click.echo(
            json.dumps(
                [item.model_dump() for item in items], indent=2, ensure_ascii=False
            )
        )
        return
    if not items:
        click.echo("queue empty")
        return
    for item in items:
        status = item.status or (
            "active" if item.active else "ready" if item.ready else "-"
        )
        layer = item.layer.value if item.layer else "-"
        role = item.role or "-"
        session = item.session_id or "-"
        click.echo(
            f"{status:>8}  {item.id or item.change_id or '-':<24} "
            f"layer={layer:<18} role={role:<22} session={session}"
        )


@click.group("queue")
def queue_group() -> None:
    """Inspect and validate the scheduler queue."""


@queue_group.command("validate")
@click.pass_context
def queue_validate_cmd(ctx: click.Context) -> None:
    """Validate configured queue file item structure."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    _emit(ctx, validate_queue(project_root))


@queue_group.command("add")
@click.argument("item_id")
@click.argument("description")
@click.option("--status", default="planned", show_default=True)
@click.option("--layer", default=None)
@click.option("--role", default=None)
@click.option("--gate-id", "gate_id", default=None)
@click.option("--change-id", "change_id", default=None)
@click.option("--change-kind", "change_kind", default=None)
@click.option("--depends-on", "depends_on", multiple=True)
@click.option("--owner-file", "owner_files", multiple=True)
@click.option(
    "--session-id",
    "session_id",
    default=None,
    help=(
        "Execution session binding. Optional while queued; active/done role "
        "items must have one."
    ),
)
@click.option("--verification", default=None)
@click.option("--stop-conditions", "stop_conditions", default=None)
@click.option("--handoff-from", "handoff_from", default=None)
@click.pass_context
def queue_add_cmd(
    ctx: click.Context,
    item_id: str,
    description: str,
    status: str,
    layer: str | None,
    role: str | None,
    gate_id: str | None,
    change_id: str | None,
    change_kind: str | None,
    depends_on: tuple[str, ...],
    owner_files: tuple[str, ...],
    session_id: str | None,
    verification: str | None,
    stop_conditions: str | None,
    handoff_from: str | None,
) -> None:
    """Append a structured queue item."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    queue_path = _queue_path(project_root)
    added = append_structured_queue_item(
        queue_path,
        item_id=item_id,
        description=description,
        status=status,
        layer=layer,
        role=role,
        gate_id=gate_id,
        change_id=change_id,
        change_kind=change_kind,
        depends_on=depends_on,
        owner_files=owner_files,
        session_id=session_id,
        verification=verification,
        stop_conditions=stop_conditions,
        handoff_from=handoff_from,
    )
    if not added:
        raise click.ClickException(f"Queue item already exists: {item_id}")
    click.echo(bilingual("queue.added", item_id=item_id, path=str(queue_path)))


@queue_group.command("list")
@click.pass_context
def queue_list_cmd(ctx: click.Context) -> None:
    """List queue items in compact form."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    items = read_queue(_queue_path(project_root))
    _echo_items(ctx, items)


@queue_group.command("next")
@click.pass_context
def queue_next_cmd(ctx: click.Context) -> None:
    """Show the next actionable queue item."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    items = read_queue(_queue_path(project_root))
    target = next((i for i in items if i.ready or i.active), None) or next(
        (i for i in items if i.status == "planned" or not i.status), None
    )
    if target is None:
        raise click.ClickException("No actionable queue item found.")
    _echo_items(ctx, [target])


@queue_group.command("start")
@click.argument("item_id")
@click.option(
    "--session-id",
    "session_id",
    default=None,
    help="Execution session to bind while marking the queue item active.",
)
@click.pass_context
def queue_start_cmd(ctx: click.Context, item_id: str, session_id: str | None) -> None:
    """Mark a queue item active and attach a session id."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    queue_path = _queue_path(project_root)
    items = read_queue(queue_path)
    item = _find_item(items, item_id)
    if session_id is None:
        active = find_active_session(project_root)
        if active is None:
            raise click.ClickException(
                "No active governance session found. Pass --session-id or "
                "start a governed session first."
            )
        session_id = active.session_id
    _validate_review_start(items, item, session_id)
    if not mark_queue_item_status(
        queue_path,
        task_id=item_id,
        status="active",
        session_id=session_id,
    ):
        raise click.ClickException(f"Queue item not found: {item_id}")
    click.echo(bilingual("queue.started", item_id=item_id, session_id=session_id))


@queue_group.command("block")
@click.argument("item_id")
@click.option("--reason", default="blocked", show_default=True)
@click.pass_context
def queue_block_cmd(ctx: click.Context, item_id: str, reason: str) -> None:
    """Mark a queue item blocked."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    if not mark_queue_item_status(
        _queue_path(project_root),
        task_id=item_id,
        status="blocked",
        risks=(reason,),
    ):
        raise click.ClickException(f"Queue item not found: {item_id}")
    click.echo(bilingual("queue.blocked", item_id=item_id))


@queue_group.command("finish")
@click.argument("item_id")
@click.option(
    "--evidence",
    "evidence",
    multiple=True,
    help="Evidence line; pass multiple times to record several.",
)
@click.option(
    "--risk",
    "risks",
    multiple=True,
    help="Risk line; pass multiple times to record several.",
)
@click.option("--session-id", "session_id", default=None)
@click.pass_context
def queue_finish_cmd(
    ctx: click.Context,
    item_id: str,
    evidence: tuple[str, ...],
    risks: tuple[str, ...],
    session_id: str | None,
) -> None:
    """Mark a queue item done and persist closeout details."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    queue_path = _queue_path(project_root)
    items = read_queue(queue_path)
    item = next(
        (
            i
            for i in items
            if item_id in {i.id, i.session_id, i.change_id}
            or i.raw.lower().startswith("[active]")
            and item_id in i.raw
        ),
        None,
    )
    resolved_session = session_id or (item.session_id if item else None)
    if resolved_session is None:
        active = find_active_session(project_root)
        resolved_session = active.session_id if active else None
    if resolved_session is None:
        raise click.ClickException(
            "No session id found for queue finish. Pass --session-id or "
            "start a governed session first."
        )
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    if not mark_queue_item_done(
        queue_path,
        task_id=item_id,
        evidence=evidence,
        risks=risks,
        session_id=resolved_session,
        completed_at=timestamp,
    ):
        raise click.ClickException(f"Queue item not found: {item_id}")
    click.echo(
        bilingual(
            "queue.finished",
            item_id=item_id,
            session_id=resolved_session,
        )
    )


__all__ = [
    "queue_group",
    "queue_validate_cmd",
    "queue_add_cmd",
    "queue_list_cmd",
    "queue_next_cmd",
    "queue_start_cmd",
    "queue_block_cmd",
    "queue_finish_cmd",
]
