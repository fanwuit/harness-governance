"""Shared formatting for failed layer gate checks."""

from __future__ import annotations

from ..messages import bilingual
from ..models.schemas import GateStatus


def _unique(items: tuple[str, ...]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def format_gate_failure_guidance(layer: str, status: GateStatus) -> list[str]:
    """Return human-readable guidance for a failed gate check."""
    lines: list[str] = [
        "",
        bilingual("gate.failure.details_header"),
    ]

    if status.questions_answered < status.questions_required:
        lines.append(
            "- "
            + bilingual(
                "gate.failure.questions_missing",
                answered=status.questions_answered,
                required=status.questions_required,
            )
        )
        if status.questions_agent_inferred:
            lines.append(
                bilingual(
                    "gate.check.answer_breakdown",
                    author=status.questions_author_answered,
                    required=status.questions_required,
                    inferred=status.questions_agent_inferred,
                )
            )

    blocking_artifacts_missing = _unique(status.blocking_artifacts_missing)
    if blocking_artifacts_missing:
        lines.append(
            "- "
            + bilingual(
                "gate.failure.blocking_artifacts_missing",
                missing=", ".join(blocking_artifacts_missing),
            )
        )

    artifacts_missing = _unique(status.artifacts_missing)
    if artifacts_missing:
        lines.append(
            "- "
            + bilingual(
                "gate.failure.artifacts_missing",
                missing=", ".join(artifacts_missing),
            )
        )

    confirmation_items_unmet = _unique(status.confirmation_items_unmet)
    if confirmation_items_unmet:
        lines.append("- " + bilingual("gate.failure.confirmations_unmet"))
        for item in confirmation_items_unmet:
            lines.append(f"  - {item}")

    lines.extend(
        [
            "",
            bilingual("gate.failure.red_flags_header"),
            "- " + bilingual("gate.failure.red_flag.small_change"),
            "- " + bilingual("gate.failure.red_flag.later"),
            "- " + bilingual("gate.failure.red_flag.existing"),
            "- " + bilingual("gate.failure.red_flag.skip"),
            "",
            bilingual("gate.failure.actions_header"),
            "1. " + bilingual("gate.failure.action.guide", layer=layer),
            "2. " + bilingual("gate.failure.action.complete"),
            "3. " + bilingual("gate.failure.action.rerun", layer=layer),
            "",
            "Choices:",
            "- yes: complete the required actions and rerun the gate.",
            "- no: stop and report the blocked layer.",
            "- back: revise an earlier layer answer or artifact, then rerun the gate.",
        ]
    )
    return lines


__all__ = ["format_gate_failure_guidance"]
