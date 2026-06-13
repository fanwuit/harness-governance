"""``harness runner`` command."""

from __future__ import annotations

import json as _json
import os
import shlex
from pathlib import Path

import click

from ..runner.adapters.codex_cli import CodexCliExecutor
from ..runner.adapters.generic import SubprocessAgentExecutor
from ..runner.loop import AutonomousReadyLoop


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
    type=click.Choice(["codex", "subprocess"]),
    default="subprocess",
    show_default=True,
    help="Which AgentExecutor to use.",
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
    default=".harness/codex-exec-invocations.ndjson",
    show_default=True,
    type=click.Path(dir_okay=False, path_type=Path),
)
@click.option(
    "--dry-run/--no-dry-run",
    default=False,
    help="Build the prompt and exit without invoking any executor.",
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
) -> None:
    """Start the autonomous-ready loop."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())

    if executor == "codex":
        agent = CodexCliExecutor(model=model, workdir=project_root)
    else:
        if not command:
            raise click.ClickException("--command is required when --executor=subprocess.")
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
            click.echo("dry-run: no ready or active queue item")
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
                f"Unknown verification preset: {verification!r}. Available: {', '.join(sorted(_PRESETS))}."
            )
        # Delegate to verify for a sanity check after the loop.
        ctx.invoke(
            __import__(
                "harness_governance.commands.verify", fromlist=["verify_cmd"]
            ).verify_cmd,
            preset=verification,
        )

    if result.stopped_for in {"failed", "blocked", "error"}:
        raise click.exceptions.Exit(code=1)


__all__ = ["runner_group", "runner_start_cmd"]