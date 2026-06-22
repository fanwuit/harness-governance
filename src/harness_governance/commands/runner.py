"""``harness runner`` command."""

from __future__ import annotations

import json as _json
import sys
from pathlib import Path
from typing import Literal

import click

from ..messages import bilingual
from ..runner.native_handoff import (
    append_completion,
    append_spawn,
    new_request_id,
    paths_for,
    write_request,
)
from ..runner.orchestrator import OrchestratorPromptBuilder
from ..runner.result_parser import ResultParser, append_invocation_log
from ..runner.template_renderer import TemplateRenderer
from ..runner.variables import VariableExtractor, is_not_found


def _default_prompt(queue_item) -> str:
    return (
        "You are one round of an autonomous harness runner.\n"
        "Process the queue item below end-to-end, then emit exactly one of:\n"
        "  AUTONOMOUS_READY_DONE\n"
        "  AUTONOMOUS_BLOCKED\n"
        "  AUTONOMOUS_BOUNDARY_REACHED\n"
        "  AUTONOMOUS_FAILED\n"
        "  AUTONOMOUS_CONTEXT_HANDOFF\n\n"
        f"Queue item:\n{queue_item.raw}\n"
    )


def _resolve_queue_file(project_root: Path, queue_file: Path) -> Path:
    from ..config import load_config

    cfg = load_config(project_root)
    resolved = queue_file
    if queue_file == Path("NEXT.md"):
        resolved = cfg.queue_file
    elif not queue_file.is_absolute():
        resolved = project_root / queue_file

    if cfg.require_queue and not resolved.is_file():
        raise click.ClickException(
            "Required scheduler queue file is missing. Run `harness init` "
            "to create NEXT.md, restore the configured queue_file, or set "
            "require_queue = false only with an explicit project waiver."
        )
    return resolved


def _find_queue_item(items, item_id: str):
    lowered = item_id.strip().lower()
    for item in items:
        candidates = (
            item.id,
            item.session_id,
            item.change_id,
        )
        if any(candidate and candidate.lower() == lowered for candidate in candidates):
            return item
        if item.raw.lower().startswith("[") and lowered in item.raw.lower():
            return item
    return None


def _target_queue_item(project_root: Path, queue_file: Path, queue_item_id: str | None):
    from ..file_ops.queue import read_queue

    items = read_queue(project_root / queue_file)
    if queue_item_id:
        target = _find_queue_item(items, queue_item_id)
        if target is None:
            raise click.ClickException(f"Queue item not found: {queue_item_id}")
        return target
    target = next((i for i in items if i.ready), None) or next(
        (i for i in items if i.active), None
    )
    if target is None:
        raise click.ClickException(bilingual("runner.no_ready_item"))
    return target


def _native_route(project_root: Path, role: str):
    from ..config import load_config
    from ..state_machine.capability_routing import (
        resolve_adapter,
        resolve_required_tier,
        verifier_required_for_tier,
    )

    cfg = load_config(project_root)
    required_tier = resolve_required_tier(role, cfg)
    route = resolve_adapter(role, required_tier, project_root=project_root)
    if route is None:
        raise click.ClickException(
            f"No native subagent declaration found for role {role!r} "
            f"at tier {required_tier.value!r}."
        )
    adapter = route.get("adapter", "")
    if adapter != "subagent":
        raise click.ClickException(
            f"Adapter {adapter!r} is not a native subagent adapter. "
            "Governed native handoff only accepts adapter='subagent'."
        )
    return cfg, required_tier, route, verifier_required_for_tier(required_tier)


def _required_prompt_failures(role: str, variables) -> list[str]:
    if role not in {"reviewer", "reviewer-verifier", "verifier", "fact-finder-reviewer"}:
        return []
    required = {
        "FORBIDDEN_SCOPE": variables.forbidden_scope,
        "VERIFICATION_COMMANDS": variables.verification_commands,
        "DONE_WHEN": variables.done_when,
    }
    return [name for name, value in required.items() if not value or is_not_found(value)]


@click.group("runner")
def runner_group() -> None:
    """Run the autonomous-ready loop."""


