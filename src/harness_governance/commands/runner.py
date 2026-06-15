"""``harness runner`` command."""

from __future__ import annotations

import json as _json
import sys
from pathlib import Path

import click

from ..commands.verify import verify_cmd
from ..messages import bilingual
from ..runner.adapters.codex_cli import CodexCliExecutor
from ..runner.adapters.generic import SubprocessAgentExecutor
from ..runner.loop import AutonomousReadyLoop
from ..runner.orchestrator import OrchestratorPromptBuilder
from ..runner.result_parser import ResultParser, append_invocation_log
from ..runner.template_renderer import TemplateRenderer
from ..runner.variables import VariableExtractor


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
    type=click.Choice(["codex", "subprocess", "orchestrator"]),
    default="subprocess",
    show_default=True,
    help="Which AgentExecutor to use. 'orchestrator' generates a Subagent prompt instead of running an external process.",
)
@click.option(
    "--command",
    "command",
    default=None,
    help="Subprocess command template (must contain ``{prompt}`` or accept the prompt as a final argument when ``--prompt-as-arg`` is set).",
)
@click.option(
    "--prompt-as-arg/--prompt-template",
    default=False,
    help="Pass the prompt as the final argument of ``--command`` instead of substituting ``{prompt}``.",
)
@click.option(
    "--model",
    "model",
    default=None,
    help="Model name for the Codex executor.",
)
@click.option(
    "--verification",
    "verification",
    default=None,
    help="Optional verification preset (e.g., ``routing-guardrails``) to run after each round.",
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
    "--invocation-log",
    "invocation_log",
    default=".harness/invocations.ndjson",
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
    command: str | None,
    prompt_as_arg: bool,
    model: str | None,
    verification: str | None,
    queue_file: Path,
    checkpoint_file: Path,
    invocation_log: Path,
    dry_run: bool,
    output_file: Path | None,
) -> None:
    """Start the autonomous-ready loop."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())

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
            queue_file=queue_file,
            checkpoint_file=checkpoint_file,
            mode=mode,
            max_rounds=max_rounds,
            platform=platform_value,
        )

        if output_file:
            output_path = (project_root / output_file).resolve()
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
                "\n" + bilingual("runner.unresolved_variables", count=str(len(prompt.missing_variables)), vars=vars_preview),
                err=True,
            )
        return

    if executor == "codex":
        agent = CodexCliExecutor(model=model, workdir=project_root)
    else:
        if not command:
            raise click.ClickException(bilingual("runner.command_required"))
        agent = SubprocessAgentExecutor(
            command_template=command,
            prompt_as_arg=prompt_as_arg,
            workdir=project_root,
        )

    if dry_run:
        from ..file_ops.queue import read_queue

        items = read_queue(project_root / queue_file)
        target = next((i for i in items if i.ready), None) or next(
            (i for i in items if i.active), None
        )
        if target is None:
            click.echo(bilingual("runner.dry_run_no_item"))
            return
        click.echo(_default_prompt(target))
        return

    loop = AutonomousReadyLoop(
        executor=agent,
        project_root=project_root,
        queue_file=queue_file,
        checkpoint_file=checkpoint_file,
        invocation_log=invocation_log,
        prompt_builder=_default_prompt,
        timeout_seconds=timeout_seconds,
    )
    result = loop.run(mode=mode, max_rounds=max_rounds)

    click.echo(
        _json.dumps(
            {
                "executor": agent.name,
                "rounds": result.rounds,
                "stopped_for": result.stopped_for,
                "invocations": [s.to_ndjson() for s in result.invocations],
            },
            indent=2,
            ensure_ascii=False,
        )
    )

    if verification:
        from .verify import _PRESETS
        if verification not in _PRESETS:
            raise click.ClickException(
                bilingual("runner.unknown_verification", preset=verification, available=", ".join(sorted(_PRESETS)))
            )
        # Delegate to verify for a sanity check after the loop.
        ctx.invoke(verify_cmd, preset=verification)

    if result.stopped_for in {"failed", "blocked", "error"}:
        raise click.exceptions.Exit(code=1)


__all__ = ["runner_group", "runner_start_cmd", "runner_render_cmd", "runner_parse_result_cmd"]


@runner_group.command("render")
@click.option(
    "--role",
    "role",
    required=True,
    type=click.Choice([
        "planner", "contract-writer", "implementer", "reviewer",
        "adr-writer", "fact-finder-reviewer", "readiness-gate-writer",
        "document-gardener", "integrator",
    ]),
    help="Role template to render.",
)
@click.option(
    "--queue",
    "queue_file",
    default="NEXT.md",
    show_default=True,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Queue file (NEXT.md).",
)
@click.option(
    "--change-id",
    "change_id",
    default=None,
    help="Change packet ID. If omitted, extracted from the first ready item.",
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
    role: str,
    queue_file: Path,
    change_id: str | None,
    output_file: Path | None,
) -> None:
    """Render a role prompt with extracted variables.

    Extracts variables from the queue item and its change packet,
    then renders the role template with exact substitution.
    """
    project_root: Path = ctx.obj.get("project_root", Path.cwd())

    from ..file_ops.queue import read_queue

    items = read_queue(project_root / queue_file)
    target = next((i for i in items if i.ready), None) or next(
        (i for i in items if i.active), None
    )
    if target is None:
        raise click.ClickException(bilingual("runner.no_ready_item"))

    extractor = VariableExtractor()
    variables = extractor.extract_for_role(project_root, target, role)

    renderer = TemplateRenderer()
    rendered = renderer.render(role, variables)

    if output_file:
        output_path = (project_root / output_file).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(rendered, encoding="utf-8")
        click.echo(bilingual("runner.render_written", role=role, path=str(output_path)))
    else:
        click.echo(rendered)

    unresolved = renderer.find_unresolved(rendered)
    if unresolved:
        unresolved_preview = ", ".join(unresolved[:5])
        if len(unresolved) > 5:
            unresolved_preview += "..."
        click.echo(
            "\n" + bilingual("runner.render_unresolved", count=str(len(unresolved)), vars=unresolved_preview),
            err=True,
        )


@runner_group.command("parse-result")
@click.option(
    "--role",
    "role",
    required=True,
    type=click.Choice([
        "planner", "contract-writer", "implementer", "reviewer",
        "adr-writer", "fact-finder-reviewer", "readiness-gate-writer",
        "document-gardener", "integrator",
    ]),
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
@click.pass_context
def runner_parse_result_cmd(
    ctx: click.Context,
    role: str,
    input_file: Path | None,
    invocation_log: Path,
    round_index: int,
) -> None:
    """Parse a subagent result and append to the invocation log.

    Reads JSON from stdin or a file, parses it into a structured
    SubagentResult, and appends an NDJSON entry to the invocation log.
    """
    project_root: Path = ctx.obj.get("project_root", Path.cwd())

    if input_file:
        text = (project_root / input_file).read_text(encoding="utf-8")
    else:
        text = sys.stdin.read()

    parser = ResultParser()
    result = parser.parse(text, role=role)

    log_path = (project_root / invocation_log).resolve()
    append_invocation_log(log_path, result, round_index=round_index)

    click.echo(_json.dumps(
        {
            "role": result.role,
            "filesChanged": result.files_changed,
            "contractBlocked": result.contract_blocked,
            "verdict": result.verdict,
            "verificationPassed": result.verification_passed,
            "isAcceptable": result.is_acceptable,
            "findingsCount": len(result.findings),
        },
        indent=2,
        ensure_ascii=False,
    ))
