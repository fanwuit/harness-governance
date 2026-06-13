"""harness CLI entry point.

Wires the :mod:`click` groups together. Phase A ships three subcommands:

* ``harness init``
* ``harness governed-start``
* ``harness packet {init,check}``

Phase B will add ``entry``, ``plan``, ``check``, ``status``, ``verify``,
``review``, ``config``, and ``runner`` groups.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from . import __version__
from .commands.governed_start import governed_start_cmd
from .commands.init import init_cmd
from .commands.packet import packet_group


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--project-root",
    "project_root",
    default=None,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Project root (defaults to current directory).",
)
@click.option("--json", "json_output", is_flag=True, default=False, help="Emit machine-readable JSON output.")
@click.version_option(__version__, prog_name="harness")
@click.pass_context
def cli(ctx: click.Context, project_root: Path | None, json_output: bool) -> None:
    """harness governance CLI — AI engineering workflow enforcement."""
    ctx.ensure_object(dict)
    ctx.obj["project_root"] = (project_root or Path.cwd()).resolve()
    ctx.obj["json_output"] = json_output


cli.add_command(init_cmd)
cli.add_command(governed_start_cmd)
cli.add_command(packet_group)


def main(argv: list[str] | None = None) -> int:
    """Console-script entry point."""
    try:
        result = cli.main(args=argv, standalone_mode=False)
    except click.exceptions.Exit as exc:
        return int(exc.exit_code)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 1
    # ``click.main(standalone_mode=False)`` swallows Exit and returns the
    # exit code, so honor that here.
    return int(result) if result else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())