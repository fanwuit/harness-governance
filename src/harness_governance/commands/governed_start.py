"""``harness governed-start`` command.

Entry router that classifies the incoming request and produces the
canonical disclosure block for the governed path.
"""

from __future__ import annotations

from pathlib import Path

import click

from ..models.schemas import RoutingInput, RoutingResult
from ..state_machine.classification import classify, RoutingPath
from ..state_machine.layers import HarnessLayer


def _build_recommendation(path: RoutingPath) -> str:
    if path is RoutingPath.FAST_PATH:
        return "Answer the question directly; no harness command needed."
    if path is RoutingPath.TRIVIAL_SAFE_CHANGE:
        return (
            "Write a short Trivial Safe Change Entry, run the verification "
            "command, then `harness review close <task-id>`."
        )
    return (
        "Load `skill-use-transparency` and `harness-engineering`, then "
        "`harness packet init <change-id>` when the work spans more than "
        "one layer."
    )


def _evaluate(input_model: RoutingInput) -> RoutingResult:
    decision = classify(
        input_model.description,
        has_file_changes=input_model.has_file_changes,
        is_public_contract=input_model.is_public_contract,
        has_external_side_effect=input_model.has_external_side_effect,
        is_unclear_or_high_risk=input_model.is_unclear_or_high_risk,
    )
    disclosure = decision.to_disclosure(input_model.companion_skills)
    recommendation = _build_recommendation(decision.path)
    return RoutingResult(
        path=decision.path,
        rationale=decision.rationale,
        current_layer=decision.current_layer,
        primary_skill=decision.primary_skill,
        disclosure=disclosure,
        recommended_next_command=recommendation,
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
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    click.echo(f"Routing: {result.path.value}")
    click.echo(f"Rationale: {result.rationale}")
    if result.current_layer:
        click.echo(f"Current layer: {result.current_layer.value}")
    if result.primary_skill:
        click.echo(f"Primary skill: {result.primary_skill}")
    click.echo("")
    click.echo("Disclosure:")
    click.echo(result.disclosure)
    click.echo("")
    click.echo(f"Next: {result.recommended_next_command}")


__all__ = ["governed_start_cmd", "_evaluate"]