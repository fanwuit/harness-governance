"""Ergonomic top-level aliases for common harness workflows."""

from __future__ import annotations

import json
from pathlib import Path

import click

from ..messages import bilingual
from ..session import find_active_session
from ..state_machine.gates import LayerGateEngine, LockFileManager, layers_for_tier
from ..state_machine.rigor import RigorTier
from .check import (
    check_docs,
    check_entry,
    check_inventory,
    check_packets,
    check_priority,
    check_routing,
    check_subagent_separation,
    check_user_evidence,
)
from .governed_start import governed_start_cmd
from .verify import is_harness_governance_repo


@click.command("start")
@click.argument("description")
@click.option(
    "--files",
    "files",
    default="",
    help="Comma-separated list of files that will be touched.",
)
@click.option(
    "--contracts/--no-contracts",
    default=None,
    help="Whether the work touches a public contract surface.",
)
@click.option(
    "--external/--no-external",
    default=None,
    help="Whether the work has external side effects or persisted data.",
)
@click.option(
    "--unclear/--no-unclear",
    default=False,
    help="Whether scope, risk, or requirements are unclear.",
)
@click.option(
    "--rigor",
    "rigor_override",
    type=click.Choice(["light", "standard", "strict"]),
    default=None,
    help="Governance rigor tier.",
)
@click.option(
    "--companion",
    "companions",
    multiple=True,
    help="Companion workflow skills (may be passed multiple times).",
)
@click.pass_context
def start_cmd(
    ctx: click.Context,
    description: str,
    files: str,
    contracts: bool | None,
    external: bool | None,
    unclear: bool,
    rigor_override: str | None,
    companions: tuple[str, ...],
) -> None:
    """Alias for ``harness governed-start``."""
    ctx.invoke(
        governed_start_cmd,
        description=description,
        files=files,
        contracts=contracts,
        external=external,
        unclear=unclear,
        rigor_override=rigor_override,
        companions=companions,
    )


@click.command("next")
@click.pass_context
def next_cmd(ctx: click.Context) -> None:
    """Show the current session layer and the recommended next command."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    session = find_active_session(project_root)
    if session is None or session.current_layer is None:
        raise click.ClickException(bilingual("session.no_active"))

    tier = RigorTier(session.rigor_tier)
    path = layers_for_tier(tier)
    current = session.current_layer
    try:
        current_index = path.index(current)
    except ValueError:
        current_index = -1
    next_layer = path[current_index + 1] if 0 <= current_index + 1 < len(path) else None

    status = LayerGateEngine().check(session, project_root, current)
    if status.passed and next_layer:
        recommendation = f"harness layer advance {next_layer.value} --confirmed"
    elif status.passed:
        recommendation = "harness review close"
    else:
        recommendation = f"harness layer guide {current.value}"

    payload = {
        "session_id": session.session_id,
        "rigor_tier": session.rigor_tier,
        "current_layer": current.value,
        "next_layer": next_layer.value if next_layer else None,
        "gate_passed": status.passed,
        "questions_answered": status.questions_answered,
        "questions_required": status.questions_required,
        "artifacts_missing": list(status.artifacts_missing),
        "blocking_artifacts_missing": list(status.blocking_artifacts_missing),
        "confirmation_items_unmet": list(status.confirmation_items_unmet),
        "recommended_next_command": recommendation,
    }

    if ctx.obj.get("json_output"):
        click.echo(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    click.echo(bilingual("alias.next.header", session=session.session_id))
    click.echo(bilingual("governed_start.rigor_tier", tier=session.rigor_tier))
    click.echo(bilingual("session.current_layer", layer=current.value))
    if next_layer:
        click.echo(bilingual("governed_start.next_layer", layer=next_layer.value))
    gate_state = "PASSED" if status.passed else "FAILED"
    click.echo(
        bilingual(
            "alias.next.gate",
            state=gate_state,
            questions=status.questions_answered,
            required=status.questions_required,
        )
    )
    click.echo(bilingual("governed_start.next", cmd=recommendation))


@click.command("ship")
@click.pass_context
def ship_cmd(ctx: click.Context) -> None:
    """Run release-readiness checks without publishing or deploying."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    release_verification_available = is_harness_governance_repo(project_root)
    results = [
        check_routing(project_root),
        check_priority(project_root),
        check_packets(project_root),
        check_entry(project_root),
        check_inventory(project_root),
        check_user_evidence(project_root),
        check_subagent_separation(project_root),
        check_docs(project_root),
    ]
    checks_passed = all(result.passed for result in results)

    session = find_active_session(project_root)
    gate_rows: list[dict[str, object]] = []
    gates_passed = session is not None
    if session is not None:
        locks = LockFileManager(project_root)
        for layer in layers_for_tier(RigorTier(session.rigor_tier)):
            locked = locks.exists(layer)
            gate_rows.append({"layer": layer.value, "locked": locked})
            gates_passed = gates_passed and locked

    passed = checks_passed and gates_passed
    payload = {
        "passed": passed,
        "checks": [
            {
                "check": result.check,
                "passed": result.passed,
                "findings": [f.model_dump() for f in result.findings],
            }
            for result in results
        ],
        "session_id": session.session_id if session else None,
        "gates": gate_rows,
        "published": False,
        "release_verification_available": release_verification_available,
    }

    if ctx.obj.get("json_output"):
        click.echo(json.dumps(payload, indent=2, ensure_ascii=False))
        if not passed:
            raise click.exceptions.Exit(code=1)
        return

    click.echo(bilingual("alias.ship.header"))
    click.echo(bilingual("alias.ship.no_publish"))
    for result in results:
        state = "PASSED" if result.passed else "FAILED"
        click.echo(f"- {result.check}: {state}")
    if session is None:
        click.echo(bilingual("alias.ship.no_session"))
    else:
        locked_count = sum(1 for row in gate_rows if bool(row["locked"]))
        click.echo(
            bilingual(
                "alias.ship.gates",
                locked=locked_count,
                total=len(gate_rows),
            )
        )
    if release_verification_available:
        click.echo(bilingual("alias.ship.release_verify_hint"))
    if passed:
        if not (project_root / ".git" / "hooks" / "pre-push").is_file():
            click.echo(bilingual("alias.ship.hook_hint"))
    else:
        click.echo(bilingual("alias.ship.fail_hint"))
    if not passed:
        raise click.exceptions.Exit(code=1)


__all__ = ["start_cmd", "next_cmd", "ship_cmd"]
