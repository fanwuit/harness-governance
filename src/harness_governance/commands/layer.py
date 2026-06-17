"""``harness layer`` commands — advance, guide, and inspect governance session layers.

The ``layer advance`` subcommand is the primary mechanism for *real state
advancement*: it loads the active session, evaluates the proposed
transition through :class:`~harness_governance.state_machine.engine.StateMachineEngine`,
and persists the result back to the session file.

The ``layer guide`` subcommand prints the author interaction guide for a
layer — a structured script telling the agent what to ask the human author,
how to present options, and what to confirm before advancing.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path

import click

from ..messages import bilingual
from ..session import (
    TransitionRecord,
    find_active_session,
    load_session,
    save_session,
)
from ..state_machine.engine import StateMachineEngine, TransitionContext
from ..state_machine.gates import (
    LayerGateEngine,
    LockFileManager,
    is_layer_required,
)
from ..state_machine.layers import HarnessLayer, LAYER_MAP
from ..state_machine.rigor import RigorTier

_GUIDE_PACKAGE = "harness_governance.data.references"
_GUIDE_FILE = "layer-author-guide.md"


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
@click.option("--confirmed", is_flag=True, default=False, help="Author has explicitly confirmed readiness to advance (recorded in audit trail).")
@click.option(
    "--skip-gate",
    "skip_gate",
    is_flag=True,
    default=False,
    help="Skip the gate check for the current layer (requires --confirmed).",
)
@click.option(
    "--rigor",
    "rigor_override",
    type=click.Choice(["light", "standard", "strict"]),
    default=None,
    help="Override the session's rigor tier for this advance.",
)
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
    confirmed: bool,
    skip_gate: bool,
    rigor_override: str | None,
) -> None:
    """Advance the session to TARGET_LAYER (validated by the state machine engine).

    Before advancing, the current layer's gate is checked.  The gate
    verifies that required questions have been answered and artifacts
    exist.  If the gate fails, the advance is blocked unless
    ``--skip-gate --confirmed`` is passed.

    Pass ``--confirmed`` to record that the author explicitly approved
    this transition.
    """
    project_root: "Path" = ctx.obj["project_root"]
    to_layer = HarnessLayer(target_layer.lower().replace(" ", "-"))

    # --skip-gate requires --confirmed (safety interlock).
    if skip_gate and not confirmed:
        raise click.UsageError(
            bilingual("layer.skip_gate_requires_confirmed")
        )

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

    # Apply rigor override if provided.
    if rigor_override:
        state = state.model_copy(update={"rigor_tier": rigor_override})

    from_layer = state.current_layer
    if from_layer == to_layer:
        click.echo(bilingual("layer.same_layer", layer=from_layer.value))
        return

    # v0.7.1: time the full advance (gate check + engine evaluate).
    _advance_start = time.perf_counter()

    # ------------------------------------------------------------------
    # Gate enforcement (Phase 5): check the *current* layer's gate before
    # allowing the advance to proceed.
    # ------------------------------------------------------------------
    tier = RigorTier(state.rigor_tier)
    if is_layer_required(from_layer, tier) and not skip_gate:
        gate_engine = LayerGateEngine()
        status = gate_engine.check(state, project_root, from_layer)

        if not status.passed:
            # Gate failed — block advance unless author explicitly skips.
            if ctx.obj.get("json_output"):
                click.echo(json.dumps({
                    "allowed": False,
                    "reason": "gate_failed",
                    "layer": from_layer.value,
                    "questions_answered": status.questions_answered,
                    "questions_required": status.questions_required,
                    "artifacts_missing": list(status.artifacts_missing),
                }, indent=2, ensure_ascii=False))
            else:
                click.echo(
                    bilingual(
                        "gate.check.failed",
                        layer=from_layer.value,
                        questions=status.questions_answered,
                        required=status.questions_required,
                        missing=", ".join(status.artifacts_missing) if status.artifacts_missing else "none",
                    ),
                    err=True,
                )
                click.echo(
                    bilingual("layer.gate_blocked"),
                    err=True,
                )
            raise SystemExit(1)

        # Gate passed — write lock for the current layer.
        locks = LockFileManager(project_root)
        locks.write_lock(from_layer, status, state)
        if ctx.obj.get("verbose", False):
            click.echo(
                bilingual(
                    "gate.check.passed",
                    layer=from_layer.value,
                    questions=status.questions_answered,
                    required=status.questions_required,
                ),
                err=True,
            )

    # Build transition context and evaluate.
    #
    # Propagate scope-drift signal from the gate hooks into the engine.
    # The drift gate hook (state_machine.drift._gate_hook_drift) reports
    # failures via confirmation_items_unmet with messages starting
    # "Scope drift".  When present, set scope_drift_detected so rule T10
    # can fire — previously this flag was never wired up, making T10
    # unreachable from the CLI.
    scope_drift_detected = False
    if not skip_gate and is_layer_required(from_layer, tier):
        for item in status.confirmation_items_unmet:
            if "Scope drift" in item or "Forbidden paths" in item:
                scope_drift_detected = True
                break

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
        scope_drift_detected=scope_drift_detected,
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

    if confirmed:
        active_flags["author_confirmed"] = True

    record = TransitionRecord(
        from_layer=from_layer,
        to_layer=to_layer,
        timestamp=datetime.now(timezone.utc).isoformat(),
        context_flags=active_flags,
        engine_verdict=verdict.allowed,
        violations=tuple(v.format() for v in verdict.violations),
        duration_seconds=round(time.perf_counter() - _advance_start, 3),
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


@layer_group.command("guide")
@click.argument("layer_name", required=False)
@click.option("--session", "session_id", default=None, help="Session ID (defaults to active session).")
@click.pass_context
def layer_guide_cmd(
    ctx: click.Context,
    layer_name: str | None,
    session_id: str | None,
) -> None:
    """Print the author interaction guide for a layer.

    Without arguments, prints the guide for the active session's current
    layer.  With a layer name, prints that layer's guide.
    """
    project_root: Path = ctx.obj["project_root"]

    # Resolve target layer.
    if layer_name:
        from ..state_machine.layers import resolve_layer
        try:
            target = resolve_layer(layer_name)
        except ValueError as exc:
            raise click.ClickException(str(exc))
    else:
        if session_id:
            try:
                state = load_session(project_root, session_id)
            except FileNotFoundError:
                raise click.ClickException(bilingual("session.not_found", session_id=session_id))
        else:
            state = find_active_session(project_root)
            if state is None:
                raise click.ClickException(bilingual("session.no_active"))
        target = state.current_layer
        if target is None:
            raise click.ClickException(bilingual("layer.no_session"))

    # Look up guide key from LAYER_MAP.
    guide_key = ""
    for entry in LAYER_MAP:
        if entry.layer is target:
            guide_key = entry.author_guide
            break

    # Load and extract the guide section.
    guide_text = _load_guide_file()
    section = _extract_guide_section(guide_text, guide_key) if guide_text else None

    if ctx.obj.get("json_output"):
        click.echo(json.dumps({
            "layer": target.value,
            "guide_key": guide_key,
            "guide": section or "",
            "found": section is not None,
        }, indent=2, ensure_ascii=False))
        return

    if section:
        click.echo(bilingual("layer.guide_header", layer=target.value))
        click.echo("")
        click.echo(section)
    else:
        click.echo(bilingual(
            "layer.guide_not_found",
            layer=target.value,
            output=_guide_fallback(target),
        ))


def _load_guide_file() -> str | None:
    """Read the bundled layer-author-guide.md; return None on failure."""
    try:
        resource = resources.files(_GUIDE_PACKAGE).joinpath(_GUIDE_FILE)
        if not resource.is_file():
            return None
        return resource.read_text(encoding="utf-8")
    except Exception:
        return None


def _extract_guide_section(guide_text: str, section_key: str) -> str | None:
    """Extract the section between ``## <section_key>`` and the next ``## `` heading."""
    target_heading = f"## {section_key}"
    lines = guide_text.splitlines()
    in_section = False
    result: list[str] = []
    for line in lines:
        if line.startswith("## ") and line.strip() == target_heading:
            in_section = True
            continue
        if in_section:
            if line.startswith("## "):
                break
            result.append(line)
    if not result:
        return None
    return "\n".join(result).strip()


def _guide_fallback(layer: HarnessLayer) -> str:
    """Return the required_output string when no guide section exists."""
    for entry in LAYER_MAP:
        if entry.layer is layer:
            return entry.required_output
    return ""


__all__ = [
    "layer_group",
    "layer_advance_cmd",
    "layer_show_cmd",
    "layer_guide_cmd",
    "_extract_guide_section",
]
