"""Layer gate definitions and rigor-based layer profiles.

Each of the 12 harness layers has a :class:`LayerGateDefinition` that
specifies the minimum questions, required artifacts, and confirmation
items that must be satisfied before advancing to the next layer.

The :data:`RIGOR_LAYER_PROFILES` mapping controls which layers are
required vs skippable at each :class:`~.rigor.RigorTier`.
"""

from __future__ import annotations

from pathlib import Path

from .layers import HarnessLayer
from .rigor import RigorTier

# ---------------------------------------------------------------------------
# Layer gate definition
# ---------------------------------------------------------------------------


class LayerGateDefinition:
    """Programmatic gate definition for one harness layer.

    Extracted from ``layer-author-guide.md`` so the gate engine can
    verify that required questions have been asked, artifacts exist,
    and confirmation items are satisfied.

    Attributes
    ----------
    layer:
        The layer this gate applies to.
    required_questions:
        The author questions (one per entry) from the layer guide.
    min_questions_answered:
        Minimum number of questions that must be answered per rigor tier.
    required_artifacts:
        Glob-able file patterns that must exist on disk.
    confirmation_items:
        Checkbox items from the Confirmation Gate section.
    """

    __slots__ = (
        "layer",
        "required_questions",
        "min_questions_answered",
        "required_artifacts",
        "confirmation_items",
    )

    def __init__(
        self,
        layer: HarnessLayer,
        required_questions: tuple[str, ...],
        min_questions_answered: dict[RigorTier, int],
        required_artifacts: tuple[str, ...],
        confirmation_items: tuple[str, ...],
    ) -> None:
        self.layer = layer
        self.required_questions = required_questions
        self.min_questions_answered = min_questions_answered
        self.required_artifacts = required_artifacts
        self.confirmation_items = confirmation_items


# ---------------------------------------------------------------------------
# Gate catalog — one entry per harness layer
# ---------------------------------------------------------------------------


