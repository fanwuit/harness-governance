"""Skill call-chain tracing — Gap 5 of the v0.8.0 governance release.

Assigns a unique ``call_id`` (UUID4 hex) to every skill invocation,
records parent-child lineage, and builds a full invocation tree for
visualisation and audit.  Persists records as NDJSON under
``.harness/skill-chains/<session_id>.ndjson``.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ..file_ops.ndjson_writer import NDJSONWriter
from ..models.schemas import InvocationTreeNode, SkillChainReport, SkillInvocation

logger = logging.getLogger("harness.skill_chain")


class SkillChainTracer:
    """Trace skill invocations across a governance session.

    Usage::

        tracer = SkillChainTracer(project_root)
        call_id = tracer.start_invocation(
            parent_call_id="abc123",
            child_skill="implementer",
            role="implementer",
            session_id="sess-01",
            layer="implementation",
        )
        tracer.end_invocation(call_id, exit_code=0, verdict="success")
        # or, for pre-built records:
        tracer.record_full_invocation(invocation)
    """

    CHAINS_DIR = Path(".harness/skill-chains")

    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root
        self._ndjson = NDJSONWriter()
        self._active_calls: dict[str, SkillInvocation] = {}

    # -- Public API -------------------------------------------------------

    def start_invocation(
        self,
        *,
        parent_call_id: str | None,
        child_skill: str,
        role: str = "",
        session_id: str = "",
        layer: str = "",
        round_index: int = 0,
        files_passed: list[str] | None = None,
        parent_skill: str = "",
        required_tier: str = "",
        actual_tier: str = "",
        platform: str = "",
        model_label: str = "",
        adapter: str = "",
        verifier_required: bool = True,
        owner_files: list[str] | None = None,
        changed_files: list[str] | None = None,
    ) -> str:
        """Begin a new skill invocation and return its ``call_id``.

        Does NOT persist until :meth:`end_invocation` or
        :meth:`record_full_invocation` is called.
        """
        call_id = uuid.uuid4().hex

        self._active_calls[call_id] = SkillInvocation(
            call_id=call_id,
            parent_call_id=parent_call_id,
            parent_skill=parent_skill,
            child_skill=child_skill,
            role=role,
            session_id=session_id,
            layer=layer,
            round_index=round_index,
            files_passed=tuple(files_passed or []),
            started_at=datetime.now(timezone.utc).isoformat(),
            trace_depth=0,  # computed on finalize
            required_tier=required_tier,
            actual_tier=actual_tier,
            platform=platform,
            model_label=model_label,
            adapter=adapter,
            verifier_required=verifier_required,
            owner_files=tuple(owner_files or []),
            changed_files=tuple(changed_files or []),
        )

        return call_id

    def end_invocation(
        self,
        call_id: str,
        *,
        exit_code: int = 0,
        verdict: str = "success",
        files_returned: list[str] | None = None,
    ) -> SkillInvocation | None:
        """Complete a previously started invocation and persist to NDJSON.

        Returns the completed :class:`SkillInvocation`, or ``None`` if
        *call_id* was never started.
        """
        inv = self._active_calls.pop(call_id, None)
        if inv is None:
            logger.warning("end_invocation for unknown call_id: %s", call_id)
            return None

        inv.finished_at = datetime.now(timezone.utc).isoformat()
        inv.exit_code = exit_code
        inv.verdict = verdict
        inv.files_returned = tuple(files_returned or [])

        # Compute duration.
        try:
            start = datetime.fromisoformat(inv.started_at)
            end = datetime.fromisoformat(inv.finished_at)
            inv.duration_seconds = (end - start).total_seconds()
        except Exception:
            pass

        self.record_full_invocation(inv)
        return inv

    def record_full_invocation(self, invocation: SkillInvocation) -> bool:
        """Persist a complete :class:`SkillInvocation` to the NDJSON log.

        Use this when you already have a fully-built record (e.g.
        parsed from a subagent result).
        """
        if not invocation.session_id:
            logger.warning(
                "Skipping invocation with no session_id: %s", invocation.call_id
            )
            return False

        log_path = self._ndjson_path(invocation.session_id)
        data = invocation.model_dump(exclude_none=True)
        return self._ndjson.append(log_path, data)

    def build_tree(self, session_id: str) -> InvocationTreeNode | None:
        """Build a recursive invocation tree for *session_id*.

        Returns ``None`` if no invocations are recorded.
        """
        invocations = self._load_invocations(session_id)
        if not invocations:
            return None

        # Index by call_id.
        by_id: dict[str, SkillInvocation] = {i.call_id: i for i in invocations}

        # Compute trace_depth for each node.
        self._compute_depths(by_id)

        # Find roots (nodes with no parent or whose parent is absent).
        roots = [
            i
            for i in invocations
            if i.parent_call_id is None or i.parent_call_id not in by_id
        ]

        if not roots:
            # Fallback: treat the first invocation as root.
            roots = [invocations[0]]

        # Build tree(s).  If there are multiple roots, wrap them under
        # a synthetic root.
        children = [self._build_subtree(inv, by_id) for inv in roots]

        if len(children) == 1:
            return children[0]

        return InvocationTreeNode(
            call_id="root",
            skill="(session)",
            role="",
            children=tuple(children),
        )

    def compute_report(self, session_id: str) -> SkillChainReport:
        """Produce a full :class:`SkillChainReport` for *session_id*."""
        invocations = self._load_invocations(session_id)

        if not invocations:
            return SkillChainReport(
                generated_at=datetime.now(timezone.utc).isoformat(),
            )

        by_id = {i.call_id: i for i in invocations}
        self._compute_depths(by_id)

        max_depth = max((i.trace_depth for i in invocations), default=0)
        unique_skills = tuple(
            sorted({i.child_skill for i in invocations if i.child_skill})
        )

        # Find orphans.
        orphans = tuple(
            i.call_id
            for i in invocations
            if i.parent_call_id is not None and i.parent_call_id not in by_id
        )

        # Longest chain: find the deepest leaf, walk up to root.
        deepest = max(invocations, key=lambda i: i.trace_depth)
        longest: list[str] = []
        current: SkillInvocation | None = deepest
        while current is not None:
            longest.insert(0, current.call_id)
            current = (
                by_id.get(current.parent_call_id) if current.parent_call_id else None
            )

        tree = self.build_tree(session_id)

        return SkillChainReport(
            total_invocations=len(invocations),
            max_depth=max_depth,
            unique_skills=unique_skills,
            longest_chain=tuple(longest),
            orphan_invocations=orphans,
            tree=tree,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def validate_chain_integrity(self, session_id: str) -> list[str]:
        """Check the invocation chain for structural problems.

        Returns a list of issue descriptions (empty = clean).
        """
        issues: list[str] = []
        invocations = self._load_invocations(session_id)

        if not invocations:
            return ["No skill invocation records found for this session."]

        by_id = {i.call_id: i for i in invocations}
        call_ids = set(by_id.keys())

        # 1. Orphan detection.
        for i in invocations:
            if i.parent_call_id is not None and i.parent_call_id not in call_ids:
                issues.append(
                    f"Orphan invocation: {i.call_id} ({i.child_skill}) "
                    f"references unknown parent {i.parent_call_id}"
                )

        # 2. Cycle detection (DFS).
        visited: set[str] = set()
        rec_stack: set[str] = set()

        def _dfs(cid: str) -> bool:
            visited.add(cid)
            rec_stack.add(cid)
            inv = by_id.get(cid)
            if inv and inv.parent_call_id:
                pid = inv.parent_call_id
                if pid not in visited and pid in by_id:
                    if _dfs(pid):
                        return True
                elif pid in rec_stack:
                    return True
            rec_stack.discard(cid)
            return False

        for cid in call_ids:
            if cid not in visited:
                if _dfs(cid):
                    issues.append(
                        f"Cycle detected in invocation chain starting at {cid}"
                    )
                    break

        # 3. Incomplete invocations (started but never finished).
        for i in invocations:
            if not i.finished_at:
                issues.append(
                    f"Incomplete invocation: {i.call_id} ({i.child_skill}) "
                    f"has no finished_at timestamp"
                )

        return issues

    def to_mermaid(self, session_id: str) -> str:
        """Generate a Mermaid flowchart diagram of the invocation tree.

        Returns a string suitable for embedding in markdown.
        """
        invocations = self._load_invocations(session_id)
        if not invocations:
            return "graph TD\n  empty[No invocations recorded]"

        lines = ["graph TD"]
        _by_id = {i.call_id: i for i in invocations}

        for i in invocations:
            node_id = i.call_id[:8]
            label = f"{i.child_skill or i.role or '?'}"
            if i.verdict == "failure":
                label += " ✗"
            elif i.verdict == "success":
                label += " ✓"
            duration = f" ({i.duration_seconds:.1f}s)" if i.duration_seconds else ""
            lines.append(f"  {node_id}[{label}{duration}]")

            if i.parent_call_id:
                parent_id = i.parent_call_id[:8]
                lines.append(f"  {parent_id} --> {node_id}")

        return "\n".join(lines)

    def to_ascii_tree(self, session_id: str) -> str:
        """Generate an ASCII-art invocation tree.

        Returns a multi-line string suitable for terminal display.
        """
        tree = self.build_tree(session_id)
        if tree is None:
            return "(no invocations)"

        return self._render_ascii(tree, prefix="", is_last=True)

    # -- Internal ---------------------------------------------------------

    def _ndjson_path(self, session_id: str) -> Path:
        chains_dir = self._project_root / self.CHAINS_DIR
        chains_dir.mkdir(parents=True, exist_ok=True)
        return chains_dir / f"{session_id}.ndjson"

    @staticmethod
    def _read_invocations(session_id: str, project_root: Path) -> list[SkillInvocation]:
        """Parse all NDJSON invocation records for a session."""
        records: list[SkillInvocation] = []
        log_path = project_root / SkillChainTracer.CHAINS_DIR / f"{session_id}.ndjson"
        if not log_path.is_file():
            return records

        for line in log_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                records.append(SkillInvocation.model_validate_json(line))
            except Exception:
                logger.debug("Skipping unparseable invocation record", exc_info=True)
        return records

    def _load_invocations(self, session_id: str) -> list[SkillInvocation]:
        """Load invocations for this tracer's session."""
        return self._read_invocations(session_id, self._project_root)

    @staticmethod
    def _compute_depths(by_id: dict[str, SkillInvocation]) -> None:
        """Set ``trace_depth`` on every invocation in *by_id* (mutates)."""

        def _depth(call_id: str, visited: set[str] | None = None) -> int:
            if visited is None:
                visited = set()
            if call_id in visited:
                return 0
            visited.add(call_id)
            inv = by_id.get(call_id)
            if inv is None or inv.parent_call_id is None:
                return 0
            return 1 + _depth(inv.parent_call_id, visited)

        for cid, inv in by_id.items():
            inv.trace_depth = _depth(cid)

    @staticmethod
    def _build_subtree(
        inv: SkillInvocation,
        by_id: dict[str, SkillInvocation],
    ) -> InvocationTreeNode:
        """Recursively build an ``InvocationTreeNode``."""
        child_invocations = [
            child for child in by_id.values() if child.parent_call_id == inv.call_id
        ]
        children = tuple(
            SkillChainTracer._build_subtree(child, by_id) for child in child_invocations
        )
        return InvocationTreeNode(
            call_id=inv.call_id,
            skill=inv.child_skill or inv.role,
            role=inv.role,
            duration_s=inv.duration_seconds,
            verdict=inv.verdict,
            children=children,
        )

    @classmethod
    def _render_ascii(
        cls,
        node: InvocationTreeNode,
        prefix: str = "",
        is_last: bool = True,
    ) -> str:
        """Recursively render an ASCII tree."""
        connector = "└── " if is_last else "├── "
        verdict_mark = ""
        if node.verdict == "success":
            verdict_mark = " ✓"
        elif node.verdict == "failure":
            verdict_mark = " ✗"
        duration = f" ({node.duration_s:.1f}s)" if node.duration_s else ""

        lines = [f"{prefix}{connector}{node.skill}{verdict_mark}{duration}"]

        child_prefix = prefix + ("    " if is_last else "│   ")
        for i, child in enumerate(node.children):
            is_last_child = i == len(node.children) - 1
            lines.append(cls._render_ascii(child, child_prefix, is_last_child))

        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Gate hook registration — called at import time
