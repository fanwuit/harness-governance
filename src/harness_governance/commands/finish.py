"""``harness finish`` command.

Provides a single, explicit closeout entry point for agents and humans.
It delegates to the existing review closeout logic so checkpoint, NEXT.md,
and matching session state stay linked.
"""

from __future__ import annotations

from pathlib import Path

import click

from ..messages import bilingual
from .review import close_task


@click.command("finish")
@click.argument("session_id")
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
@click.option(
    "--checkpoint",
    "checkpoint",
    type=click.Path(dir_okay=False, path_type=Path),
    default=Path(".harness/run-checkpoint.md"),
    show_default=True,
    help="Checkpoint file to update.",
)
@click.option(
    "--next-resume",
    "next_resume",
    default=None,
    help="Pointer to the next resume source.",
)
@click.pass_context
def finish_cmd(
    ctx: click.Context,
    session_id: str,
    evidence: tuple[str, ...],
    risks: tuple[str, ...],
    checkpoint: Path,
    next_resume: str | None,
) -> None:
    """Finish a governed task and synchronize local state."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    target = close_task(
        project_root,
        session_id,
        evidence=evidence,
        risks=risks,
        checkpoint=checkpoint,
        next_resume=next_resume,
    )
    click.echo(bilingual("review.recorded", task_id=session_id, path=str(target)))
    click.echo(f"Finished: {session_id}")


__all__ = ["finish_cmd"]
