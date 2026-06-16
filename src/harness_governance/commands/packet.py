"""``harness packet {init,check}`` commands."""

from __future__ import annotations

from pathlib import Path

import click

from ..file_ops import packet as packet_ops
from ..messages import bilingual
from ..models.schemas import ChangePacketInitResult, CheckResult
from ..session import find_active_session, save_session


@click.group("packet")
def packet_group() -> None:
    """Manage change packets under ``docs/changes/<id>/``."""


@packet_group.command("init")
@click.argument("change_id")
@click.option(
    "--repo",
    "repo_root",
    default=None,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Project root (defaults to current directory).",
)
@click.option("--force/--no-force", default=False, help="Fill missing files without overwriting existing ones.")
@click.pass_context
def packet_init_cmd(
    ctx: click.Context,
    change_id: str,
    repo_root: Path | None,
    force: bool,
) -> None:
    """Create a new change packet directory."""
    root = repo_root or ctx.obj.get("project_root", Path.cwd())

    # Session gate: when require_session is enabled, reject if no active session.
    from ..config import load_config

    try:
        cfg = load_config(root)
    except Exception:
        cfg = None
    if cfg and cfg.require_session:
        active = find_active_session(root)
        if active is None:
            raise click.ClickException(bilingual("session.require_session"))
        # Link the change_id to the session.
        if active.change_id != change_id:
            active = active.model_copy(update={"change_id": change_id})
            save_session(root, active)

    try:
        result = packet_ops.init_packet(root, change_id, force=force)
    except FileExistsError as exc:
        raise click.ClickException(str(exc)) from exc
    except ValueError as exc:
        raise click.BadParameter(str(exc), param_hint="change_id") from exc

    if ctx.obj.get("json_output"):
        import json

        click.echo(
            json.dumps(
                {
                    "change_id": result.change_id,
                    "packet_dir": str(result.packet_dir),
                    "created_files": list(result.created_files),
                    "today": result.today.isoformat(),
                },
                indent=2,
            )
        )
        return

    rel = result.packet_dir.resolve().relative_to(root.resolve())
    click.echo(bilingual("packet.initialized", path=str(rel)))
    if result.created_files:
        click.echo(bilingual("packet.created_files", files=", ".join(result.created_files)))
    else:
        click.echo(bilingual("packet.no_new_files"))


@packet_group.command("check")
@click.argument("targets", nargs=-1)
@click.option(
    "--repo",
    "repo_root",
    default=None,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Project root (defaults to current directory).",
)
@click.pass_context
def packet_check_cmd(
    ctx: click.Context,
    targets: tuple[str, ...],
    repo_root: Path | None,
) -> None:
    """Validate change packet structure."""
    root = repo_root or ctx.obj.get("project_root", Path.cwd())

    if targets:
        packet_dirs: list[Path] = []
        for target in targets:
            try:
                packet_dirs.append(packet_ops.resolve_packet_path(root, target))
            except FileNotFoundError as exc:
                raise click.ClickException(str(exc)) from exc
    else:
        packet_dirs = packet_ops.discover_packets(root)

    all_errors: list[str] = []
    inspected = 0
    for packet_dir in packet_dirs:
        errors, _ = packet_ops.check_packet(packet_dir, project_root=root)
        all_errors.extend(errors)
        inspected += 1

    passed = not all_errors
    result = CheckResult(
        check="packet",
        passed=passed,
        findings=tuple(),
        inspected=inspected,
    )

    if ctx.obj.get("json_output"):
        import json

        click.echo(
            json.dumps(
                {
                    "check": result.check,
                    "passed": result.passed,
                    "inspected": result.inspected,
                    "errors": all_errors,
                },
                indent=2,
            )
        )
        if not passed:
            raise click.exceptions.Exit(code=1)
        return

    if not packet_dirs:
        click.echo(bilingual("packet.check_passed_empty"))
        return

    if passed:
        click.echo(bilingual("packet.check_passed_with_count", n=inspected))
        return

    click.echo(bilingual("packet.check_failed_header"))
    for error in all_errors:
        click.echo(f"- {error}")
    raise click.exceptions.Exit(code=1)


__all__ = [
    "packet_group",
    "packet_init_cmd",
    "packet_check_cmd",
    "ChangePacketInitResult",
]