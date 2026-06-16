"""``harness layer`` commands — advance and inspect governance session layers.

The ``layer advance`` subcommand is the primary mechanism for *real state
advancement*: it loads the active session, evaluates the proposed
transition through :class:`~harness_governance.state_machine.engine.StateMachineEngine`,
and persists the result back to the session file.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import click

from ..messages import bilingual
from ..session import (
    TransitionRecord,
    find_active_session,
    load_session,
    save_session,
)
from ..state_machine.engine import StateMachineEngine, TransitionContext
from ..state_machine.layers import HarnessLayer


@click.group("layer")
def layer_group() -> None:
    """Advance or inspect the governance session layer."""


@layer_group.command("advance")
@click.argument(
    "target_layer",
    type=click.Choice([layer.value for layer in HarnessLayer], case_sensitive=False),
)
@click.option("--session", "session_id", default=None, help="Session ID (defaults to active session).")
@click.option("--prototype", is_flag=True, default=False, help="Explicitly scoped as throwaway prototype.")
@click.option("--side-effects", is_flag=True, default=False, help="Work has persistence or external side effects.")
@click.option("--chat-only", is_flag=True, default=False, help="Decision captured only in chat.")
@click.option("--boundary-touch", is_flag=True, default=False, help="Work touches long-lived boundaries or public contracts.")
@click.option("--material-unknown", is_flag=True, default=False, help="A material unknown was discovered.")
@click.option("--uncontracted", is_flag=True, default=False, help="Implementation revealed uncontracted behavior.")
@click.option("--verification-failed", is_flag=True, default=False, help="Verification step failed.")
@click.option("--work-paused", is_flag=True, default=False, help="Work is finishing or pausing.")
@click.option("--contract-stalling", is_flag=True, default=False, help="Contract work repeating without progress.")
@click.pass_context
def layer_advance_cmd(
    ctx: click.Context,
    target_layer: str,
    session_id: str | None,
    prototype: bool,
    side_effects: bool,
    chat_only: bool,
    boundary_touch: bool,
    material_unknown: bool,
    uncontracted: bool,
    verification_failed: bool,
    work_paused: bool,
    contract_stalling: bool,
) -> None:
    """Advance the session to TARGET_LAYER (validated by the state machine engine)."""
    project_root: "Path" = ctx.obj["project_root"]
    to_layer = HarnessLayer(target_layer.lower().replace(" ", "-"))

    # Resolve session.
    if session_id:
        try:
            state = load_session(project_root, session_id)
        except FileNotFoundError:
            raise click.ClickException(bilingual("session.not_found", session_id=session_id))
    else:
        state = find_active_session(project_root)
        if state is None:
            raise click.ClickException(bilingual("layer.no_session"))

    if state.current_layer is None:
        # Should not happen for governed sessions, but guard anyway.
        raise click.ClickException(bilingual("layer.no_session"))

    from_layer = state.current_layer
    if from_layer == to_layer:
        click.echo(bilingual("layer.same_layer", layer=from_layer.value))
        return

    # Build transition context and evaluate.
    engine = StateMachineEngine()
    tc = TransitionContext(
        from_layer=from_layer,
        to_layer=to_layer,
        is_prototype_explicit=prototype,
        has_persistence_or_side_effect=side_effects,
        is_chat_only_decision=chat_only,
        touches_long_lived_boundary=boundary_touch,
        material_unknown_present=material_unknown,
        implementation_reveals_uncontracted_behavior=uncontracted,
        verification_failed=verification_failed,
        work_finished_or_paused=work_paused,
        contract_work_repeating=contract_stalling,
    )
    verdict = engine.evaluate(tc)

    # Record transition.
    context_flags = {
        "is_prototype_explicit": prototype,
        "has_persistence_or_side_effect": side_effects,
        "is_chat_only_decision": chat_only,
        "touches_long_lived_boundary": boundary_touch,
        "material_unknown_present": material_unknown,
        "implementation_reveals_uncontracted_behavior": uncontracted,
        "verification_failed": verification_failed,
        "work_finished_or_paused": work_paused,
        "contract_work_repeating": contract_stalling,
    }
    # Strip False values for cleaner records.
    active_flags = {k: v for k, v in context_flags.items() if v}

    record = TransitionRecord(
        from_layer=from_layer,
        to_layer=to_layer,
        timestamp=datetime.now(timezone.utc).isoformat(),
        context_flags=active_flags,
        engine_verdict=verdict.allowed,
        violations=tuple(v.format() for v in verdict.violations),
    )

    if not verdict.allowed:
        # Transition blocked — still record the attempt, do NOT update layer.
        state = state.model_copy(
            update={"transitions": state.transitions + (record,)},
        )
        save_session(project_root, state)

        if ctx.obj.get("json_output"):
            click.echo(json.dumps({
                "allowed": False,
                "from_layer": from_layer.value,
                "to_layer": to_layer.value,
                "violations": list(record.violations),
            }, indent=2, ensure_ascii=False))
        else:
            click.echo(bilingual(
                "layer.transition_blocked",
                from_layer=from_layer.value,
                to_layer=to_layer.value,
            ))
            for v in record.violations:
                click.echo(f"  {v}")
        raise SystemExit(1)

    # Allowed — advance the layer.
    state = state.model_copy(
        update={
            "current_layer": to_layer,
            "transitions": state.transitions + (record,),
        },
    )
    save_session(project_root, state)

    if ctx.obj.get("json_output"):
        click.echo(json.dumps({
            "allowed": True,
            "from_layer": from_layer.value,
            "to_layer": to_layer.value,
            "session_id": state.session_id,
        }, indent=2, ensure_ascii=False))
    else:
        click.echo(bilingual(
            "layer.advanced",
            from_layer=from_layer.value,
            to_layer=to_layer.value,
        ))


@layer_group.command("show")
@click.option("--session", "session_id", default=None, help="Session ID (defaults to active session).")
@click.pass_context
def layer_show_cmd(ctx: click.Context, session_id: str | None) -> None:
    """Show the current layer and transition history of a session."""
    project_root: "Path" = ctx.obj["project_root"]

    if session_id:
        try:
            state = load_session(project_root, session_id)
        except FileNotFoundError:
            raise click.ClickException(bilingual("session.not_found", session_id=session_id))
    else:
        state = find_active_session(project_root)
        if state is None:
            raise click.ClickException(bilingual("session.no_active"))

    if ctx.obj.get("json_output"):
        click.echo(json.dumps({
            "session_id": state.session_id,
            "current_layer": state.current_layer.value if state.current_layer else None,
            "transitions": [
                {
                    "from": t.from_layer.value,
                    "to": t.to_layer.value,
                    "timestamp": t.timestamp,
                    "allowed": t.engine_verdict,
                    "violations": list(t.violations),
                }
                for t in state.transitions
            ],
        }, indent=2, ensure_ascii=False))
        return

    click.echo(bilingual("session.header", session_id=state.session_id))
    layer_name = state.current_layer.value if state.current_layer else "-"
    click.echo(bilingual("session.current_layer", layer=layer_name))
    click.echo(bilingual("session.transitions_header", count=len(state.transitions)))
    for t in state.transitions:
        status = "OK" if t.engine_verdict else "BLOCKED"
        line = f"  {t.from_layer.value} -> {t.to_layer.value}  [{status}]  {t.timestamp}"
        if t.violations:
            line += f"  ({'; '.join(t.violations)})"
        click.echo(line)


__all__ = ["layer_group", "layer_advance_cmd", "layer_show_cmd"]
