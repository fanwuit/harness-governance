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
from ..state_machine.rigor import resolve_rigor
from ..config.defaults import PLATFORM_SKILL_PATHS


def _build_recommendation(path: RoutingPath) -> str:
    if path is RoutingPath.FAST_PATH:
        return "governed_start.recommendation.fast"
    if path is RoutingPath.TRIVIAL_SAFE_CHANGE:
        return "governed_start.recommendation.trivial"
    return "governed_start.recommendation.governed"


def _check_skill_freshness(project_root: Path) -> str | None:
    """Return a one-line warning if the on-disk skill is older than the
    installed template, else None.

    Scans every supported platform's skill path so a multi-platform
    project (claude-code + codex + …) still gets caught when at least
    one adapter is stale. Reads only the first ~1 KB of each file to
    keep the check fast on large monorepos.

    Files that do not start with YAML frontmatter (``---``) are
    skipped: AGENTS.md, README.md, and similar project docs are
    *user-maintained* and not skill templates, so comparing them to a
    skill template would produce false positives.
    """
    from .init import extract_skill_version, load_skill_template

    warnings: list[str] = []
    for plat, rel in PLATFORM_SKILL_PATHS.items():
        target = (project_root / rel).resolve()
        if not target.is_file():
            continue
        try:
            with target.open("rb") as f:
                raw = f.read(2048)
            text = raw.decode("utf-8", errors="replace")
            # Strip BOM defensively before searching.
            if text.startswith("﻿"):
                text = text[1:]
            # Skip non-skill files: AGENTS.md, README.md, etc. are
            # user-maintained project docs, not skill templates.
            if not text.lstrip().startswith("---"):
                continue
            disk_ver = extract_skill_version(text)
        except OSError:
            continue
        template = load_skill_template(plat)
        template_ver = extract_skill_version(template)
        if template_ver and disk_ver != template_ver:
            warnings.append(f"{plat}: v{disk_ver or 'unknown'} → v{template_ver}")
    if not warnings:
        return None
    joined = "; ".join(warnings)
    return (
        f"⚠ harness skill in this project is older than the installed "
        f"template ({joined}). Run `harness init --force` to upgrade."
    )


def _evaluate(input_model: RoutingInput, project_root: Path) -> RoutingResult:
    decision = classify(
        input_model.description,
        has_file_changes=input_model.has_file_changes,
        is_public_contract=input_model.is_public_contract,
        has_external_side_effect=input_model.has_external_side_effect,
        is_unclear_or_high_risk=input_model.is_unclear_or_high_risk,
        rigor=input_model.rigor_tier,
    )
    disclosure = decision.to_disclosure(input_model.companion_skills)
    rec_key = _build_recommendation(decision.path)
    skill_warning = _check_skill_freshness(project_root)
    return RoutingResult(
        path=decision.path,
        rationale=decision.rationale,
        current_layer=decision.current_layer,
        primary_skill=decision.primary_skill,
        disclosure=disclosure,
        recommended_next_command=bilingual(rec_key),
        skill_version_warning=skill_warning,
        rigor_tier=decision.rigor_tier.value,
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
    "--rigor",
    "rigor_override",
    type=click.Choice(["light", "standard", "strict"]),
    default=None,
    help="Governance rigor tier (auto-detected from description when omitted).",
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
    rigor_override: str | None,
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
        rigor_tier=rigor_override,
    )
    project_root: Path = ctx.obj["project_root"]
    result = _evaluate(payload, project_root)

    # Resolve rigor tier for session storage.
    resolved_rigor = resolve_rigor(rigor_override, description)

    # Create a governance session for governed-path tasks.
    session_id: str | None = None
    if result.path is RoutingPath.GOVERNED_PATH:
        from datetime import datetime, timezone

        session_id = generate_session_id(description)
        session = SessionState(
            session_id=session_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            description=description,
            routing_path=result.path,
            current_layer=result.current_layer,
            companion_skills=payload.companion_skills,
            rigor_tier=resolved_rigor.value,
        )
        session_path = create_session(project_root, session)
        import logging

        logging.getLogger("harness").info("session created: %s", session_path)

    # Layer 4: runtime competing-skill warning (soft check, never blocks)
    try:
        from ..priority import detect_competing_skills

        competing = detect_competing_skills(project_root)
        if competing:
            names = ", ".join(c.skill_name for c in competing[:5])
            if len(competing) > 5:
                names += f" (+{len(competing) - 5} more)"
            click.echo(
                bilingual("priority.runtime_warning", count=len(competing), names=names),
                err=True,
            )
    except Exception:
        pass  # priority scan must never block governed-start

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
                    "skill_version_warning": result.skill_version_warning,
                    "rigor_tier": result.rigor_tier,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    is_verbose = ctx.obj.get("verbose", False)
    is_fast = result.path is RoutingPath.FAST_PATH
    is_trivial = result.path is RoutingPath.TRIVIAL_SAFE_CHANGE

    # Skill-version staleness warning (printed once, regardless of path)
    if result.skill_version_warning:
        click.echo(result.skill_version_warning, err=True)

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
    if result.rigor_tier:
        click.echo(bilingual("governed_start.rigor_tier", tier=result.rigor_tier))
    click.echo("")
    click.echo(bilingual("governed_start.disclosure"))
    click.echo(result.disclosure)
    click.echo("")
    click.echo(bilingual("governed_start.next", cmd=result.recommended_next_command))
    if session_id:
        click.echo(bilingual("session.created", session_id=session_id))


__all__ = ["governed_start_cmd", "_evaluate"]