# ---------------------------------------------------------------------------


def _gate_hook_skill_chain_verification(
    session,  # SessionState
    project_root: Path,
) -> list[str]:
    """VERIFICATION hook: validate skill chain integrity.

    Checks for orphans, cycles, and incomplete invocations.
    """
    failures: list[str] = []
    tracer = SkillChainTracer(project_root)
    session_id = getattr(session, "session_id", "") or ""

    if not session_id:
        return failures

    issues = tracer.validate_chain_integrity(session_id)

    # Only block on hard errors (orphans, cycles).  "No records" is
    # an advisory — the blocking_artifacts on VERIFICATION gate already
    # ensures the NDJSON file exists.
    for issue in issues:
        if "No skill invocation records found" in issue:
            continue  # non-blocking: may be a session without subagent calls
        failures.append(issue)

    return failures


def _gate_hook_skill_chain_review(
    session,  # SessionState
    project_root: Path,
) -> list[str]:
    """REVIEW_NEXT hook: ensure the call chain is archived for audit."""
    failures: list[str] = []
    tracer = SkillChainTracer(project_root)
    session_id = getattr(session, "session_id", "") or ""

    if not session_id:
        return failures

    report = tracer.compute_report(session_id)

    if report.total_invocations == 0:
        failures.append(
            "No skill invocation records archived — audit trail is incomplete. "
            "Consider running 'harness skill-chain trace' to verify."
        )

    if report.orphan_invocations:
        failures.append(
            f"Skill chain has {len(report.orphan_invocations)} orphan invocation(s) "
            f"that cannot be traced to a parent. Review the call chain before archiving."
        )

    if report.max_depth == 0 and report.total_invocations > 1:
        failures.append(
            "Skill chain is flat (depth=0) with multiple invocations — "
            "parent-child relationships may not have been recorded correctly."
        )

    return failures


