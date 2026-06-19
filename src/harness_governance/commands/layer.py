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
import re
import time
from datetime import datetime, timezone
from importlib import resources
from pathlib import Path

import click

from ..messages import bilingual
from ..session import (
    SessionState,
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
    layers_for_tier,
)
from ..state_machine.layers import HarnessLayer, LAYER_MAP, resolve_layer
from ..state_machine.rigor import RigorTier
from .gate_failure import format_gate_failure_guidance

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
@click.option(
    "--session",
    "session_id",
    default=None,
    help="Session ID (defaults to active session).",
)
@click.option(
    "--prototype",
    is_flag=True,
    default=False,
    help="Explicitly scoped as throwaway prototype.",
)
@click.option(
    "--side-effects",
    is_flag=True,
    default=False,
    help="Work has persistence or external side effects.",
)
@click.option(
    "--chat-only", is_flag=True, default=False, help="Decision captured only in chat."
)
@click.option(
    "--boundary-touch",
    is_flag=True,
    default=False,
    help="Work touches long-lived boundaries or public contracts.",
)
@click.option(
    "--material-unknown",
    is_flag=True,
    default=False,
    help="A material unknown was discovered.",
)
@click.option(
    "--uncontracted",
    is_flag=True,
    default=False,
    help="Implementation revealed uncontracted behavior.",
)
@click.option(
    "--verification-failed",
    is_flag=True,
    default=False,
    help="Verification step failed.",
)
@click.option(
    "--work-paused", is_flag=True, default=False, help="Work is finishing or pausing."
)
@click.option(
    "--contract-stalling",
    is_flag=True,
    default=False,
    help="Contract work repeating without progress.",
)
@click.option(
    "--confirmed",
    is_flag=True,
    default=False,
    help="Author has explicitly confirmed readiness to advance (recorded in audit trail).",
)
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
        raise click.UsageError(bilingual("layer.skip_gate_requires_confirmed"))

    # Resolve session.
    state: SessionState
    if session_id:
        try:
            state = load_session(project_root, session_id)
        except FileNotFoundError:
            raise click.ClickException(
                bilingual("session.not_found", session_id=session_id)
            )
    else:
        _state = find_active_session(project_root)
        if _state is None:
            raise click.ClickException(bilingual("layer.no_session"))
        state = _state

    if state.current_layer is None:
        # Should not happen for governed sessions, but guard anyway.
        raise click.ClickException(bilingual("layer.no_session"))

    # Apply rigor override if provided.
    if rigor_override:
        state = state.model_copy(update={"rigor_tier": rigor_override})

    from_layer = state.current_layer
    assert from_layer is not None  # guaranteed by the check above
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
                click.echo(
                    json.dumps(
                        {
                            "allowed": False,
                            "reason": "gate_failed",
                            "layer": from_layer.value,
                            "questions_answered": status.questions_answered,
                            "questions_required": status.questions_required,
                            "artifacts_missing": list(status.artifacts_missing),
                        },
                        indent=2,
                        ensure_ascii=False,
                    )
                )
            else:
                click.echo(
                    bilingual(
                        "gate.check.failed",
                        layer=from_layer.value,
                        questions=status.questions_answered,
                        required=status.questions_required,
                        missing=", ".join(status.artifacts_missing)
                        if status.artifacts_missing
                        else "none",
                    ),
                    err=True,
                )
                click.echo(
                    bilingual("layer.gate_blocked"),
                    err=True,
                )
                for line in format_gate_failure_guidance(from_layer.value, status):
                    click.echo(line, err=True)
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
    active_flags: dict[str, bool] = {k: bool(v) for k, v in context_flags.items() if v}

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
            click.echo(
                json.dumps(
                    {
                        "allowed": False,
                        "from_layer": from_layer.value,
                        "to_layer": to_layer.value,
                        "violations": list(record.violations),
                    },
                    indent=2,
                    ensure_ascii=False,
                )
            )
        else:
            click.echo(
                bilingual(
                    "layer.transition_blocked",
                    from_layer=from_layer.value,
                    to_layer=to_layer.value,
                )
            )
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
        click.echo(
            json.dumps(
                {
                    "allowed": True,
                    "from_layer": from_layer.value,
                    "to_layer": to_layer.value,
                    "session_id": state.session_id,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        click.echo(
            bilingual(
                "layer.advanced",
                from_layer=from_layer.value,
                to_layer=to_layer.value,
            )
        )


@layer_group.command("answer")
@click.argument("layer_name")
@click.option(
    "--question",
    required=True,
    help="Author question text or stable question identifier.",
)
@click.option(
    "--answer",
    required=True,
    help="Author's answer to record for this layer.",
)
@click.option(
    "--session",
    "session_id",
    default=None,
    help="Session ID (defaults to active session).",
)
@click.pass_context
def layer_answer_cmd(
    ctx: click.Context,
    layer_name: str,
    question: str,
    answer: str,
    session_id: str | None,
) -> None:
    """Record an author question answer in the active governance session."""
    project_root: Path = ctx.obj["project_root"]

    try:
        target = resolve_layer(layer_name)
    except ValueError as exc:
        raise click.ClickException(str(exc))

    state = _resolve_session(project_root, session_id)
    state = _append_layer_answer(state, target, question, answer)
    save_session(project_root, state)

    answered = sum(1 for qa in state.layer_qa if qa.get("layer") == target.value)
    if ctx.obj.get("json_output"):
        click.echo(
            json.dumps(
                {
                    "session_id": state.session_id,
                    "layer": target.value,
                    "questions_answered": answered,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    click.echo(
        bilingual(
            "layer.answer_recorded",
            layer=target.value,
            count=answered,
        )
    )


@layer_group.command("ask")
@click.argument("layer_name", required=False)
@click.option(
    "--session",
    "session_id",
    default=None,
    help="Session ID (defaults to active session).",
)
@click.pass_context
def layer_ask_cmd(
    ctx: click.Context,
    layer_name: str | None,
    session_id: str | None,
) -> None:
    """Ask and record the author questions for a layer."""
    project_root: Path = ctx.obj["project_root"]
    state = _resolve_session(project_root, session_id)

    if layer_name:
        try:
            target = resolve_layer(layer_name)
        except ValueError as exc:
            raise click.ClickException(str(exc))
    else:
        current = state.current_layer
        if current is None:
            raise click.ClickException(bilingual("layer.no_session"))
        target = current

    section = _guide_section_for_layer(target)
    questions = _extract_author_questions(section or "")
    if not questions:
        raise click.ClickException(
            bilingual("layer.ask.no_questions", layer=target.value)
        )

    already_answered = {
        str(qa.get("question", ""))
        for qa in state.layer_qa
        if qa.get("layer") == target.value
    }
    if ctx.obj.get("json_output"):
        status = LayerGateEngine().check(state, project_root, target)
        next_layer = _next_layer_for_state(state, target)
        answered = sum(1 for qa in state.layer_qa if qa.get("layer") == target.value)
        click.echo(
            json.dumps(
                {
                    "session_id": state.session_id,
                    "layer": target.value,
                    "questions_recorded": 0,
                    "questions_answered": answered,
                    "gate_passed": status.passed,
                    "questions_required": status.questions_required,
                    "next_layer": next_layer.value if next_layer else None,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    recorded = 0
    for question in questions:
        if question in already_answered:
            continue
        answer = _prompt_author_answer(question, target)
        state = _append_layer_answer(state, target, question, answer)
        recorded += 1

    save_session(project_root, state)
    answered = sum(1 for qa in state.layer_qa if qa.get("layer") == target.value)
    status = LayerGateEngine().check(state, project_root, target)

    if ctx.obj.get("json_output"):
        click.echo(
            json.dumps(
                {
                    "session_id": state.session_id,
                    "layer": target.value,
                    "questions_recorded": recorded,
                    "questions_answered": answered,
                    "gate_passed": status.passed,
                    "questions_required": status.questions_required,
                    "artifacts_missing": list(status.artifacts_missing),
                    "blocking_artifacts_missing": list(
                        status.blocking_artifacts_missing
                    ),
                    "confirmation_items_unmet": list(status.confirmation_items_unmet),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    click.echo(
        bilingual(
            "layer.ask.recorded",
            layer=target.value,
            count=recorded,
            answered=answered,
        )
    )
    gate_state = "PASSED" if status.passed else "FAILED"
    click.echo(
        bilingual(
            "alias.next.gate",
            state=gate_state,
            questions=status.questions_answered,
            required=status.questions_required,
        )
    )
    if status.confirmation_items_unmet:
        click.echo(bilingual("gate.failure.confirmations_unmet"))
        for item in status.confirmation_items_unmet:
            click.echo(f"  - {item}")


@layer_group.command("wizard")
@click.argument("layer_name", required=False)
@click.option(
    "--session",
    "session_id",
    default=None,
    help="Session ID (defaults to active session).",
)
@click.pass_context
def layer_wizard_cmd(
    ctx: click.Context,
    layer_name: str | None,
    session_id: str | None,
) -> None:
    """Run the guided ask/check/advance flow for one governance layer."""
    project_root: Path = ctx.obj["project_root"]
    state = _resolve_session(project_root, session_id)
    target = _resolve_layer_or_current(state, layer_name)
    section = _guide_section_for_layer(target)
    questions = _extract_author_questions(section or "")
    if not questions:
        raise click.ClickException(
            bilingual("layer.ask.no_questions", layer=target.value)
        )

    already_answered = {
        str(qa.get("question", ""))
        for qa in state.layer_qa
        if qa.get("layer") == target.value
    }
    if ctx.obj.get("json_output"):
        status = LayerGateEngine().check(state, project_root, target)
        next_layer = _next_layer_for_state(state, target)
        answered = sum(1 for qa in state.layer_qa if qa.get("layer") == target.value)
        click.echo(
            json.dumps(
                {
                    "session_id": state.session_id,
                    "layer": target.value,
                    "questions_recorded": 0,
                    "questions_answered": answered,
                    "gate_passed": status.passed,
                    "questions_required": status.questions_required,
                    "next_layer": next_layer.value if next_layer else None,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    recorded = 0
    for question in questions:
        if question in already_answered:
            continue
        answer = _prompt_author_answer(question, target)
        state = _append_layer_answer(state, target, question, answer)
        already_answered.add(question)
        recorded += 1

    save_session(project_root, state)
    answered = sum(1 for qa in state.layer_qa if qa.get("layer") == target.value)
    status = LayerGateEngine().check(state, project_root, target)
    next_layer = _next_layer_for_state(state, target)

    payload = {
        "session_id": state.session_id,
        "layer": target.value,
        "questions_recorded": recorded,
        "questions_answered": answered,
        "gate_passed": status.passed,
        "questions_required": status.questions_required,
        "next_layer": next_layer.value if next_layer else None,
    }
    if ctx.obj.get("json_output"):
        click.echo(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    click.echo(
        bilingual(
            "layer.ask.recorded",
            layer=target.value,
            count=recorded,
            answered=answered,
        )
    )
    gate_state = "PASSED" if status.passed else "FAILED"
    click.echo(
        bilingual(
            "alias.next.gate",
            state=gate_state,
            questions=status.questions_answered,
            required=status.questions_required,
        )
    )
    if not status.passed:
        for line in format_gate_failure_guidance(target.value, status):
            click.echo(line)
        return
    if next_layer is None:
        click.echo(bilingual("layer.wizard.no_next"))
        return

    choice = _select_choice(
        bilingual("layer.wizard.advance_prompt", layer=next_layer.value),
        (
            ("yes", bilingual("layer.wizard.choice.yes")),
            ("no", bilingual("layer.wizard.choice.no")),
            ("back", bilingual("layer.wizard.choice.back")),
        ),
    )
    if choice == "yes":
        ctx.invoke(
            layer_advance_cmd,
            target_layer=next_layer.value,
            session_id=state.session_id,
            prototype=False,
            side_effects=False,
            chat_only=False,
            boundary_touch=False,
            material_unknown=False,
            uncontracted=False,
            verification_failed=False,
            work_paused=False,
            contract_stalling=False,
            confirmed=True,
            skip_gate=False,
            rigor_override=None,
        )
    elif choice == "back":
        click.echo(bilingual("layer.wizard.back"))
    else:
        click.echo(
            bilingual(
                "governed_start.next",
                cmd=f"harness layer advance {next_layer.value} --confirmed",
            )
        )


@layer_group.command("intake")
@click.option(
    "--session",
    "session_id",
    default=None,
    help="Session ID (defaults to active session).",
)
@click.pass_context
def layer_intake_cmd(ctx: click.Context, session_id: str | None) -> None:
    """Ask and record intake-orientation author questions."""
    ctx.invoke(
        layer_ask_cmd,
        layer_name=HarnessLayer.INTAKE_ORIENTATION.value,
        session_id=session_id,
    )


@layer_group.command("show")
@click.option(
    "--session",
    "session_id",
    default=None,
    help="Session ID (defaults to active session).",
)
@click.pass_context
def layer_show_cmd(ctx: click.Context, session_id: str | None) -> None:
    """Show the current layer and transition history of a session."""
    project_root: "Path" = ctx.obj["project_root"]

    state: SessionState
    if session_id:
        try:
            state = load_session(project_root, session_id)
        except FileNotFoundError:
            raise click.ClickException(
                bilingual("session.not_found", session_id=session_id)
            )
    else:
        _state = find_active_session(project_root)
        if _state is None:
            raise click.ClickException(bilingual("session.no_active"))
        state = _state

    if ctx.obj.get("json_output"):
        click.echo(
            json.dumps(
                {
                    "session_id": state.session_id,
                    "current_layer": state.current_layer.value
                    if state.current_layer
                    else None,
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
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    click.echo(bilingual("session.header", session_id=state.session_id))
    layer_name = state.current_layer.value if state.current_layer else "-"
    click.echo(bilingual("session.current_layer", layer=layer_name))
    click.echo(bilingual("session.transitions_header", count=len(state.transitions)))
    for t in state.transitions:
        status = "OK" if t.engine_verdict else "BLOCKED"
        line = (
            f"  {t.from_layer.value} -> {t.to_layer.value}  [{status}]  {t.timestamp}"
        )
        if t.violations:
            line += f"  ({'; '.join(t.violations)})"
        click.echo(line)


@layer_group.command("guide")
@click.argument("layer_name", required=False)
@click.option(
    "--session",
    "session_id",
    default=None,
    help="Session ID (defaults to active session).",
)
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
    target: HarnessLayer | None
    if layer_name:
        try:
            target = resolve_layer(layer_name)
        except ValueError as exc:
            raise click.ClickException(str(exc))
    else:
        _state2: SessionState
        if session_id:
            try:
                _state2 = load_session(project_root, session_id)
            except FileNotFoundError:
                raise click.ClickException(
                    bilingual("session.not_found", session_id=session_id)
                )
        else:
            _found = find_active_session(project_root)
            if _found is None:
                raise click.ClickException(bilingual("session.no_active"))
            _state2 = _found
        target = _state2.current_layer
        if target is None:
            raise click.ClickException(bilingual("layer.no_session"))

    guide_key, section = _guide_key_and_section_for_layer(target)

    if ctx.obj.get("json_output"):
        click.echo(
            json.dumps(
                {
                    "layer": target.value,
                    "guide_key": guide_key,
                    "guide": section or "",
                    "found": section is not None,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    if section:
        click.echo(bilingual("layer.guide_header", layer=target.value))
        click.echo("")
        click.echo(section)
    else:
        click.echo(
            bilingual(
                "layer.guide_not_found",
                layer=target.value,
                output=_guide_fallback(target),
            )
        )


def _load_guide_file() -> str | None:
    """Read the bundled layer-author-guide.md; return None on failure."""
    try:
        resource = resources.files(_GUIDE_PACKAGE).joinpath(_GUIDE_FILE)
        if not resource.is_file():
            return None
        return resource.read_text(encoding="utf-8")
    except Exception:
        return None


def _resolve_session(project_root: Path, session_id: str | None) -> SessionState:
    if session_id:
        try:
            return load_session(project_root, session_id)
        except FileNotFoundError:
            raise click.ClickException(
                bilingual("session.not_found", session_id=session_id)
            )

    found = find_active_session(project_root)
    if found is None:
        raise click.ClickException(bilingual("session.no_active"))
    return found


def _resolve_layer_or_current(
    state: SessionState, layer_name: str | None
) -> HarnessLayer:
    if layer_name:
        try:
            return resolve_layer(layer_name)
        except ValueError as exc:
            raise click.ClickException(str(exc))
    current = state.current_layer
    if current is None:
        raise click.ClickException(bilingual("layer.no_session"))
    return current


def _append_layer_answer(
    state: SessionState,
    target: HarnessLayer,
    question: str,
    answer: str,
) -> SessionState:
    existing = tuple(
        qa
        for qa in state.layer_qa
        if not (qa.get("layer") == target.value and qa.get("question") == question)
    )
    entry = {
        "layer": target.value,
        "question": question,
        "answer": answer,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return state.model_copy(update={"layer_qa": existing + (entry,)})


def _next_layer_for_state(
    state: SessionState, current: HarnessLayer
) -> HarnessLayer | None:
    path = layers_for_tier(RigorTier(state.rigor_tier))
    try:
        idx = path.index(current)
    except ValueError:
        return None
    if idx + 1 >= len(path):
        return None
    return path[idx + 1]


def _prompt_author_answer(question: str, target: HarnessLayer) -> str:
    stdin = click.get_text_stream("stdin")
    if stdin.isatty():
        try:
            return str(click.prompt(question, type=str))
        except click.Abort:
            raise click.ClickException(
                bilingual("layer.ask.aborted", layer=target.value)
            )

    click.echo(f"{question}: ", nl=False)
    answer = stdin.readline()
    if answer == "":
        raise click.ClickException(
            bilingual("layer.ask.aborted", layer=target.value)
        )
    click.echo(answer.rstrip("\n"))
    return answer.rstrip("\n")


def _select_choice(prompt: str, choices: tuple[tuple[str, str], ...]) -> str:
    """Return a choice key using arrow keys on a TTY or numbers otherwise."""
    click.echo(prompt)
    for idx, (_key, label) in enumerate(choices, 1):
        click.echo(f"  {idx}. {label}")

    if (
        click.get_text_stream("stdin").isatty()
        and click.get_text_stream("stdout").isatty()
    ):
        click.echo(bilingual("layer.selector.hint"))
        index = 0
        while True:
            char = click.getchar()
            if char in ("\r", "\n"):
                return choices[index][0]
            if char in ("1", "2", "3") and int(char) <= len(choices):
                return choices[int(char) - 1][0]
            if char in ("\x1b[B", "\t", "j"):
                index = (index + 1) % len(choices)
                click.echo(f"> {choices[index][1]}")
            elif char in ("\x1b[A", "k"):
                index = (index - 1) % len(choices)
                click.echo(f"> {choices[index][1]}")

    stdin = click.get_text_stream("stdin")
    click.echo("> ", nl=False)
    raw_text = stdin.readline()
    if raw_text == "":
        return "no"
    click.echo(raw_text.rstrip("\n"))
    try:
        raw = int(raw_text.strip())
    except ValueError:
        return "no"
    if raw < 1 or raw > len(choices):
        return "no"
    return choices[raw - 1][0]


def _guide_key_and_section_for_layer(target: HarnessLayer) -> tuple[str, str | None]:
    guide_key = ""
    for entry in LAYER_MAP:
        if entry.layer is target:
            guide_key = entry.author_guide
            break

    guide_text = _load_guide_file()
    section = _extract_guide_section(guide_text, guide_key) if guide_text else None
    return guide_key, section


def _guide_section_for_layer(target: HarnessLayer) -> str | None:
    return _guide_key_and_section_for_layer(target)[1]


def _extract_author_questions(section: str) -> list[str]:
    """Extract numbered author questions from a guide section."""
    lines = section.splitlines()
    in_questions = False
    questions: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("### "):
            if in_questions:
                break
            in_questions = "Author Questions" in stripped or "作者问题" in stripped
            continue
        if not in_questions:
            continue
        match = re.match(r"^\d+\.\s+(.*\S)\s*$", stripped)
        if match:
            questions.append(match.group(1))
    return questions


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
    "layer_answer_cmd",
    "layer_ask_cmd",
    "layer_wizard_cmd",
    "layer_intake_cmd",
    "layer_show_cmd",
    "layer_guide_cmd",
    "_extract_author_questions",
    "_extract_guide_section",
]