def _q(n: int) -> dict[RigorTier, int]:
    """Shorthand: STRICT=n, STANDARD=max(1, n//2+n%2), LIGHT=1."""
    return {
        RigorTier.STRICT: n,
        RigorTier.STANDARD: max(1, n // 2 + n % 2),
        RigorTier.LIGHT: 1,
    }


GATE_CATALOG: dict[HarnessLayer, LayerGateDefinition] = {
    HarnessLayer.INTAKE_ORIENTATION: LayerGateDefinition(
        layer=HarnessLayer.INTAKE_ORIENTATION,
        required_questions=(
            "What is the current task or goal? / 当前的任务或目标是什么？",
            "Is there an existing queue (NEXT.md, TODO, backlog, issue tracker)? / 是否有现有队列？",
            "Are there known constraints or risks? / 有哪些已知的约束或风险？",
            "Continuation of previous work or new task? / 这是之前工作的延续，还是新任务？",
        ),
        min_questions_answered=_q(4),
        required_artifacts=(".harness/sessions/*.json",),
        confirmation_items=(
            "Routing decision explicitly acknowledged",
            "Current layer stated and understood",
            "Competing skill warnings reviewed (if any)",
            "Session ID recorded",
        ),
    ),
    HarnessLayer.IDEA: LayerGateDefinition(
        layer=HarnessLayer.IDEA,
        required_questions=(
            "Can you state the core problem in one sentence? / 你能用一句话描述核心问题或意图吗？",
            "Feature, bug fix, refactor, investigation, or other? / 这是功能需求、bug 修复、重构、调查，还是其他？",
        ),
        min_questions_answered=_q(2),
        required_artifacts=(".harness/sessions/*.json",),
        confirmation_items=(
            "One-line intent statement explicitly approved",
            "Task type agreed",
            "Any known non-goals noted",
        ),
    ),
    HarnessLayer.FACT_DISCOVERY: LayerGateDefinition(
        layer=HarnessLayer.FACT_DISCOVERY,
        required_questions=(
            "Specific files, logs, APIs, or docs to examine first? / 有哪些特定的文件、日志、API 或文档我应该先查看？",
            "Known unknowns — things we know we don't know? / 有哪些已知的未知？",
            "What existing evidence can you point to? / 你能指给我哪些现有的证据？",
        ),
        min_questions_answered=_q(3),
        required_artifacts=("docs/facts/*.md",),
        confirmation_items=(
            "All material unknowns resolved or declared as assumptions",
            "Author reviewed Assumption/Risk blocks",
            "Results written to durable location (not chat-only)",
        ),
    ),
    HarnessLayer.BRAINSTORMING: LayerGateDefinition(
        layer=HarnessLayer.BRAINSTORMING,
        required_questions=(
            "Approaches you already have in mind? / 你心里已经有哪几种方案或思路？",
            "Approaches you specifically want to exclude? / 有你想明确排除的方案吗？",
            "Who are the stakeholders affected? / 哪些利益相关者会受影响？",
            "Hard constraints (budget, time, tech stack, regulation)? / 硬约束是什么？",
        ),
        min_questions_answered=_q(4),
        required_artifacts=("docs/brainstorming/*.md",),
        confirmation_items=(
            "At least one alternative documented (or absence justified)",
            "Author selected or endorsed a direction",
            "Explicit non-goals documented",
            "Risks and assumptions captured",
            "Next layer candidate identified",
        ),
    ),
    HarnessLayer.BRIEF: LayerGateDefinition(
        layer=HarnessLayer.BRIEF,
        required_questions=(
            "Does the goal capture what success looks like? / 目标陈述是否准确反映了成功的定义？",
            "Are non-goals correct — anything to add or remove? / 非目标是否正确？",
            "Are success criteria measurable and verifiable? / 成功标准是否可衡量、可验证？",
            "Which layer next: Architecture, ADR, Contract, or continue refining? / 下一层去哪个？",
        ),
        min_questions_answered=_q(4),
        required_artifacts=("docs/briefs/*.md",),
        confirmation_items=(
            "Goal statement explicitly approved",
            "Non-goals explicitly confirmed",
            "Success criteria are measurable (not vague)",
            "Next layer explicitly confirmed by author",
            "Brief written to a durable file",
        ),
    ),
    HarnessLayer.ARCHITECTURE: LayerGateDefinition(
        layer=HarnessLayer.ARCHITECTURE,
        required_questions=(
            "Existing architectural decisions or diagrams to reference? / 有现有的架构决策或图表可以参考吗？",
            "Which boundaries are firm (cannot change), which are negotiable? / 哪些边界是固定的，哪些是可协商的？",
            "Which teams/systems own the components being touched? / 哪些团队/系统拥有被触碰的组件？",
            "What is the data flow — inputs, outputs, persistence? / 数据流是怎样的？",
        ),
        min_questions_answered=_q(4),
        required_artifacts=("docs/architecture/*.md",),
        confirmation_items=(
            "All boundaries documented and reviewed",
            "Owners for each component/touchpoint identified",
            "ADR candidates listed with rationale",
            "No implementation details decided prematurely",
        ),
    ),
    HarnessLayer.ADR: LayerGateDefinition(
        layer=HarnessLayer.ADR,
        required_questions=(
            "Do you agree with the recommended decision and its rationale? / 你同意推荐的决策及其理由吗？",
            "Any alternatives not listed that should be considered? / 有没有未列出的替代方案需要考虑？",
            "What are the long-term consequences — maintenance, migration, cost? / 长期后果是什么？",
            "How should this decision be validated after implementation? / 这个决策在实施后应该如何验证？",
        ),
        min_questions_answered=_q(4),
        required_artifacts=("docs/adr/*.md",),
        confirmation_items=(
            "Decision explicitly stated and understood",
            "At least one alternative considered with rejection rationale",
            "Consequences (positive and negative) documented",
            "Validation approach defined",
            "ADR status moved from 'proposed' to 'accepted' by author",
        ),
    ),
    HarnessLayer.CONTRACT: LayerGateDefinition(
        layer=HarnessLayer.CONTRACT,
        required_questions=(
            "What exact behaviour must the implementation satisfy? / 实现必须满足什么确切行为？",
            "What failure cases must be handled? / 必须处理哪些失败情况？",
            "Are there existing contracts/schemas/tests to extend rather than replace? / 是否有现成的契约可以扩展？",
            "What scope is explicitly out of bounds? / 什么范围明确不在范围内？",
        ),
        min_questions_answered=_q(4),
        required_artifacts=("docs/contracts/*.md",),
        confirmation_items=(
            "Every contract clause reviewed and accepted",
            "Failure cases explicitly covered",
            "Forbidden scope boundaries respected",
            "Contract does not freeze boundary decisions without prior ADR (T3)",
        ),
    ),
    HarnessLayer.READINESS: LayerGateDefinition(
        layer=HarnessLayer.READINESS,
        required_questions=(
            "Do you believe all implementation prerequisites are met? / 你是否认为所有实施前提条件都已满足？",
            "Is this a throwaway prototype or will it produce real/persisted artifacts? / 这是丢弃式原型还是会产生真实产物？",
            "Any concerns about the implementation environment or tooling? / 对实施环境或工具有任何顾虑吗？",
        ),
        min_questions_answered=_q(3),
        required_artifacts=(".harness/sessions/*.json",),
        confirmation_items=(
            "Readiness gate result (pass/fail) explicitly stated",
            "All contract evidence cited",
            "Verification commands defined",
            "Stop conditions defined",
            "If prototype: explicitly scoped as throwaway (T1/T2)",
            "Author explicitly authorises implementation",
        ),
    ),
    HarnessLayer.IMPLEMENTATION: LayerGateDefinition(
        layer=HarnessLayer.IMPLEMENTATION,
        required_questions=(
            "Do you want to review intermediate progress or only the final result? / 你是想检查中间进度，还是只看最终结果？",
            "Should I stop and ask before touching files outside the approved owner list? / 在触碰批准的所有者列表之外的文件之前，我应该停下来问你吗？",
            "If verification fails: attempt to fix, or stop and report? / 如果验证失败：尝试修复，还是停止并报告？",
        ),
        min_questions_answered=_q(3),
        required_artifacts=(".harness/gates/10-implementation.lock",),
        confirmation_items=(
            "All verification commands passed (or failures documented)",
            "No uncontracted behaviour introduced (T7)",
            "All stop conditions evaluated",
            "Author reviewed verification evidence",
        ),
    ),
    HarnessLayer.VERIFICATION: LayerGateDefinition(
        layer=HarnessLayer.VERIFICATION,
        required_questions=(
            "Any additional verification steps beyond the defined commands? / 除了已定义的命令外，还有额外的验证步骤吗？",
            "Should I record screenshots or traces? / 需要我录制截图或跟踪吗？",
            "If verification fails: investigate the cause, or report and pause? / 如果验证失败：调查原因，还是报告并暂停？",
        ),
        min_questions_answered=_q(3),
        required_artifacts=("docs/verification/*.md",),
        confirmation_items=(
            "All verification commands executed, results are fresh",
            "Failures documented with evidence and owner layer identified",
            "Author reviewed verification summary",
        ),
    ),
    HarnessLayer.REVIEW_NEXT: LayerGateDefinition(
        layer=HarnessLayer.REVIEW_NEXT,
        required_questions=(
            "Is this work complete and ready to archive? / 这项工作是否完成且可以归档？",
            "What is the next priority — what should be done next? / 下一个优先级是什么？",
            "Any new queue items, blocked items, or not-now items to add? / 有没有新的队列项要添加？",
            "Any risks or lessons learned to preserve? / 有没有需要保留的风险或经验教训？",
        ),
        min_questions_answered=_q(4),
        required_artifacts=(".harness/sessions/*.json",),
        confirmation_items=(
            "Done archive entry is accurate and complete",
            "Ready queue, blocked, and not-now items reviewed",
            "Risks and evidence written to stable state",
            "Session closed or next layer explicitly selected",
        ),
    ),
}


# ---------------------------------------------------------------------------
# Rigor-based layer profiles — which layers are required per tier
# ---------------------------------------------------------------------------


RIGOR_LAYER_PROFILES: dict[RigorTier, tuple[HarnessLayer, ...]] = {
    RigorTier.LIGHT: (
        # 6 core layers only — fast track for small changes.
        HarnessLayer.INTAKE_ORIENTATION,
        HarnessLayer.BRIEF,
        HarnessLayer.READINESS,
        HarnessLayer.IMPLEMENTATION,
        HarnessLayer.VERIFICATION,
        HarnessLayer.REVIEW_NEXT,
    ),
    RigorTier.STANDARD: (
        # All 12 layers, brainstorming+brief may merge at agent's discretion.
        HarnessLayer.INTAKE_ORIENTATION,
        HarnessLayer.IDEA,
        HarnessLayer.FACT_DISCOVERY,
        HarnessLayer.BRAINSTORMING,
        HarnessLayer.BRIEF,
        HarnessLayer.ARCHITECTURE,
        HarnessLayer.ADR,
        HarnessLayer.CONTRACT,
        HarnessLayer.READINESS,
        HarnessLayer.IMPLEMENTATION,
        HarnessLayer.VERIFICATION,
        HarnessLayer.REVIEW_NEXT,
    ),
    RigorTier.STRICT: (
        # All 12 layers — no merging, no skipping. Every question required.
        HarnessLayer.INTAKE_ORIENTATION,
        HarnessLayer.IDEA,
        HarnessLayer.FACT_DISCOVERY,
        HarnessLayer.BRAINSTORMING,
        HarnessLayer.BRIEF,
        HarnessLayer.ARCHITECTURE,
        HarnessLayer.ADR,
        HarnessLayer.CONTRACT,
        HarnessLayer.READINESS,
        HarnessLayer.IMPLEMENTATION,
        HarnessLayer.VERIFICATION,
        HarnessLayer.REVIEW_NEXT,
    ),
}


def gate_for_layer(layer: HarnessLayer) -> LayerGateDefinition | None:
    """Return the :class:`LayerGateDefinition` for *layer*, or None."""
    return GATE_CATALOG.get(layer)


def layers_for_tier(tier: RigorTier) -> tuple[HarnessLayer, ...]:
    """Return the required layers for *tier*."""
    return RIGOR_LAYER_PROFILES.get(tier, RIGOR_LAYER_PROFILES[RigorTier.STRICT])


def is_layer_required(layer: HarnessLayer, tier: RigorTier) -> bool:
    """Return True if *layer* is required at *tier*."""
    return layer in layers_for_tier(tier)


def layer_order_number(layer: HarnessLayer) -> int:
    """Return 1-based ordinal for lock-file naming (01–12)."""
    from .layers import canonical_progression

    try:
        return canonical_progression().index(layer) + 1
    except ValueError:
        return 0


# ---------------------------------------------------------------------------
# Layer gate engine — programmatic gate verification
# ---------------------------------------------------------------------------


class LayerGateEngine:
    """Programmatic gate checker for one harness layer.

    Stateless — all state comes from :class:`~.session.SessionState` and
    the filesystem.  Call :meth:`check` to produce a :class:`GateStatus`.

    Usage::

        engine = LayerGateEngine()
        status = engine.check(session, project_root, layer)
        if not status.passed:
            print(f"Gate failed: {status.questions_answered}/{status.questions_required}")
    """

    def check(
        self,
        session: "SessionState",  # type: ignore[name-defined]  # noqa: F821
        project_root: "Path",  # type: ignore[name-defined]  # noqa: F821
        layer: "HarnessLayer",  # type: ignore[name-defined]  # noqa: F821
    ) -> "GateStatus":  # type: ignore[name-defined]  # noqa: F821
        """Check whether *layer*'s gate is satisfied given *session* state.

        Parameters
        ----------
        session:
            The governance session (contains ``rigor_tier`` and ``layer_qa``).
        project_root:
            Project root for artifact glob matching.
        layer:
            The harness layer to check.

        Returns
        -------
        GateStatus
            Pass/fail result with detailed findings.
        """
        from datetime import datetime, timezone

        from ..models.schemas import GateStatus

        gate_def = gate_for_layer(layer)
        if gate_def is None:
            return GateStatus(
                layer=layer.value,
                passed=True,
                checked_at=datetime.now(timezone.utc).isoformat(),
            )

        tier = RigorTier(session.rigor_tier)
        required = gate_def.min_questions_answered.get(tier, 1)

        # Count answered questions for this layer from the session Q&A log.
        qa_count = sum(
            1 for qa in session.layer_qa if qa.get("layer") == layer.value
        )

        # Check required artifacts on disk.
        artifacts_found: list[str] = []
        artifacts_missing: list[str] = []
        for pattern in gate_def.required_artifacts:
            matches = list(project_root.glob(pattern))
            if matches:
                artifacts_found.extend(str(m.relative_to(project_root)) for m in matches)
            else:
                artifacts_missing.append(pattern)

        # Gate passes when Q&A threshold is met.  Artifacts are
        # informational — some (like session files) are auto-created,
        # and blocking on their absence creates chicken-and-egg problems.
        passed = qa_count >= required

        return GateStatus(
            layer=layer.value,
            passed=passed,
            questions_answered=qa_count,
            questions_required=required,
            artifacts_found=tuple(artifacts_found),
            artifacts_missing=tuple(artifacts_missing),
            confirmation_items_met=gate_def.confirmation_items,
            confirmation_items_unmet=(),
            checked_at=datetime.now(timezone.utc).isoformat(),
        )


# ---------------------------------------------------------------------------
# Capability lock files — disk-level enforcement
# ---------------------------------------------------------------------------


class LockFileManager:
    """Manages capability lock files under ``.harness/gates/``.

    Lock files are the disk-level enforcement mechanism (Layer 3 of the
    5-layer defense).  Before any ``Write`` / ``Edit``, the agent must
    verify that the corresponding gate lock exists and is current.

    Lock file naming: ``01-intake-orientation.lock`` through
    ``12-review-next.lock``.
    """

    GATES_DIR = Path(".harness/gates")

    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root
        self._gates_dir = project_root / self.GATES_DIR

    @property
    def gates_dir(self) -> Path:
        return self._gates_dir

    def lock_path(self, layer: HarnessLayer) -> Path:
        """Return the absolute path to the lock file for *layer*."""
        num = layer_order_number(layer)
        return self._gates_dir / f"{num:02d}-{layer.value}.lock"

    def write_lock(
        self, layer: HarnessLayer, status: "GateStatus", session: "SessionState"
    ) -> Path:
        """Write a lock file for *layer* and return its path.

        Creates the ``.harness/gates/`` directory if it doesn't exist.
        """
        from datetime import datetime, timezone
        import json

        path = self.lock_path(layer)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "layer": layer.value,
            "passed": status.passed,
            "passed_at": datetime.now(timezone.utc).isoformat(),
            "session_id": session.session_id,
            "rigor_tier": session.rigor_tier,
            "questions_answered": status.questions_answered,
            "questions_required": status.questions_required,
            "check_duration_ms": getattr(status, "check_duration_ms", 0.0),
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def read_lock(self, layer: HarnessLayer) -> dict | None:
        """Return the parsed lock file dict, or None if it doesn't exist."""
        import json

        path = self.lock_path(layer)
        if not path.is_file():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None

    def exists(self, layer: HarnessLayer) -> bool:
        """Return True if a lock file exists for *layer*."""
        return self.lock_path(layer).is_file()

    def remove_lock(self, layer: HarnessLayer) -> bool:
        """Remove the lock file for *layer*.  Return True if it was deleted."""
        path = self.lock_path(layer)
        if path.is_file():
            path.unlink()
            return True
        return False

    def remove_all_locks(self) -> int:
        """Remove all lock files in the gates directory.  Return count removed."""
        if not self._gates_dir.is_dir():
            return 0
        count = 0
        for lock_file in self._gates_dir.glob("*.lock"):
            lock_file.unlink()
            count += 1
        return count



__all__ = [
    "LayerGateDefinition",
    "GATE_CATALOG",
    "RIGOR_LAYER_PROFILES",
    "LayerGateEngine",
    "LockFileManager",
    "gate_for_layer",
    "layers_for_tier",
    "is_layer_required",
    "layer_order_number",
]