@runner_group.command("start")
@click.option(
    "--mode",
    "mode",
    type=click.Choice(["bounded", "boundary"]),
    default="bounded",
    show_default=True,
    help="BoundedBatch (default) caps rounds strictly; RunUntilBoundary uses the cap as a fuse.",
)
@click.option(
    "--max-rounds",
    "max_rounds",
    type=int,
    default=1,
    show_default=True,
    help="Maximum rounds to run. In boundary mode the cap defaults to 50 when this is left at 1.",
)
@click.option(
    "--timeout-seconds",
    "timeout_seconds",
    type=int,
    default=1800,
    show_default=True,
    help="Per-round timeout.",
)
@click.option(
    "--executor",
    "executor",
    type=click.Choice(["orchestrator"]),
    default="orchestrator",
    show_default=True,
    help=(
        "Generate a prompt for native "
        "subagent dispatch. Harness core "
        "does not execute platform or process agent workers."
    ),
)
@click.option(
    "--queue",
    "queue_file",
    default="NEXT.md",
    show_default=True,
    type=click.Path(dir_okay=False, path_type=Path),
)
@click.option(
    "--checkpoint",
    "checkpoint_file",
    default=".harness/run-checkpoint.md",
    show_default=True,
    type=click.Path(dir_okay=False, path_type=Path),
)
@click.option(
    "--dry-run/--no-dry-run",
    default=False,
    help="Build the prompt and exit without invoking any executor.",
)
@click.option(
    "--output",
    "output_file",
    default=None,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Output file for orchestrator prompt (only with --executor orchestrator). Default: stdout.",
)
@click.pass_context
def runner_start_cmd(
    ctx: click.Context,
    mode: str,
    max_rounds: int,
    timeout_seconds: int,
    executor: str,
    queue_file: Path,
    checkpoint_file: Path,
    dry_run: bool,
    output_file: Path | None,
) -> None:
    """Start the autonomous-ready loop."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    _mode: Literal["bounded", "boundary"] = mode  # type: ignore[assignment]
    resolved_queue_file = _resolve_queue_file(project_root, queue_file)

    # Orchestrator mode: generate prompt, don't run executor
    if executor == "orchestrator":
        # Determine platform from config or explicit override
        platform_value = None
        try:
            from ..config import load_config

            cfg = load_config(project_root)
            platform_value = cfg.agent_platform
        except Exception:
            pass  # fall back to generic if config is missing

        builder = OrchestratorPromptBuilder()
        prompt = builder.build(
            project_root=project_root,
            queue_file=resolved_queue_file,
            checkpoint_file=checkpoint_file,
            mode=_mode,
            max_rounds=max_rounds,
            platform=platform_value,
        )

        if output_file:
            output_path = (project_root / output_file).resolve()
            from ..file_ops._util import assert_inside

            try:
                assert_inside(project_root, output_path)
            except ValueError as exc:
                raise click.ClickException(str(exc)) from exc
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(prompt.text, encoding="utf-8")
            click.echo(bilingual("runner.orchestrator_written", path=str(output_path)))
        else:
            click.echo(prompt.text)

        if prompt.missing_variables:
            vars_preview = ", ".join(prompt.missing_variables[:5])
            if len(prompt.missing_variables) > 5:
                vars_preview += "..."
            click.echo(
                "\n"
                + bilingual(
                    "runner.unresolved_variables",
                    count=str(len(prompt.missing_variables)),
                    vars=vars_preview,
                ),
                err=True,
            )
        return

@runner_group.command("dispatch")
@click.option(
    "--role",
    "role",
    required=False,
    default=None,
    type=click.Choice(
        [
            "planner",
            "fact-finder",
            "contract-test-writer",
            "contract-writer",
            "implementer",
            "product-implementer",
            "reviewer",
            "reviewer-verifier",
            "verifier",
            "architect-adr",
            "adr-writer",
            "fact-finder-reviewer",
            "readiness-gate-writer",
            "document-gardener",
            "integrator",
        ]
    ),
    help="Role to dispatch.",
)
@click.option(
    "--prompt",
    "prompt_text",
    default=None,
    help="Prompt text for the subagent. If omitted, a default prompt is used.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    default=False,
    help="Resolve the adapter and print the dispatch plan without executing.",
)
@click.option(
    "--session-id",
    "session_id",
    default=None,
    help="Session ID for provenance recording. Auto-detected if omitted.",
)
@click.pass_context
def runner_dispatch_cmd(
    ctx: click.Context,
    role: str,
    prompt_text: str | None,
    dry_run: bool,
    session_id: str | None,
) -> None:
    """Dispatch a subagent for a specific role.

    Resolves the capability tier and adapter from agent declarations,
    executes the subagent, and records provenance in the skill chain.

    This is the primary mechanism for capabilitiy-tier-aware dispatch:
    each role uses the adapter and model declared in the agent's
    ``tiers.json``.
    """
    project_root: Path = ctx.obj.get("project_root", Path.cwd())

    _cfg, tier, route, needs_verifier = _native_route(project_root, role)
    executor_name = f"native-subagent:{route['platform']}"

    # 3. Build the prompt
    if prompt_text is None:
        prompt_text = (
            f"You are a {role} subagent at capability tier '{tier.value}'.\n"
            f"Please complete the task described below.\n"
            f"Respond with structured JSON output.\n\n"
            f"## Task\n\nThis is a simulated dispatch for role '{role}' "
            f"at tier '{tier.value}'."
        )

    if dry_run:
        click.echo("=== Dispatch Plan (dry-run) ===")
        click.echo(f"  Role:         {role}")
        click.echo(f"  Required tier: {tier.value}")
        click.echo(f"  Verifier needed: {needs_verifier}")
        click.echo(f"  Executor:     {executor_name}")
        click.echo(f"  Prompt:       {prompt_text[:120]}...")
        return

    click.echo(
        _json.dumps(
            {
                "status": "native_handoff_required",
                "role": role,
                "requiredTier": tier.value,
                "platform": route["platform"],
                "adapter": route["adapter"],
                "modelLabel": route.get("model_label", ""),
                "next": "Run `harness runner prepare-native`, then spawn via the platform-native subagent mechanism.",
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return

__all__ = [
    "runner_group",
    "runner_start_cmd",
    "runner_render_cmd",
    "runner_prepare_native_cmd",
    "runner_record_native_spawn_cmd",
    "runner_parse_result_cmd",
    "runner_dispatch_cmd",
]


@runner_group.command("render")
@click.option(
    "--role",
    "role",
    required=False,
    default=None,
    type=click.Choice(
        [
            "planner",
            "fact-finder",
            "contract-test-writer",
            "contract-writer",
            "implementer",
            "product-implementer",
            "reviewer",
            "reviewer-verifier",
            "verifier",
            "architect-adr",
            "adr-writer",
            "fact-finder-reviewer",
            "readiness-gate-writer",
            "document-gardener",
            "integrator",
        ]
    ),
    help="Role template to render.",
)
@click.option(
    "--queue-file",
    "queue_file",
    default="NEXT.md",
    show_default=True,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Queue file path; NEXT.md is the default carrier.",
)
@click.option(
    "--queue",
    "queue_item_id",
    default=None,
    help="Queue item id to render. If omitted, render the first ready/active item.",
)
@click.option(
    "--change-id",
    "change_id",
    default=None,
    help="Change packet ID override. If omitted, extracted from the queue item.",
)
@click.option(
    "--session-id",
    "session_id",
    default=None,
    help="Session ID for render provenance. Must match the queue SessionId when present.",
)
@click.option(
    "--output",
    "output_file",
    default=None,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Output file. Default: stdout.",
)
@click.pass_context
def runner_render_cmd(
    ctx: click.Context,
    role: str | None,
    queue_file: Path,
    queue_item_id: str | None,
    change_id: str | None,
    session_id: str | None,
    output_file: Path | None,
) -> None:
    """Render a role prompt with extracted variables.

    Extracts variables from the queue item and its change packet,
    then renders the role template with exact substitution.
    """
    project_root: Path = ctx.obj.get("project_root", Path.cwd())

    target = _target_queue_item(project_root, queue_file, queue_item_id)

    render_role = role or target.role
    if render_role is None:
        raise click.ClickException(
            "Unable to infer role for queue render. Add Role: to the queue item "
            "or pass --role explicitly."
        )
    if queue_item_id and role and target.role and role != target.role:
        raise click.ClickException(
            f"Explicit role {role!r} does not match queue item role {target.role!r}."
        )

    resolved_session_id = session_id or target.session_id
    if target.session_id and resolved_session_id != target.session_id:
        raise click.ClickException(
            f"runner render sessionId {resolved_session_id!r} does not match "
            f"queue SessionId {target.session_id!r}."
        )

    if change_id:
        target = target.model_copy(update={"change_id": change_id})

    extractor = VariableExtractor()
    variables = extractor.extract_for_role(project_root, target, render_role)
    missing_required = _required_prompt_failures(render_role, variables)
    if missing_required:
        raise click.ClickException(
            "Missing required reviewer/verifier prompt fields: "
            + ", ".join(missing_required)
        )

    renderer = TemplateRenderer()
    rendered = renderer.render(render_role, variables)

    if output_file:
        output_path = (project_root / output_file).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
        click.echo(
            bilingual("runner.render_written", role=render_role, path=str(output_path))
        )
    else:
        click.echo(rendered)

    if resolved_session_id:
        from ..hard_gates import queue_item_key, record_render
        from ..state_machine.capability_routing import (
            resolve_adapter,
            resolve_required_tier,
            verifier_required_for_tier,
        )
        from ..config import load_config

        cfg = load_config(project_root)
        required_tier = resolve_required_tier(render_role, cfg)
        route = resolve_adapter(render_role, required_tier, project_root=project_root)
        actual_tier = required_tier.value if route else ""

        record_render(
            project_root,
            session_id=resolved_session_id,
            queue_id=queue_item_key(target),
            role=render_role,
            required_tier=required_tier.value,
            actual_tier=actual_tier,
            platform=route["platform"] if route else cfg.agent_platform,
            adapter=route["adapter"] if route else "",
            model_label=route["model_label"] if route else "",
            verifier_required=verifier_required_for_tier(required_tier),
        )

    unresolved = renderer.find_unresolved(rendered)
    if unresolved:
        unresolved_preview = ", ".join(unresolved[:5])
        if len(unresolved) > 5:
            unresolved_preview += "..."
        click.echo(
            "\n"
            + bilingual(
                "runner.render_unresolved",
                count=str(len(unresolved)),
                vars=unresolved_preview,
            ),
            err=True,
        )


@runner_group.command("prepare-native")
@click.option("--role", "role", required=True, help="Role template to render.")
@click.option(
    "--queue-file",
    "queue_file",
    default="NEXT.md",
    show_default=True,
    type=click.Path(dir_okay=False, path_type=Path),
)
@click.option("--queue", "queue_item_id", required=True, help="Queue item id.")
@click.option("--session-id", "session_id", required=True, help="Governance session id.")
@click.pass_context
def runner_prepare_native_cmd(
    ctx: click.Context,
    role: str,
    queue_file: Path,
    queue_item_id: str,
    session_id: str,
) -> None:
    """Prepare a platform-native subagent handoff request."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    target = _target_queue_item(project_root, queue_file, queue_item_id)
    if target.session_id and target.session_id != session_id:
        raise click.ClickException(
            f"session id {session_id!r} does not match queue SessionId {target.session_id!r}"
        )
    if target.role and target.role != role:
        raise click.ClickException(
            f"role {role!r} does not match queue Role {target.role!r}"
        )

    _cfg, required_tier, route, needs_verifier = _native_route(project_root, role)
    extractor = VariableExtractor()
    variables = extractor.extract_for_role(project_root, target, role)
    missing_required = _required_prompt_failures(role, variables)
    if missing_required:
        raise click.ClickException(
            "Missing required reviewer/verifier prompt fields: "
            + ", ".join(missing_required)
        )

    renderer = TemplateRenderer()
    prompt = renderer.render(role, variables)
    unresolved = renderer.find_unresolved(prompt)
    if unresolved:
        raise click.ClickException(
            "Rendered prompt contains unresolved variables: "
            + ", ".join(unresolved[:8])
        )

    from ..hard_gates import queue_item_key, record_render

    queue_id = queue_item_key(target)
    record_render(
        project_root,
        session_id=session_id,
        queue_id=queue_id,
        role=role,
        required_tier=required_tier.value,
        actual_tier=required_tier.value,
        platform=route["platform"],
        adapter=route["adapter"],
        model_label=route.get("model_label", ""),
        verifier_required=needs_verifier,
    )

    request_id = new_request_id(role)
    request = write_request(
        project_root,
        session_id=session_id,
        queue_id=queue_id,
        request_id=request_id,
        role=role,
        required_tier=required_tier.value,
        actual_tier=required_tier.value,
        platform=route["platform"],
        adapter=route["adapter"],
        model_label=route.get("model_label", ""),
        prompt_text=prompt,
    )
    p = paths_for(
        project_root,
        session_id=session_id,
        role=role,
        request_id=request_id,
    )
    click.echo(
        _json.dumps(
            {
                "status": "native_handoff_required",
                "requestId": request_id,
                "requestPath": str(p.request_path.relative_to(project_root)),
                "promptPath": request["promptPath"],
                "promptSha256": request["promptSha256"],
            },
            indent=2,
            ensure_ascii=False,
        )
    )


