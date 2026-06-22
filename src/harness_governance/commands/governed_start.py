"""``harness governed-start`` command.

Entry router that classifies the incoming request and produces the
canonical disclosure block for the governed path.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Literal, cast

import click

from ..messages import bilingual
from ..config import load_config
from ..file_ops.queue import (
    append_governed_queue_item,
    mark_queue_item_status,
    read_queue,
)
from ..queue_validation import validate_queue
from ..hard_gates import is_trivial_queue_item
from ..models.schemas import AgentAssessment, RoutingInput, RoutingResult
from ..session import SessionState, create_session, generate_session_id
from ..state_machine.classification import (
    classify,
    RoutingPath,
    PUBLIC_CONTRACT_KEYWORDS,
)
from ..state_machine.gates import layers_for_tier
from ..state_machine.layers import HarnessLayer
from ..state_machine.rigor import resolve_rigor, STRICT_DETECTION_KEYWORDS
from ..config.defaults import PLATFORM_SKILL_PATHS


# Keywords that imply external side effects (persisted data, network,
# deployments, billing, etc.) — used for auto-inferring --external.
_EXTERNAL_IMPLYING_KEYWORDS: tuple[str, ...] = (
    "database",
    "db",
    "sql",
    "redis",
    "mongo",
    "postgres",
    "mysql",
    "api",
    "endpoint",
    "http",
    "request",
    "response",
    "webhook",
    "deploy",
    "deployment",
    "release",
    "ci/cd",
    "pipeline",
    "payment",
    "billing",
    "charge",
    "invoice",
    "subscription",
    "email",
    "notification",
    "push",
    "sms",
    "auth",
    "login",
    "signup",
    "register",
    "session",
    "token",
    "persist",
    "store",
    "save",
    "write",
    "insert",
    "update",
    "migration",
    "seed",
    "fixture",
    "数据库",
    "接口",
    "部署",
    "发布",
    "支付",
    "账单",
    "邮件",
    "通知",
    "认证",
    "登录",
    "注册",
    "持久化",
    "存储",
    "迁移",
)


def _infer_flags(description: str) -> tuple[bool, bool]:
    """Auto-infer --contracts and --external from the task description.

    Returns (inferred_contracts, inferred_external).

    Rules:
    - If description contains any PUBLIC_CONTRACT_KEYWORDS → contracts=True
    - If description contains any STRICT_DETECTION_KEYWORDS → contracts=True
      (large-scope tasks inherently touch public contracts)
    - If description contains any _EXTERNAL_IMPLYING_KEYWORDS → external=True
    - If description contains any STRICT_DETECTION_KEYWORDS → external=True
      (large-scope tasks inherently have external side effects)
    """
    description_lc = description.lower()

    inferred_contracts = any(
        kw in description_lc for kw in PUBLIC_CONTRACT_KEYWORDS
    ) or any(kw.lower() in description_lc for kw in STRICT_DETECTION_KEYWORDS)
    inferred_external = any(
        kw in description_lc for kw in _EXTERNAL_IMPLYING_KEYWORDS
    ) or any(kw.lower() in description_lc for kw in STRICT_DETECTION_KEYWORDS)

    return inferred_contracts, inferred_external


def _build_recommendation(path: RoutingPath) -> str:
    if path is RoutingPath.FAST_PATH:
        return "governed_start.recommendation.fast"
    if path is RoutingPath.TRIVIAL_SAFE_CHANGE:
        return "governed_start.recommendation.trivial"
    return "governed_start.recommendation.governed"


def _format_layer_path(rigor_tier: str) -> str:
    """Return the layer path for the resolved rigor tier."""
    from ..state_machine.rigor import RigorTier

    tier = RigorTier(rigor_tier)
    return " -> ".join(layer.value for layer in layers_for_tier(tier))


def _next_layer(current: HarnessLayer | None, rigor_tier: str) -> HarnessLayer | None:
    """Return the next layer in the rigor-specific path, if any."""
    if current is None:
        return None
    from ..state_machine.rigor import RigorTier

    path = layers_for_tier(RigorTier(rigor_tier))
    try:
        index = path.index(current)
    except ValueError:
        return None
    if index + 1 >= len(path):
        return None
    return path[index + 1]


def _find_queue_item(items, item_id: str):
    lowered = item_id.strip().lower()
    for item in items:
        if item.id and item.id.lower() == lowered:
            return item
        if item.session_id and item.session_id.lower() == lowered:
            return item
        if item.change_id and item.change_id.lower() == lowered:
            return item
        if lowered in item.raw.lower():
            return item
    return None


def _queue_item_description(item) -> str:
    if not item.raw.strip():
        return ""
    first_line = item.raw.splitlines()[0].strip()
    first_line = re.sub(r"^\s*(?:\d+\.|[-*])\s*", "", first_line)
    return re.sub(
        r"^\[(?:planned|ready|active|blocked|done|not-now|archived)\]\s*",
        "",
        first_line,
        flags=re.IGNORECASE,
    ).strip()


def _validate_queue_context(queue_item, items) -> None:
    if not queue_item.role_plan and not is_trivial_queue_item(queue_item):
        raise click.ClickException(
            "Non-trivial queue item must declare RolePlan, for example: "
            "RolePlan: planner -> contract-test-writer -> implementer -> reviewer-verifier."
        )

    dep_map = {}
    for item in items:
        for key in (item.id, item.session_id, item.change_id):
            if key:
                dep_map.setdefault(key, item)

    if queue_item.layer is not None:
        if queue_item.layer.value == "implementation" and queue_item.role != "implementer":
            raise click.ClickException(
                "Implementation queue item must declare role=implementer."
            )
        if queue_item.layer.value == "verification" and queue_item.role not in {
            "reviewer-verifier",
            "verifier",
        }:
            raise click.ClickException(
                "Verification queue item must declare role=reviewer-verifier or role=verifier."
            )

    resolved_deps = [dep_map.get(dep_id) for dep_id in queue_item.depends_on]
    for dep_id, dep in zip(queue_item.depends_on, resolved_deps, strict=False):
        if dep is None:
            raise click.ClickException(f"Queue dependency not found: {dep_id}")
        if dep.status != "done":
            raise click.ClickException(f"Queue dependency not done: {dep_id}")

    if queue_item.role == "reviewer-verifier":
        impl_deps = [dep for dep in resolved_deps if dep and dep.role == "implementer"]
        if not impl_deps:
            raise click.ClickException(
                "Review queue item must dependsOn an implementation item."
            )
        if queue_item.session_id:
            for dep in impl_deps:
                if dep.session_id and queue_item.session_id == dep.session_id:
                    raise click.ClickException(
                        "reviewer-verifier sessionId must differ from implementation."
                    )


def _validate_resolved_queue_session(queue_item, items, session_id: str) -> None:
    if queue_item.role != "reviewer-verifier":
        return
    dep_map = {}
    for item in items:
        for key in (item.id, item.session_id, item.change_id):
            if key:
                dep_map.setdefault(key, item)
    impl_deps = [
        dep_map.get(dep_id)
        for dep_id in queue_item.depends_on
        if dep_map.get(dep_id) and dep_map.get(dep_id).role == "implementer"
    ]
    for dep in impl_deps:
        if dep.session_id and session_id == dep.session_id:
            raise click.ClickException(
                "reviewer-verifier sessionId must differ from implementation."
            )


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
    assessment = input_model.agent_assessment
    decision = classify(
        input_model.description,
        has_file_changes=input_model.has_file_changes,
        is_public_contract=input_model.is_public_contract,
        has_external_side_effect=input_model.has_external_side_effect,
        is_unclear_or_high_risk=input_model.is_unclear_or_high_risk,
        rigor=input_model.rigor_tier,
        agent_recommended_route=assessment.recommended_route if assessment else None,
        agent_risk=assessment.risk if assessment else None,
        agent_change_kind=assessment.change_kind if assessment else "",
        agent_recommended_rigor=assessment.recommended_rigor if assessment else None,
        agent_operation=assessment.operation if assessment else None,
        agent_writes_files=assessment.writes_files if assessment else None,
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


def _load_agent_assessment(path: Path) -> AgentAssessment:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise click.ClickException(f"Failed to read assessment file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise click.ClickException(f"Invalid assessment JSON: {exc}") from exc
    try:
        return AgentAssessment.model_validate(data)
    except Exception as exc:
        raise click.ClickException(f"Invalid assessment schema: {exc}") from exc


@click.command("governed-start")
@click.argument("description", required=False)
@click.option(
    "--files",
    "files",
    default="",
    help="Comma-separated list of files that will be touched.",
)
@click.option(
    "--contracts/--no-contracts",
    default=None,
    help="Whether the work touches a public contract surface. Auto-inferred from description when omitted.",
)
@click.option(
    "--external/--no-external",
    default=None,
    help="Whether the work has external side effects or persisted data. Auto-inferred from description when omitted.",
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
@click.option(
    "--assessment",
    "assessment_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help="JSON file containing an agent preflight assessment.",
)
@click.option(
    "--recommended-route",
    type=click.Choice([path.value for path in RoutingPath]),
    default=None,
    help="Agent-recommended route from preflight assessment.",
)
@click.option(
    "--risk",
    type=click.Choice(["low", "medium", "high"]),
    default=None,
    help="Agent-assessed task risk.",
)
@click.option(
    "--change-kind",
    default="",
    help="Agent-assessed change kind, for example single-file-doc or local-test.",
)
@click.option(
    "--queue",
    "queue_item_id",
    default=None,
    help="Queue item id to use as the governing task context.",
)
@click.pass_context
def governed_start_cmd(
    ctx: click.Context,
    description: str | None,
    files: str,
    contracts: bool | None,
    external: bool | None,
    unclear: bool,
    rigor_override: str | None,
    companions: tuple[str, ...],
    assessment_path: Path | None,
    recommended_route: str | None,
    risk: str | None,
    change_kind: str,
    queue_item_id: str | None,
) -> None:
    """Classify an incoming task and produce the canonical disclosure."""
    project_root: Path = ctx.obj["project_root"]
    queue_item = None
    queue_items = []
    if queue_item_id:
        config = load_config(project_root)
        queue_items = read_queue(config.queue_file)
        queue_item = _find_queue_item(queue_items, queue_item_id)
        if queue_item is None:
            raise click.ClickException(f"Queue item not found: {queue_item_id}")
        queue_validation = validate_queue(project_root)
        if not queue_validation.passed:
            problems = "\n".join(
                f"- [{finding.level}] {finding.target}: {finding.message}"
                for finding in queue_validation.findings
            )
            raise click.ClickException(f"Queue validation failed:\n{problems}")
        _validate_queue_context(queue_item, queue_items)

    loaded_assessment = (
        _load_agent_assessment(assessment_path) if assessment_path is not None else None
    )
    if queue_item is not None:
        explicit_route = (
            RoutingPath(recommended_route)
            if recommended_route is not None
            else loaded_assessment.recommended_route
            if loaded_assessment is not None
            else None
        )
        if explicit_route is not None and explicit_route is not RoutingPath.GOVERNED_PATH:
            raise click.ClickException(
                "--queue requires governed-path; queue start is an execution binding."
            )
    assessment_route = (
        RoutingPath.GOVERNED_PATH
        if queue_item is not None
        else RoutingPath(recommended_route)
        if recommended_route is not None
        else loaded_assessment.recommended_route
        if loaded_assessment is not None
        else None
    )
    assessment_risk = (
        risk
        if risk is not None
        else loaded_assessment.risk
        if loaded_assessment is not None
        else "medium"
    )
    assessment_change_kind = change_kind or (
        loaded_assessment.change_kind if loaded_assessment is not None else ""
    )
    assessment = loaded_assessment
    if assessment is None and (
        assessment_route is not None or risk is not None or assessment_change_kind
    ):
        assessment = AgentAssessment(
            user_request=description or "",
            change_kind=assessment_change_kind,
            risk=cast(Literal["low", "medium", "high"], assessment_risk),
            recommended_route=assessment_route,
            recommended_rigor=cast(
                Literal["light", "standard", "strict"] | None, rigor_override
            ),
        )
    elif assessment is not None and (
        recommended_route is not None or risk is not None or change_kind
    ):
        assessment = assessment.model_copy(
            update={
                "recommended_route": assessment_route,
                "risk": assessment_risk,
                "change_kind": assessment_change_kind,
            }
        )

    resolved_description = description
    if queue_item is not None and not resolved_description:
        resolved_description = _queue_item_description(queue_item) or queue_item.raw
    if not resolved_description and assessment is not None:
        resolved_description = (
            assessment.user_request or assessment.agent_interpretation
        )
    if not resolved_description:
        raise click.UsageError("Missing DESCRIPTION or --assessment user_request.")

    # Auto-infer --contracts and --external from description when not
    # explicitly passed.  This prevents misrouting when agents omit flags.
    inferred_contracts, inferred_external = _infer_flags(resolved_description)
    resolved_contracts = (
        contracts
        if contracts is not None
        else assessment.touches_public_contract
        if assessment is not None
        else inferred_contracts
    )
    resolved_external = (
        external
        if external is not None
        else assessment.has_external_side_effects
        if assessment is not None
        else inferred_external
    )
    resolved_unclear = unclear or (assessment.scope_unclear if assessment else False)
    effective_rigor = rigor_override or (
        assessment.recommended_rigor if assessment is not None else None
    )

    assessed_files = assessment.intended_files if assessment is not None else ()
    has_file_changes = (
        bool(files.strip())
        or bool(assessed_files)
        or (assessment.writes_files if assessment is not None else False)
        or resolved_contracts
        or resolved_external
    )
    payload = RoutingInput(
        description=resolved_description,
        has_file_changes=has_file_changes,
        is_public_contract=resolved_contracts,
        has_external_side_effect=resolved_external,
        is_unclear_or_high_risk=resolved_unclear,
        companion_skills=tuple(companions),
        rigor_tier=effective_rigor,
        agent_assessment=assessment,
    )
    result = _evaluate(payload, project_root)

    # Resolve rigor tier for session storage.
    resolved_rigor = resolve_rigor(effective_rigor, resolved_description)

    # Create a governance session for governed-path tasks.
    session_id: str | None = None
    if result.path is RoutingPath.GOVERNED_PATH:
        from datetime import datetime, timezone

        session_id = (
            queue_item.session_id
            if queue_item and queue_item.session_id
            else generate_session_id(resolved_description)
        )
        if queue_item is not None:
            _validate_resolved_queue_session(queue_item, queue_items, session_id)
        session = SessionState(
            session_id=session_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            description=resolved_description,
            routing_path=result.path,
            current_layer=result.current_layer,
            companion_skills=payload.companion_skills,
            rigor_tier=resolved_rigor.value,
        )
        session_path = create_session(project_root, session)
        config = load_config(project_root)
        if queue_item is None:
            append_governed_queue_item(
                config.queue_file,
                session_id=session_id,
                description=resolved_description,
                layer=result.current_layer or HarnessLayer.INTAKE_ORIENTATION,
                rigor_tier=resolved_rigor.value,
            )
        else:
            mark_queue_item_status(
                config.queue_file,
                task_id=queue_item.id
                or queue_item.session_id
                or queue_item.change_id
                or queue_item_id
                or session_id,
                status="active",
                session_id=session_id,
            )
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
                bilingual(
                    "priority.runtime_warning", count=len(competing), names=names
                ),
                err=True,
            )
    except Exception:
        pass  # priority scan must never block governed-start

    if ctx.obj.get("json_output"):
        click.echo(
            json.dumps(
                {
                    "path": result.path.value,
                    "rationale": result.rationale,
                    "current_layer": result.current_layer.value
                    if result.current_layer
                    else None,
                    "layer_path": (
                        _format_layer_path(result.rigor_tier)
                        if result.path is RoutingPath.GOVERNED_PATH
                        and result.rigor_tier
                        else None
                    ),
                    "next_layer": (
                        next_layer.value
                        if (
                            result.path is RoutingPath.GOVERNED_PATH
                            and result.rigor_tier
                            and (
                                next_layer := _next_layer(
                                    result.current_layer,
                                    result.rigor_tier,
                                )
                            )
                        )
                        else None
                    ),
                    "primary_skill": result.primary_skill,
                    "disclosure": result.disclosure,
                    "recommended_next_command": result.recommended_next_command,
                    "session_id": session_id,
                    "skill_version_warning": result.skill_version_warning,
                    "rigor_tier": result.rigor_tier,
                    "agent_assessment": (
                        assessment.model_dump(mode="json") if assessment else None
                    ),
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
        click.echo(
            bilingual("governed_start.current_layer", layer=result.current_layer.value)
        )
    if result.primary_skill:
        click.echo(
            bilingual("governed_start.primary_skill", skill=result.primary_skill)
        )
    if result.rigor_tier:
        click.echo(bilingual("governed_start.rigor_tier", tier=result.rigor_tier))
    if result.path is RoutingPath.GOVERNED_PATH and result.rigor_tier:
        click.echo(
            bilingual(
                "governed_start.layer_path",
                path=_format_layer_path(result.rigor_tier),
            )
        )
        next_layer = _next_layer(result.current_layer, result.rigor_tier)
        if next_layer:
            click.echo(bilingual("governed_start.next_layer", layer=next_layer.value))
        click.echo(bilingual("governed_start.path_hint"))
    click.echo("")
    click.echo(bilingual("governed_start.disclosure"))
    click.echo(result.disclosure)
    click.echo("")
    click.echo(bilingual("governed_start.next", cmd=result.recommended_next_command))
    if session_id:
        click.echo(bilingual("session.created", session_id=session_id))


__all__ = ["governed_start_cmd", "_evaluate"]
