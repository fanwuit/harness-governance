"""The 12 harness layers.

The canonical source of truth for layer ordering is
``harness-engineering/references/layer-progression.md``. This module
encodes that ordering as a :class:`HarnessLayer` enum and a
:class:`LayerMap` data structure that pairs each layer with its
primary local governance skill and required exit artifact.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class HarnessLayer(str, Enum):
    """The 12 canonical harness layers.

    String values match the queue-label spellings mandated by
    ``layer-progression.md`` § Queue Layer Labels so they can be used
    verbatim in ``NEXT.md``, dashboards, and handoffs.
    """

    INTAKE_ORIENTATION = "intake-orientation"
    IDEA = "idea"
    FACT_DISCOVERY = "fact-discovery"
    BRAINSTORMING = "brainstorming"
    BRIEF = "brief"
    ARCHITECTURE = "architecture"
    ADR = "adr"
    CONTRACT = "contract"
    READINESS = "readiness"
    IMPLEMENTATION = "implementation"
    VERIFICATION = "verification"
    REVIEW_NEXT = "review-next"


@dataclass(frozen=True, slots=True)
class LayerEntry:
    """One row of the harness layer map.

    Attributes
    ----------
    layer:
        The layer label.
    primary_skill:
        The local governance skill that owns this layer's output.
    supporting_skills:
        Local governance skills that may contribute techniques, in
        preference order.
    required_output:
        Human-readable description of the durable artifact required
        before moving to the next layer.
    """

    layer: HarnessLayer
    primary_skill: str
    supporting_skills: tuple[str, ...]
    required_output: str
    author_guide: str = ""


# Authoritative layer map. Order matters: ``LAYER_MAP`` is iterated to
# produce canonical progression chains, so reordering it changes the
# state machine.
LAYER_MAP: tuple[LayerEntry, ...] = (
    LayerEntry(
        layer=HarnessLayer.INTAKE_ORIENTATION,
        primary_skill="harness-engineering",
        supporting_skills=("codebase-orientation", "find-docs", "planning-with-files"),
        required_output=(
            "Current repo/task context, existing queue or planning source, "
            "and known constraints."
        ),
        author_guide="intake-orientation",
    ),
    LayerEntry(
        layer=HarnessLayer.IDEA,
        primary_skill="harness-engineering",
        supporting_skills=("observable-fact-discovery",),
        required_output="A stable statement of the user intent or problem.",
        author_guide="idea",
    ),
    LayerEntry(
        layer=HarnessLayer.FACT_DISCOVERY,
        primary_skill="observable-fact-discovery",
        supporting_skills=("find-docs", "codebase-orientation"),
        required_output=(
            "Reviewable facts, samples, probes, logs, fixtures, docs "
            "citations, or explicit unknowns."
        ),
        author_guide="fact-discovery",
    ),
    LayerEntry(
        layer=HarnessLayer.BRAINSTORMING,
        primary_skill="brainstorm-to-brief",
        supporting_skills=("observable-fact-discovery",),
        required_output="Options, tradeoffs, risks, assumptions, and non-goals.",
        author_guide="brainstorming",
    ),
    LayerEntry(
        layer=HarnessLayer.BRIEF,
        primary_skill="brainstorm-to-brief",
        supporting_skills=("document-gardener",),
        required_output=(
            "Goal, context, non-goals, success criteria, risks, and next layer."
        ),
        author_guide="brief",
    ),
    LayerEntry(
        layer=HarnessLayer.ARCHITECTURE,
        primary_skill="architecture-boundary-design",
        supporting_skills=("implementation-detail-timing", "observable-fact-discovery"),
        required_output=(
            "Boundaries, responsibilities, ownership, data flow, and ADR candidates."
        ),
        author_guide="architecture",
    ),
    LayerEntry(
        layer=HarnessLayer.ADR,
        primary_skill="adr-writing",
        supporting_skills=("architecture-boundary-design", "document-gardener"),
        required_output=(
            "Decision, rationale, alternatives, consequences, and validation approach."
        ),
        author_guide="adr",
    ),
    LayerEntry(
        layer=HarnessLayer.CONTRACT,
        primary_skill="contract-first-development",
        supporting_skills=(
            "contract-growth-control",
            "observable-fact-discovery",
            "find-docs",
        ),
        required_output=(
            "Executable or reviewable contracts: schema, fixture, example, "
            "probe, API shape, check, or acceptance test."
        ),
        author_guide="contract",
    ),
    LayerEntry(
        layer=HarnessLayer.READINESS,
        primary_skill="implementation-readiness-gate",
        supporting_skills=(
            "implementation-detail-timing",
            "contract-growth-control",
            "governed-implementation-entry",
        ),
        required_output=(
            "Target-local boundaries, contracts, verification commands, "
            "AGENTS.md rules, baseline checks, and the Implementation "
            "Entry Record are known."
        ),
        author_guide="readiness",
    ),
    LayerEntry(
        layer=HarnessLayer.IMPLEMENTATION,
        primary_skill="governed-implementation-entry",
        supporting_skills=(
            "implementation-readiness-gate",
            "code-quality-drift-guard",
            "agent-mistake-guard",
        ),
        required_output=(
            "Implementation Entry Record exists as the mechanical "
            "credential for code/config changes that stay inside "
            "approved boundaries and satisfy existing contracts."
        ),
        author_guide="implementation",
    ),
    LayerEntry(
        layer=HarnessLayer.VERIFICATION,
        primary_skill="review-next-governance",
        supporting_skills=("code-quality-drift-guard", "harness-status-dashboard"),
        required_output=(
            "Fresh evidence from tests, checks, probes, screenshots, "
            "traces, or explicit failure records."
        ),
        author_guide="verification",
    ),
    LayerEntry(
        layer=HarnessLayer.REVIEW_NEXT,
        primary_skill="review-next-governance",
        supporting_skills=(
            "document-gardener",
            "harness-status-dashboard",
            "autonomous-ready-loop",
        ),
        required_output=(
            "Done archive, scheduler ready queue, blocked items, not-now "
            "items, risks, and evidence are written to stable state."
        ),
        author_guide="review-next",
    ),
)

LAYER_BY_NAME: dict[str, HarnessLayer] = {layer.value: layer for layer in HarnessLayer}


def resolve_layer(name: str) -> HarnessLayer:
    """Return the layer matching ``name`` (case-insensitive).

    Accepts the canonical queue spelling (``intake-orientation``) as
    well as the readable form used in prose (``Intake / Orientation``).
    """
    # Strip surrounding whitespace, normalize separators. The order of
    # substitutions matters: collapse "/ " or " /" before the bulk
    # replace so we don't end up with a double dash.
    key = name.strip().lower()
    key = key.replace(" / ", "-").replace("/ ", "-").replace(" /", "-")
    key = key.replace(" ", "-")
    if key in LAYER_BY_NAME:
        return LAYER_BY_NAME[key]
    # Try synonyms used in layer-progression.md prose.
    synonyms = {
        "intake": HarnessLayer.INTAKE_ORIENTATION,
    }
    if key in synonyms:
        return synonyms[key]
    raise ValueError(f"Unknown harness layer: {name!r}")


def canonical_progression() -> tuple[HarnessLayer, ...]:
    """Return the canonical 12-layer progression in order."""
    return tuple(entry.layer for entry in LAYER_MAP)


def layer_index(layer: HarnessLayer) -> int:
    """Return the zero-based index of ``layer`` in the canonical progression."""
    return canonical_progression().index(layer)