# ---------------------------------------------------------------------------
# Gate hook: capability-tier enforcement
# ---------------------------------------------------------------------------


def _gate_hook_capability_tier(session, project_root: Path) -> list[str]:
    """Enforce that execution/mechanical work has an independent verifier.

    Fails at REVIEW_NEXT layer when:
    - Any invocation with ``verifier_required=true`` has no matching
      verifier invocation with ``actual_tier=strong``.
    - The verifier and a lower-tier role share the same invocation
      (self-verification).
    """
    session_id = session.session_id
    records = _load_invocations(_chains_path(project_root, session_id))
    if not records:
        return []

    failures: list[str] = []
    needs_verifier: list[SkillInvocation] = [
        r for r in records if r.verifier_required
    ]
    if not needs_verifier:
        return []

    verifier_calls: set[str] = set()
    for r in records:
        if r.role == "verifier" and r.actual_tier == "strong":
            verifier_calls.add(r.call_id)

    for inv in needs_verifier:
        if not verifier_calls:
            failures.append(
                f"Role '{inv.role}' requires an independent strong verifier "
                f"but no verifier invocation with actual_tier=strong was found. "
                f"Execution/mechanical tier work cannot close out without "
                f"independent verification."
            )
            break

        if inv.call_id in verifier_calls:
            failures.append(
                f"Role '{inv.role}' (required_tier={inv.required_tier}) "
                f"cannot self-verify. An independent strong verifier must "
                f"accept the work."
            )

    return failures


def _chains_path(project_root: Path, session_id: str) -> Path:
    return project_root / SkillChainTracer.CHAINS_DIR / f"{session_id}.ndjson"


def _load_invocations(path: Path) -> list[SkillInvocation]:
    if not path.is_file():
        return []
    import json

    records: list[SkillInvocation] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
            records.append(SkillInvocation.model_validate(data))
        except (json.JSONDecodeError, Exception):
            continue
    return records


# Module-level registration — fires when skill_chain is imported.
try:
    from .gates import HarnessLayer, register_gate_hook

    register_gate_hook(HarnessLayer.VERIFICATION, _gate_hook_skill_chain_verification)
    register_gate_hook(HarnessLayer.REVIEW_NEXT, _gate_hook_skill_chain_review)
    register_gate_hook(HarnessLayer.REVIEW_NEXT, _gate_hook_capability_tier)
except ImportError:
    pass
