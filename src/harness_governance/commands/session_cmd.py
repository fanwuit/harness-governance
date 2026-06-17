"""``harness session`` commands — inspect and manage governance sessions.

Provides ``show``, ``list``, and ``close`` subcommands for the session
lifecycle.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import click

from ..messages import bilingual
from ..session import (
    SessionState,
    find_active_session,
    list_sessions,
    load_session,
    save_session,
)


@click.group("session")
def session_group() -> None:
    """Inspect and manage governance sessions."""


@session_group.command("show")
@click.argument("session_id", required=False, default=None)
@click.pass_context
def session_show_cmd(ctx: click.Context, session_id: str | None) -> None:
    """Show details of a governance session (defaults to active session)."""
    project_root: "Path" = ctx.obj["project_root"]

    state: SessionState
    if session_id:
        try:
            state = load_session(project_root, session_id)
        except FileNotFoundError:
            raise click.ClickException(
                bilingual("session.not_found", session_id=session_id)
            )
    else:
        _state = find_active_session(project_root)
        if _state is None:
            raise click.ClickException(bilingual("session.no_active"))
        state = _state

    if ctx.obj.get("json_output"):
        click.echo(state.model_dump_json(indent=2))
        return

    click.echo(bilingual("session.header", session_id=state.session_id))
    click.echo(bilingual("session.description", text=state.description))
    click.echo(bilingual("session.routing_path", path=state.routing_path.value))
    layer_name = state.current_layer.value if state.current_layer else "-"
    click.echo(bilingual("session.current_layer", layer=layer_name))
    click.echo(bilingual("session.status_line", status=state.status))
    if state.change_id:
        click.echo(bilingual("session.change_id", change_id=state.change_id))
    if state.closed_at:
        click.echo(f"Closed at: {state.closed_at}")
    click.echo(bilingual("session.transitions_header", count=len(state.transitions)))
    for t in state.transitions:
        status = "OK" if t.engine_verdict else "BLOCKED"
        line = (
            f"  {t.from_layer.value} -> {t.to_layer.value}  [{status}]  {t.timestamp}"
        )
        if t.violations:
            line += f"  ({'; '.join(t.violations)})"
        click.echo(line)


@session_group.command("list")
@click.pass_context
def session_list_cmd(ctx: click.Context) -> None:
    """List all governance sessions (active and closed)."""
    project_root: "Path" = ctx.obj["project_root"]
    sessions = list_sessions(project_root)

    if not sessions:
        click.echo(bilingual("session.no_sessions"))
        return

    if ctx.obj.get("json_output"):
        click.echo(
            json.dumps(
                [json.loads(s.model_dump_json()) for s in sessions],
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    for s in sessions:
        layer_name = s.current_layer.value if s.current_layer else "-"
        marker = "*" if s.status == "active" else " "
        click.echo(
            f"{marker} {s.session_id}  [{s.status}]  "
            f"layer={layer_name}  {s.description[:60]}"
        )


@session_group.command("close")
@click.argument("session_id")
@click.pass_context
def session_close_cmd(ctx: click.Context, session_id: str) -> None:
    """Close a governance session (mark as done)."""
    project_root: "Path" = ctx.obj["project_root"]

    try:
        state = load_session(project_root, session_id)
    except FileNotFoundError:
        raise click.ClickException(
            bilingual("session.not_found", session_id=session_id)
        )

    if state.status == "closed":
        click.echo(bilingual("session.already_closed", session_id=session_id))
        return

    state = state.model_copy(
        update={
            "status": "closed",
            "closed_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    save_session(project_root, state)

    if ctx.obj.get("json_output"):
        click.echo(
            json.dumps(
                {
                    "session_id": state.session_id,
                    "status": "closed",
                    "closed_at": state.closed_at,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        click.echo(bilingual("session.closed", session_id=session_id))


__all__ = ["session_group", "session_show_cmd", "session_list_cmd", "session_close_cmd"]
