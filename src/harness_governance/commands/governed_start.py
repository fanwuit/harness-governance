"""``harness governed-start`` command.

Entry router that classifies the incoming request and produces the
canonical disclosure block for the governed path.
"""

from __future__ import annotations

from pathlib import Path

import click

from ..messages import bilingual
from ..models.schemas import RoutingInput, RoutingResult
from ..session import SessionState, create_session, generate_session_id
from ..state_machine.classification import classify, RoutingPath
from ..state_machine.layers import HarnessLayer


def _build_recommendation(path: RoutingPath) -> str:
    if path is RoutingPath.FAST_PATH:
        return "governed_start.recommendation.fast"
    if path is RoutingPath.TRIVIAL_SAFE_CHANGE:
        return "governed_start.recommendation.trivial"
    return "governed_start.recommendation.governed"


def _evaluate(input_model: RoutingInput) -> RoutingResult:
    decision = classify(
        input_model.description,
        has_file_changes=input_model.has_file_changes,
        is_public_contract=input_model.is_public_contract,
        has_external_side_effect=input_model.has_external_side_effect,
        is_unclear_or_high_risk=input_model.is_unclear_or_high_risk,
    )
    disclosure = decision.to_disclosure(input_model.companion_skills)
    rec_key = _build_recommendation(decision.path)
    return RoutingResult(
        path=decision.path,
        rationale=decision.rationale,
        current_layer=decision.current_layer,
        primary_skill=decision.primary_skill,
        disclosure=disclosure,
        recommended_next_command=bilingual(rec_key),
    )


@click.command("governed-start")
@click.argument("description")
@click.option(
    "--files",
    "files",
    default="",
    help="Comma-separated list of files that will be touched.",
)
@click.option(
    "--contracts/--no-contracts",
    default=False,
    help="Whether the work touches a public contract surface.",
)
@click.option(
    "--external/--no-external",
    default=False,
    help="Whether the work has external side effects or persisted data.",
)
@click.option(
    "--unclear/--no-unclear",
    default=False,
    help="Whether scope, risk, or requirements are unclear.",
)
@click.option(
    "--companion",
    "companions",
    multiple=True,
    help="Companion workflow skills (may be passed multiple times).",
)
@click.pass_context
def governed_start_cmd(
    ctx: click.Context,
    description: str,
    files: str,
    contracts: bool,
    external: bool,
    unclear: bool,
    companions: tuple[str, ...],
) -> None:
    """Classify an incoming task and produce the canonical disclosure."""
    has_file_changes = bool(files.strip()) or contracts or external
    payload = RoutingInput(
        description=description,
        has_file_changes=has_file_changes,
        is_public_contract=contracts,
        has_external_side_effect=external,
        is_unclear_or_high_risk=unclear,
        companion_skills=tuple(companions),
    )
    result = _evaluate(payload)

    # Create a governance session for governed-path tasks.
    session_id: str | None = None
    if result.path is RoutingPath.GOVERNED_PATH:
        project_root: Path = ctx.obj["project_root"]
        from datetime import datetime, timezone

        session_id = generate_session_id(description)
        session = SessionState(
            session_id=session_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            description=description,
            routing_path=result.path,
            current_layer=result.current_layer,
            companion_skills=payload.companion_skills,
        )
        session_path = create_session(project_root, session)
        import logging

        logging.getLogger("harness").info("session created: %s", session_path)

    if ctx.obj.get("json_output"):
        import json

        click.echo(
            json.dumps(
                {
                    "path": result.path.value,
                    "rationale": result.rationale,
                    "current_layer": result.current_layer.value if result.current_layer else None,
                    "primary_skill": result.primary_skill,
                    "disclosure": result.disclosure,
                    "recommended_next_command": result.recommended_next_command,
                    "session_id": session_id,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    is_verbose = ctx.obj.get("verbose", False)
    is_fast = result.path is RoutingPath.FAST_PATH
    is_trivial = result.path is RoutingPath.TRIVIAL_SAFE_CHANGE

    # Fast-path: one-liner unless --verbose
    if is_fast and not is_verbose:
        click.echo(bilingual("governed_start.fast_ok"))
        click.echo(result.recommended_next_command)
        return

    # Trivial: compact output, no disclosure block, queue optional
    if is_trivial and not is_verbose:
        click.echo(bilingual("governed_start.routing", path=result.path.value))
        click.echo(bilingual("governed_start.rationale", text=result.rationale))
        click.echo(result.recommended_next_command)
        return

    # Governed path (or any path with --verbose): full disclosure
    click.echo(bilingual("governed_start.routing", path=result.path.value))
    click.echo(bilingual("governed_start.rationale", text=result.rationale))
    if result.current_layer:
        click.echo(bilingual("governed_start.current_layer", layer=result.current_layer.value))
    if result.primary_skill:
        click.echo(bilingual("governed_start.primary_skill", skill=result.primary_skill))
    click.echo("")
    click.echo(bilingual("governed_start.disclosure"))
    click.echo(result.disclosure)
    click.echo("")
    click.echo(bilingual("governed_start.next", cmd=result.recommended_next_command))
    if session_id:
        click.echo(bilingual("session.created", session_id=session_id))


__all__ = ["governed_start_cmd", "_evaluate"]