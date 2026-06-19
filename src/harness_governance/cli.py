"""harness CLI entry point.

Wires the :mod:`click` groups together.  v0.8.0 ships 19 command groups:

* ``harness init``
* ``harness start`` — alias for governed-start
* ``harness governed-start``
* ``harness next`` — current session next-step guidance
* ``harness ship`` — readiness check, no publication
* ``harness packet {init,check}``
* ``harness entry {check,record}``
* ``harness plan {init,attest,show,clear,complete}``
* ``harness check {routing,packets,entry,inventory,all}``
* ``harness status``
* ``harness verify <preset>``
* ``harness review close``
* ``harness config init``
* ``harness runner start``
* ``harness gate {check,status,reset,timing}``
* ``harness layer {advance,show,guide,ask,wizard}``
* ``harness session {show,list,archive}``
* ``harness tech-stack {capture,check,add,show,lint,docstyle}``
* ``harness isolation`` — role isolation workspace inspection
* ``harness drift`` — scope drift boundary inspection
* ``harness alignment`` — contract/implementation field alignment
* ``harness skill-chain`` — subagent invocation lineage tracing
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from . import __version__
from .commands.alignment import alignment_group
from .commands.aliases import next_cmd, ship_cmd, start_cmd
from .commands.check import check_group
from .commands.config_cmd import config_group
from .commands.drift import drift_group
from .commands.entry import entry_group
from .commands.gate import gate_group
from .commands.governed_start import governed_start_cmd
from .commands.hook import hook_group
from .commands.init import init_cmd
from .commands.isolation import isolation_group
from .commands.layer import layer_group
from .commands.packet import packet_group
from .commands.plan import plan_group
from .commands.review import review_group
from .commands.runner import runner_group
from .commands.session_cmd import session_group
from .commands.skill_chain import skill_chain_group
from .commands.state_contract import state_contract_group
from .commands.status import status_cmd
from .commands.tech_stack import tech_stack_group
from .commands.verify import verify_cmd
from .logging_setup import setup_logging


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "--project-root",
    "project_root",
    default=None,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Project root (defaults to current directory).",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    default=False,
    help="Emit machine-readable JSON output.",
)
@click.option(
    "--verbose",
    "-v",
    "verbose",
    is_flag=True,
    default=False,
    help="Show informational messages (INFO level).",
)
@click.option(
    "--debug",
    "-d",
    "debug",
    is_flag=True,
    default=False,
    help="Show detailed diagnostic output (DEBUG level).",
)
@click.version_option(__version__, prog_name="harness")
@click.pass_context
def cli(
    ctx: click.Context,
    project_root: Path | None,
    json_output: bool,
    verbose: bool,
    debug: bool,
) -> None:
    """harness governance CLI — AI engineering workflow enforcement."""
    if verbose and debug:
        raise click.UsageError("--verbose and --debug are mutually exclusive.")
    ctx.ensure_object(dict)
    ctx.obj["project_root"] = (project_root or Path.cwd()).resolve()
    ctx.obj["json_output"] = json_output
    ctx.obj["verbose"] = verbose
    ctx.obj["debug"] = debug
    setup_logging(verbose=verbose, debug=debug)


cli.add_command(init_cmd)
cli.add_command(start_cmd)
cli.add_command(governed_start_cmd)
cli.add_command(hook_group)
cli.add_command(next_cmd)
cli.add_command(ship_cmd)
cli.add_command(packet_group)
cli.add_command(entry_group)
cli.add_command(plan_group)
cli.add_command(check_group)
cli.add_command(status_cmd)
cli.add_command(verify_cmd)
cli.add_command(review_group)
cli.add_command(config_group)
cli.add_command(runner_group)
cli.add_command(layer_group)
cli.add_command(gate_group)
cli.add_command(session_group)
cli.add_command(state_contract_group)
cli.add_command(tech_stack_group)
cli.add_command(isolation_group)
cli.add_command(drift_group)
cli.add_command(alignment_group)
cli.add_command(skill_chain_group)


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
