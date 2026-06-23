"""``harness spec {quick,upgrade,list}`` commands.

The ``spec quick`` subcommand creates a single-file lightweight spec
(``.harness/specs/<slug>.md``) as an alternative to the full 5-file
change packet.

The ``spec upgrade`` subcommand promotes a spec quick into a full change
packet.

The ``spec list`` subcommand enumerates existing specs.
"""

from __future__ import annotations

from pathlib import Path

import click

from ..file_ops import spec as spec_ops
from ..messages import bilingual


@click.group("spec")
def spec_group() -> None:
    """Manage lightweight specs under ``.harness/specs/``."""


@spec_group.command("quick")
@click.argument("description")
@click.option(
    "--slug",
    default=None,
    help="Spec slug (auto-generated from description when omitted).",
)
@click.pass_context
def spec_quick_cmd(ctx: click.Context, description: str, slug: str | None) -> None:
    """Create a lightweight single-file spec from DESCRIPTION."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())

    try:
        target = spec_ops.init_spec(project_root, description, slug=slug)
    except FileExistsError as exc:
        raise click.ClickException(str(exc)) from exc

    if ctx.obj.get("json_output"):
        import json

        click.echo(
            json.dumps(
                {
                    "path": target.as_posix(),
                    "slug": target.stem,
                },
                indent=2,
            )
        )
        return

    click.echo(bilingual("spec.created", path=target.as_posix()))


@spec_group.command("list")
@click.pass_context
def spec_list_cmd(ctx: click.Context) -> None:
    """List all spec files under ``.harness/specs/``."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    specs = spec_ops.list_specs(project_root)

    if ctx.obj.get("json_output"):
        import json

        click.echo(
            json.dumps(
                {
                    "specs": [
                        {
                            "path": p.as_posix(),
                            "slug": p.stem,
                        }
                        for p in specs
                    ],
                    "count": len(specs),
                },
                indent=2,
            )
        )
        return

    if not specs:
        click.echo(bilingual("spec.list_empty"))
        return

    click.echo(bilingual("spec.list_header", count=len(specs)))
    for p in specs:
        click.echo(f"  - {p}")


@spec_group.command("upgrade")
@click.argument("spec_path", type=click.Path(dir_okay=False, path_type=Path))
@click.option(
    "--change-id",
    default=None,
    help="Change packet id (defaults to the spec file stem).",
)
@click.pass_context
def spec_upgrade_cmd(
    ctx: click.Context,
    spec_path: Path,
    change_id: str | None,
) -> None:
    """Promote a lightweight spec into ``docs/changes/<change-id>/``."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())

    try:
        target = spec_ops.upgrade_spec(project_root, spec_path, change_id=change_id)
    except FileNotFoundError as exc:
        raise click.ClickException(f"Spec not found: {spec_path}") from exc
    except FileExistsError as exc:
        raise click.ClickException(str(exc)) from exc
    except ValueError as exc:
        raise click.BadParameter(str(exc), param_hint="change_id") from exc

    rel = target.resolve().relative_to(project_root.resolve())
    rel_path = rel.as_posix()
    if ctx.obj.get("json_output"):
        import json

        click.echo(
            json.dumps(
                {
                    "change_id": target.name,
                    "packet_dir": target.as_posix(),
                    "path": rel_path,
                },
                indent=2,
            )
        )
        return

    click.echo(f"Spec upgraded to change packet: {rel_path}")


__all__ = [
    "spec_group",
    "spec_quick_cmd",
    "spec_list_cmd",
    "spec_upgrade_cmd",
]