@runner_group.command("record-native-spawn")
@click.option("--session-id", "session_id", required=True)
@click.option("--role", "role", required=True)
@click.option("--agent-id", "agent_id", required=True)
@click.option("--request-id", "request_id", required=True)
@click.option("--status", "status", default="spawned", show_default=True)
@click.pass_context
def runner_record_native_spawn_cmd(
    ctx: click.Context,
    session_id: str,
    role: str,
    agent_id: str,
    request_id: str,
    status: str,
) -> None:
    """Record that the main agent spawned a native platform subagent."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    try:
        record = append_spawn(
            project_root,
            session_id=session_id,
            role=role,
            request_id=request_id,
            agent_id=agent_id,
            status=status,
        )
    except (FileNotFoundError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(_json.dumps(record, indent=2, ensure_ascii=False))


@runner_group.command("parse-result")
@click.option(
    "--role",
    "role",
    required=True,
    type=click.Choice(
        [
            "planner",
            "fact-finder",
            "contract-test-writer",
            "contract-writer",
            "implementer",
            "reviewer",
            "reviewer-verifier",
            "verifier",
            "architect-adr",
            "adr-writer",
            "fact-finder-reviewer",
            "readiness-gate-writer",
            "document-gardener",
            "integrator",
        ]
    ),
    help="Role that produced the result.",
)
@click.option(
    "--input",
    "input_file",
    default=None,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Input file containing subagent JSON output. Default: stdin.",
)
@click.option(
    "--invocation-log",
    "invocation_log",
    default=".harness/invocations.ndjson",
    show_default=True,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Invocation log to append to.",
)
@click.option(
    "--round",
    "round_index",
    default=0,
    type=int,
    help="Round index for the log entry.",
)
@click.option("--session-id", "session_id", default=None, help="Governance session id.")
@click.option("--request-id", "request_id", default=None, help="Native handoff request id.")
@click.option("--agent-id", "agent_id", default=None, help="Native platform agent id.")
@click.pass_context
def runner_parse_result_cmd(
    ctx: click.Context,
    role: str,
    input_file: Path | None,
    invocation_log: Path,
    round_index: int,
    session_id: str | None,
    request_id: str | None,
    agent_id: str | None,
) -> None:
    """Parse a subagent result and append to the invocation log.

    Reads JSON from stdin or a file, parses it into a structured
    SubagentResult, and appends an NDJSON entry to the invocation log.
    """
    project_root: Path = ctx.obj.get("project_root", Path.cwd())

    from ..file_ops._util import assert_inside

    if input_file:
        input_path = (project_root / input_file).resolve()
        try:
            assert_inside(project_root, input_path)
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
        text = input_path.read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()

    parser = ResultParser()
    parse_role = "reviewer" if role == "reviewer-verifier" else role
    result = parser.parse(text, role=parse_role)

    log_path = (project_root / invocation_log).resolve()
    try:
        assert_inside(project_root, log_path)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    append_invocation_log(log_path, result, round_index=round_index)
    completion = None
    if session_id or request_id or agent_id:
        if not (session_id and request_id and agent_id):
            raise click.ClickException(
                "--session-id, --request-id, and --agent-id must be provided together"
            )
        try:
            completion = append_completion(
                project_root,
                session_id=session_id,
                role=role,
                request_id=request_id,
                agent_id=agent_id,
                verdict=result.verdict,
                verification_passed=result.verification_passed,
                findings_count=len(result.findings),
            )
        except (FileNotFoundError, ValueError) as exc:
            raise click.ClickException(str(exc)) from exc

    payload = {
        "role": result.role,
        "filesChanged": result.files_changed,
        "contractBlocked": result.contract_blocked,
        "verdict": result.verdict,
        "verificationPassed": result.verification_passed,
        "isAcceptable": result.is_acceptable,
        "findingsCount": len(result.findings),
    }
    if completion:
        payload.update(
            {
                "requestId": completion["requestId"],
                "agentId": completion["agentId"],
                "promptSha256": completion["promptSha256"],
                "status": completion["status"],
            }
        )
    click.echo(_json.dumps(payload, indent=2, ensure_ascii=False))

