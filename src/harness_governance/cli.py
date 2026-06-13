"""harness CLI entry point.

Wires the :mod:`click` groups together. Phase B ships:

* ``harness init``
* ``harness governed-start``
* ``harness packet {init,check}``
* ``harness entry {check,record}``
* ``harness plan {init,attest,show,clear,complete}``
* ``harness check {routing,packets,entry,inventory,all}``
* ``harness status``
* ``harness verify <preset>``
* ``harness review close``
* ``harness config init``
* ``harness runner start``
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from . import __version__
from .commands.check import check_group
from .commands.config_cmd import config_group
from .commands.entry import entry_group
from .commands.governed_start import governed_start_cmd
from .commands.init import init_cmd
from .commands.packet import packet_group
from .commands.plan import plan_group
from .commands.review import review_group
from .commands.runner import runner_group
from .commands.status import status_cmd
from .commands.verify import verify_cmd


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
cli.add_command(entry_group)
cli.add_command(plan_group)
cli.add_command(check_group)
cli.add_command(status_cmd)
cli.add_command(verify_cmd)
cli.add_command(review_group)
cli.add_command(config_group)
cli.add_command(runner_group)


def main(argv: list[str] | None = None) -> int:
    """Console-script entry point."""
    try:
        result = cli.main(args=argv, standalone_mode=False)
    except click.exceptions.Exit as exc:
        return int(exc.exit_code)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 1
    return int(result) if result else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())