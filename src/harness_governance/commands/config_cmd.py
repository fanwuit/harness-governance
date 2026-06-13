"""``harness config init`` command.

Writes ``.harness/config.toml`` for the current project. Useful when
``harness init`` is skipped or when only the config (no skill adapter)
is needed.
"""

from __future__ import annotations

from pathlib import Path

import click

from ..config.defaults import PLATFORM_SKILL_PATHS
from ..config.settings import write_default_config
from .init import detect_platform


@click.group("config")
def config_group() -> None:
    """Manage ``.harness/config.toml``."""


@config_group.command("init")
@click.option(
    "--platform",
    "platform",
    default=None,
    type=click.Choice(sorted(PLATFORM_SKILL_PATHS)),
    help="Override automatic platform detection.",
)
@click.option("--force/--no-force", default=False, help="Overwrite existing config.")
@click.pass_context
def config_init_cmd(ctx: click.Context, platform: str | None, force: bool) -> None:
    """Initialize ``.harness/config.toml``."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    detected = platform or detect_platform(project_root)
    path = write_default_config(project_root, agent_platform=detected, force=force)
    click.echo(f"Created: {path}")
    click.echo(f"Agent platform: {detected}")


__all__ = ["config_group", "config_init_cmd"]