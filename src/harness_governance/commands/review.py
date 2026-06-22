"""``harness review {close,auto-close}`` commands."""

from __future__ import annotations

import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import click

from ..config import load_config
from ..file_ops.checkpoint import Checkpoint
from ..file_ops.queue import (
    append_structured_queue_item,
    mark_queue_item_done,
    read_queue,
)
from ..messages import bilingual
from ..models.schemas import HarnessConfig
from ..session import load_session, save_session
from ..state_machine.layers import HarnessLayer


@click.group("review")
def review_group() -> None:
    """Close out tasks; persist review/next state."""


def close_task(
    project_root: Path,
    task_id: str,
    *,
    evidence: tuple[str, ...] = (),
    risks: tuple[str, ...] = (),
    checkpoint: Path = Path(".harness/run-checkpoint.md"),
    next_resume: str | None = None,
) -> Path:
    """Close *task_id* across checkpoint, queue, and matching session state."""
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

    config = load_config(project_root)
    items = read_queue(config.queue_file)
    matched_item = next(
        (
            item
            for item in items
            if task_id in {item.id, item.session_id, item.change_id}
            or re.search(
                rf"^\s*\[(?:active|ready)\]\s+.*{re.escape(task_id)}",
                item.raw,
                re.IGNORECASE,
            )
        ),
        None,
    )
    for item in items:
        if item.role != "reviewer-verifier":
            continue
        if task_id in {item.id, item.change_id} and item.session_id != task_id:
            raise click.ClickException(
                "reviewer-verifier queue items must be finished by their "
                "own sessionId; an implementer must not close review work."
            )
    cp.dump(target)
    mark_queue_item_done(
        config.queue_file,
        task_id=task_id,
        evidence=evidence,
        risks=risks,
        session_id=task_id,
        completed_at=timestamp,
    )
    _close_matching_session(project_root, task_id, timestamp)
    if matched_item and matched_item.role == "implementer":
        has_review_queue = any(
            item.role == "reviewer-verifier"
            and matched_item.id
            and matched_item.id in item.depends_on
            for item in items
        )
        if not has_review_queue:
            review_id = _review_queue_id(matched_item.id or task_id)
            append_structured_queue_item(
                config.queue_file,
                item_id=review_id,
                description=f"Review implementation {matched_item.id or task_id}",
                status="ready",
                layer=HarnessLayer.VERIFICATION.value,
                role="reviewer-verifier",
                change_id=matched_item.change_id,
                gate_id="verification" if matched_item.gate_id else None,
                change_kind=matched_item.change_kind,
                depends_on=(matched_item.id or task_id,),
                owner_files=matched_item.owner_files,
                role_plan=matched_item.role_plan
                or (
                    "planner",
                    "contract-test-writer",
                    "implementer",
                    "reviewer-verifier",
                ),
                session_id=_review_session_id(matched_item.session_id or task_id),
                verification="harness check all --no-auto-close",
                stop_conditions=(
                    "Stop if implementation evidence is missing or the "
                    "review session matches the implementation session."
                ),
                handoff_from=matched_item.session_id or task_id,
            )
            click.echo(
                f"Generated reviewer-verifier queue item: {review_id}"
            )
    return target


def _review_queue_id(implementation_id: str) -> str:
    return f"review-{implementation_id}"


def _review_session_id(implementation_session_id: str) -> str:
    return f"review-{implementation_session_id}"


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
    target = close_task(
        project_root,
        task_id,
        evidence=evidence,
        risks=risks,
        checkpoint=checkpoint,
        next_resume=next_resume,
    )
    click.echo(bilingual("review.recorded", task_id=task_id, path=str(target)))


def _close_matching_session(project_root: Path, task_id: str, timestamp: str) -> bool:
    """Close the session whose id exactly matches *task_id*, if it exists."""
    try:
        state = load_session(project_root, task_id)
    except FileNotFoundError:
        return False

    if state.status == "closed":
        return False

    save_session(
        project_root,
        state.model_copy(
            update={
                "status": "closed",
                "closed_at": timestamp,
            }
        ),
    )
    return True


def _is_working_tree_clean(project_root: Path) -> bool:
    """Return True when ``git status --porcelain`` is empty."""
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
            cwd=project_root,
        )
        return result.returncode == 0 and not result.stdout.strip()
    except FileNotFoundError:
        return True
    except OSError:
        return True


def _extract_session_id(raw: str) -> str | None:
    """Extract ``Session: <id>`` from a queue block's raw text."""
    for line in raw.splitlines():
        m = re.match(r"^\s*-?\s*Session:\s*(.+)$", line, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    return None


def auto_close_active_tasks(
    project_root: Path,
    *,
    dry_run: bool = False,
    config: HarnessConfig | None = None,
) -> tuple[int, int]:
    """Scan [active] queue items and auto-close those that are done.

    A task is considered done when its session is already closed or when
    its session has reached the REVIEW_NEXT layer and the working tree
    is clean.

    Returns (active_count, closed_count).
    """
    cfg = config or load_config(project_root)
    items = read_queue(cfg.queue_file)
    active_items = [item for item in items if item.active]

    closed = 0
    for item in active_items:
        session_id = _extract_session_id(item.raw)
        if not session_id:
            continue

        try:
            session = load_session(project_root, session_id)
        except FileNotFoundError:
            continue

        should_close = False

        if session.status == "closed":
            should_close = True
        elif (
            session.current_layer == HarnessLayer.REVIEW_NEXT
            and _is_working_tree_clean(project_root)
        ):
            should_close = True

        if not should_close:
            continue

        closed += 1
        if not dry_run:
            if session.status != "closed":
                ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
                save_session(
                    project_root,
                    session.model_copy(
                        update={"status": "closed", "closed_at": ts}
                    ),
                )
            mark_queue_item_done(
                cfg.queue_file,
                task_id=session_id,
                evidence=("auto-closed by harness review auto-close",),
            )

    return len(active_items), closed


@review_group.command("auto-close")
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Show what would be closed without making changes.",
)
@click.pass_context
def review_auto_close_cmd(ctx: click.Context, dry_run: bool) -> None:
    """Auto-close [active] tasks whose sessions indicate completion.

    A task qualifies when:

    \b
    * its session is already closed, or
    * its session has reached the REVIEW_NEXT layer and the working
      tree is clean.

    Typically run automatically after ``harness check all``.
    """
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    active, closed = auto_close_active_tasks(project_root, dry_run=dry_run)

    if active == 0:
        click.echo(bilingual("review.auto_close.no_active"))
        return

    if closed == 0:
        click.echo(bilingual("review.auto_close.none"))
        return

    click.echo(
        bilingual("review.auto_close.summary", active=active, closed=closed)
    )


__all__ = [
    "review_group",
    "review_close_cmd",
    "review_auto_close_cmd",
    "auto_close_active_tasks",
    "close_task",
]
