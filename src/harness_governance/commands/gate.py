"""``harness gate`` commands — programmatic gate verification.

The gate command group is the cross-platform enforcement interface
(Layer 2 of the 5-layer defense).  Agent skill files instruct agents to
run ``harness gate check <layer>`` before any ``Write`` / ``Edit``.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import click

from ..messages import bilingual
from ..models.schemas import GateResult, CheckFinding
from ..session import TransitionRecord, find_active_session, load_session
from ..state_machine.gates import (
    LayerGateEngine,
    LockFileManager,
    layers_for_tier,
)
from ..state_machine.layers import HarnessLayer
from ..state_machine.rigor import RigorTier


@click.group("gate")
def gate_group() -> None:
    """Programmatic gate verification and lock-file management."""


# ---------------------------------------------------------------------------
# gate check
# ---------------------------------------------------------------------------


@gate_group.command("check")
@click.argument("layer")
@click.option(
    "--session-id",
    default=None,
    help="Session ID (auto-detected from active session when omitted).",
)
@click.pass_context
def gate_check(ctx: click.Context, layer: str, session_id: str | None) -> None:
    """Verify that *layer*'s gate is satisfied.

    LAYER is the layer name (e.g. ``intake-orientation``,
    ``implementation``).

    Exit code 0 = gate passed (lock file written).
    Exit code 1 = gate failed.
    """
    project_root: Path = ctx.obj["project_root"]

    # Resolve the layer.
    try:
        hlayer = HarnessLayer(layer)
    except ValueError:
        valid = ", ".join(m.value for m in HarnessLayer)
        raise click.BadParameter(f"Invalid layer: {layer!r}. Valid: {valid}")

    # Find the active session.
    session = None
    if session_id:
        from ..session import load_session

        session = load_session(project_root, session_id)
    else:
        session = find_active_session(project_root)

    if session is None:
        click.echo(bilingual("gate.no_session"), err=True)
        ctx.exit(1)

    # Run the gate check (v0.7.1: timed).
    engine = LayerGateEngine()
    _check_start = time.perf_counter()
    status = engine.check(session, project_root, hlayer)
    _elapsed_ms = (time.perf_counter() - _check_start) * 1000.0
    status = status.model_copy(update={"check_duration_ms": round(_elapsed_ms, 2)})

    # Write lock file if passed.
    is_json = ctx.obj.get("json_output", False)
    if status.passed:
        locks = LockFileManager(project_root)
        lock_path = locks.write_lock(hlayer, status, session)
        if not is_json:
            click.echo(
                bilingual(
                    "gate.check.passed",
                    layer=layer,
                    questions=status.questions_answered,
                    required=status.questions_required,
                ),
                err=True,
            )
        if ctx.obj.get("verbose", False):
            click.echo(f"  Lock: {lock_path}", err=True)
    else:
        if not is_json:
            click.echo(
                bilingual(
                    "gate.check.failed",
                    layer=layer,
                    questions=status.questions_answered,
                    required=status.questions_required,
                    missing=", ".join(status.artifacts_missing)
                    if status.artifacts_missing
                    else "none",
                ),
                err=True,
            )

    # JSON output.
    if ctx.obj.get("json_output"):
        findings: list[CheckFinding] = []
        if status.questions_answered < status.questions_required:
            findings.append(
                CheckFinding(
                    check="layer-gate",
                    target=layer,
                    level="error",
                    message=(
                        f"Questions: {status.questions_answered}/"
                        f"{status.questions_required}"
                    ),
                )
            )
        for pat in status.artifacts_missing:
            findings.append(
                CheckFinding(
                    check="layer-gate",
                    target=pat,
                    level="error",
                    message=f"Required artifact not found: {pat}",
                )
            )
        result = GateResult(
            layer=layer,
            passed=status.passed,
            findings=tuple(findings),
            status=status,
        )
        click.echo(
            result.model_dump_json(indent=2),
        )

    if not status.passed:
        ctx.exit(1)


# ---------------------------------------------------------------------------
# gate status
# ---------------------------------------------------------------------------


@gate_group.command("status")
@click.argument("layer", required=False)
@click.pass_context
def gate_status(ctx: click.Context, layer: str | None) -> None:
    """Show lock-file status for one layer or all 12 layers."""
    project_root: Path = ctx.obj["project_root"]
    locks = LockFileManager(project_root)
    session = find_active_session(project_root)
    tier = RigorTier(session.rigor_tier) if session else RigorTier.STRICT
    required_layers = layers_for_tier(tier)

    if layer:
        try:
            hlayer = HarnessLayer(layer)
        except ValueError:
            valid = ", ".join(m.value for m in HarnessLayer)
            raise click.BadParameter(f"Invalid layer: {layer!r}. Valid: {valid}")
        layers_to_show = [hlayer]
    else:
        layers_to_show = list(required_layers)

    if ctx.obj.get("json_output"):
        results = []
        for hl in layers_to_show:
            lock_data = locks.read_lock(hl)
            results.append(
                {
                    "layer": hl.value,
                    "locked": lock_data is not None,
                    "lock_data": lock_data,
                }
            )
        click.echo(json.dumps(results, indent=2, ensure_ascii=False))
        return

    for hl in layers_to_show:
        lock_data = locks.read_lock(hl)
        if lock_data:
            click.echo(
                bilingual(
                    "gate.status.locked",
                    layer=hl.value,
                    session=lock_data.get("session_id", "?"),
                    passed_at=lock_data.get("passed_at", "?"),
                )
            )
        else:
            click.echo(bilingual("gate.status.unlocked", layer=hl.value))


# ---------------------------------------------------------------------------
# gate reset
# ---------------------------------------------------------------------------


@gate_group.command("reset")
@click.argument("layer", required=False)
@click.option("--confirmed", is_flag=True, default=False, help="Required safety flag.")
@click.option(
    "--all", "all_layers", is_flag=True, default=False, help="Reset all locks."
)
@click.pass_context
def gate_reset(
    ctx: click.Context,
    layer: str | None,
    confirmed: bool,
    all_layers: bool,
) -> None:
    """Remove a lock file (requires --confirmed).

    Use ``--all`` to remove all lock files at once.
    """
    if not confirmed:
        raise click.UsageError(bilingual("gate.reset.requires_confirmed"))

    if not all_layers and not layer:
        raise click.UsageError("Must specify LAYER or --all.")

    project_root: Path = ctx.obj["project_root"]
    locks = LockFileManager(project_root)

    if all_layers:
        count = locks.remove_all_locks()
        click.echo(bilingual("gate.reset.all_removed", count=count))
        return

    try:
        hlayer = HarnessLayer(layer)
    except ValueError:
        valid = ", ".join(m.value for m in HarnessLayer)
        raise click.BadParameter(f"Invalid layer: {layer!r}. Valid: {valid}")

    if locks.remove_lock(hlayer):
        click.echo(bilingual("gate.reset.removed", layer=layer))
    else:
        click.echo(bilingual("gate.reset.not_found", layer=layer))


# ---------------------------------------------------------------------------
# gate timing
# ---------------------------------------------------------------------------


@gate_group.command("timing")
@click.option(
    "--session",
    "session_id",
    default=None,
    help="Session ID (defaults to active session).",
)
@click.option(
    "--all",
    "all_sessions",
    is_flag=True,
    default=False,
    help="Show timing for all sessions.",
)
@click.pass_context
def gate_timing(
    ctx: click.Context,
    session_id: str | None,
    all_sessions: bool,
) -> None:
    """Show per-layer timing from session transitions and gate lock files."""
    project_root: Path = ctx.obj["project_root"]

    if all_sessions:
        from ..session import list_sessions

        sessions = list_sessions(project_root)
    elif session_id:
        try:
            sessions = [load_session(project_root, session_id)]
        except FileNotFoundError:
            raise click.ClickException(
                bilingual("session.not_found", session_id=session_id)
            )
    else:
        session = find_active_session(project_root)
        if session is None:
            raise click.ClickException(bilingual("gate.no_session"))
        sessions = [session]

    if ctx.obj.get("json_output"):
        output = []
        for s in sessions:
            json_transitions = []
            for t in s.transitions:
                t_rec: TransitionRecord = t
                json_transitions.append(
                    {
                        "from": t_rec.from_layer.value,
                        "to": t_rec.to_layer.value,
                        "timestamp": t_rec.timestamp,
                        "duration_s": round(t_rec.duration_seconds, 3),
                        "verdict": t_rec.engine_verdict,
                    }
                )
            locks_mgr = LockFileManager(project_root)
            gate_timings: dict[str, float] = {}
            for t in s.transitions:
                t_rec2: TransitionRecord = t
                lock_data = locks_mgr.read_lock(t_rec2.from_layer)
                if lock_data:
                    gate_timings[t_rec2.from_layer.value] = lock_data.get(
                        "check_duration_ms", 0.0
                    )
            output.append(
                {
                    "session_id": s.session_id,
                    "rigor_tier": s.rigor_tier,
                    "transitions": json_transitions,
                    "gate_check_timings_ms": gate_timings,
                }
            )
        click.echo(json.dumps(output, indent=2, ensure_ascii=False))
        return

    for s in sessions:
        click.echo(bilingual("gate.timing.header", session=s.session_id))
        transitions: tuple[TransitionRecord, ...] = s.transitions
        if not transitions:
            click.echo(bilingual("gate.timing.no_transitions"))
            continue

        total = 0.0
        for t in transitions:
            dur = t.duration_seconds
            total += dur
            verdict = "OK" if t.engine_verdict else "BLOCKED"
            click.echo(
                bilingual(
                    "gate.timing.transition_row",
                    from_layer=t.from_layer.value,
                    to_layer=t.to_layer.value,
                    duration=round(dur, 3),
                    verdict=verdict,
                )
            )

        avg = total / len(transitions) if transitions else 0.0
        click.echo(
            bilingual(
                "gate.timing.summary",
                total=round(total, 3),
                count=len(transitions),
                avg=round(avg, 3),
            )
        )
        click.echo("")
