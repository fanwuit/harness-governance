"""``harness packet {init,check}`` commands."""

from __future__ import annotations

from pathlib import Path

import click

from ..file_ops import packet as packet_ops
from ..models.schemas import ChangePacketInitResult, CheckResult


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
    click.echo(f"Initialized change packet: {rel}")
    if result.created_files:
        click.echo(f"Created files: {', '.join(result.created_files)}")
    else:
        click.echo("No new files were written (packet already populated).")


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
        click.echo("Change packet check passed: no change packets found.")
        return

    if passed:
        click.echo(f"Change packet check passed: {inspected} packet(s).")
        return

    click.echo("Change packet check failed:")
    for error in all_errors:
        click.echo(f"- {error}")
    raise click.exceptions.Exit(code=1)


__all__ = [
    "packet_group",
    "packet_init_cmd",
    "packet_check_cmd",
    "ChangePacketInitResult",
]