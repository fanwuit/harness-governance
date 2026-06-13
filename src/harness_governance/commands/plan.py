"""``harness plan {init,attest,show,clear,complete}`` commands."""

from __future__ import annotations

from pathlib import Path

import click

from ..file_ops import plan as plan_ops


@click.group("plan")
def plan_group() -> None:
    """Manage planning sessions under ``.planning/<id>/``."""


@plan_group.command("init")
@click.argument("slug", required=False)
@click.option(
    "--template",
    "template",
    default="default",
    show_default=True,
    type=click.Choice(["default", "analytics"]),
    help="Template flavor.",
)
@click.pass_context
def plan_init_cmd(ctx: click.Context, slug: str | None, template: str) -> None:
    """Create a new planning session."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    try:
        session = plan_ops.init_plan(project_root, template=template, slug=slug)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc

    if ctx.obj.get("json_output"):
        import json

        click.echo(
            json.dumps(
                {
                    "plan_id": session.plan_id,
                    "plan_dir": str(session.plan_dir),
                    "task_plan_path": str(session.task_plan_path),
                    "findings_path": str(session.findings_path),
                    "progress_path": str(session.progress_path),
                    "attested": session.attested,
                },
                indent=2,
            )
        )
        return
    click.echo(f"Initialized planning session: {session.plan_id}")
    click.echo(f"Plan dir: {session.plan_dir}")


@plan_group.command("attest")
@click.argument("plan_id", required=False)
@click.pass_context
def plan_attest_cmd(ctx: click.Context, plan_id: str | None) -> None:
    """Lock the current task_plan.md with a SHA-256 attestation."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    try:
        digest = plan_ops.attest_plan(project_root, plan_id)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    short = digest[:12]
    click.echo(f"Locked SHA-256: {short}... (full hash stored in .attestation)")


@plan_group.command("show")
@click.argument("plan_id", required=False)
@click.pass_context
def plan_show_cmd(ctx: click.Context, plan_id: str | None) -> None:
    """Print the stored attestation hash."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    target = (project_root / ".planning" / (plan_id or "")) if plan_id else plan_ops.resolve_active_plan(project_root)
    if target is None:
        raise click.ClickException("No active plan. Run `harness plan init` first.")
    attestation = target.plan_dir / ".attestation"
    if not attestation.is_file():
        raise click.ClickException(f"No attestation set for {target.plan_id}.")
    digest = attestation.read_text(encoding="utf-8").strip()
    click.echo(f"Plan: {target.plan_dir / 'task_plan.md'}")
    click.echo(f"Attestation: {attestation}")
    click.echo(f"SHA-256: {digest}")


@plan_group.command("clear")
@click.argument("plan_id", required=False)
@click.pass_context
def plan_clear_cmd(ctx: click.Context, plan_id: str | None) -> None:
    """Remove an attestation (re-open the plan)."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    target = (project_root / ".planning" / (plan_id or "")) if plan_id else plan_ops.resolve_active_plan(project_root)
    if target is None:
        raise click.ClickException("No active plan. Run `harness plan init` first.")
    attestation = target.plan_dir / ".attestation"
    if not attestation.is_file():
        click.echo(f"[plan-attest] No attestation to clear for {target.plan_id}.")
        return
    attestation.unlink()
    click.echo(f"[plan-attest] Cleared attestation for {target.plan_id}.")


@plan_group.command("complete")
@click.argument("plan_id", required=False)
@click.pass_context
def plan_complete_cmd(ctx: click.Context, plan_id: str | None) -> None:
    """Report whether every Phase in the plan is marked complete."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    try:
        all_done = plan_ops.is_plan_complete(project_root, plan_id)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    if all_done:
        click.echo("[planning-with-files] ALL PHASES COMPLETE.")
        raise click.exceptions.Exit(code=0)
    click.echo("[planning-with-files] Task in progress; not all phases are complete yet.")
    raise click.exceptions.Exit(code=1)


__all__ = [
    "plan_group",
    "plan_init_cmd",
    "plan_attest_cmd",
    "plan_show_cmd",
    "plan_clear_cmd",
    "plan_complete_cmd",
]