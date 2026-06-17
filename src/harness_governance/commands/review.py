"""``harness review close <task-id>`` command."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import click

from ..file_ops.checkpoint import Checkpoint
from ..messages import bilingual


@click.group("review")
def review_group() -> None:
    """Close out tasks; persist review/next state."""


@review_group.command("close")
@click.argument("task_id")
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
    help="Pointer to the next resume source (queue item, ADR, …).",
)
@click.pass_context
def review_close_cmd(
    ctx: click.Context,
    task_id: str,
    evidence: tuple[str, ...],
    risks: tuple[str, ...],
    checkpoint: Path,
    next_resume: str | None,
) -> None:
    """Record review/next state for a finished task.

    Writes the supplied evidence and risks into the run checkpoint under
    ``## Verification`` and ``## Stop Reason`` and updates the
    ``## Next Resume Source`` heading. The original file (if any) is
    preserved otherwise.
    """
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    target = (
        (project_root / checkpoint).resolve()
        if not checkpoint.is_absolute()
        else checkpoint
    )

    from ..file_ops._util import assert_inside

    try:
        assert_inside(project_root, target)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    cp = Checkpoint.load(target)
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    cp.last_worker = cp.last_worker or f"review close {timestamp}"
    cp.durable_state_updated = cp.durable_state_updated or f"task {task_id} closed"

    evidence_lines = "\n".join(f"- {line}" for line in evidence) if evidence else ""
    risk_lines = "\n".join(f"- {line}" for line in risks) if risks else ""

    new_verification_parts: list[str] = []
    if cp.verification:
        new_verification_parts.append(cp.verification.rstrip())
    if evidence_lines:
        new_verification_parts.append(f"### Evidence for {task_id}\n{evidence_lines}")
    if risk_lines:
        new_verification_parts.append(f"### Risks for {task_id}\n{risk_lines}")
    cp.verification = "\n\n".join(new_verification_parts).strip()

    stop_lines = []
    if cp.stop_reason:
        stop_lines.append(cp.stop_reason.rstrip())
    stop_lines.append(f"- task {task_id} closed at {timestamp}")
    if risks:
        stop_lines.append(f"- risks: {'; '.join(risks)}")
    cp.stop_reason = "\n".join(stop_lines).strip()

    if next_resume:
        cp.next_resume_source = next_resume

    cp.dump(target)
    click.echo(bilingual("review.recorded", task_id=task_id, path=str(target)))


__all__ = ["review_group", "review_close_cmd"]
