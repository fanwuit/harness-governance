"""Variable extraction for role-prompt template rendering.

Extracts template variable values from project files (NEXT.md,
task packets, contracts, git diff) so the template renderer can
substitute them into role prompts without any LLM reasoning.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, fields
from pathlib import Path

from ..file_ops.packet import extract_task_packet_sections, packet_dir
from ..file_ops.queue import extract_ready_block_fields
from ..models.schemas import QueueItem

# Sentinel for variables that could not be resolved.
NOT_FOUND_PREFIX = "NOT FOUND"


def _not_found(variable_name: str) -> str:
    return f"{NOT_FOUND_PREFIX}: {{{{{variable_name}}}}}"


@dataclass(slots=True)
class RoleVariables:
    """All template variables for one ready item.

    Fields map directly to ``{{VARIABLE_NAME}}`` placeholders in
    the role-prompt templates.  A value of ``""`` means the variable
    is not applicable for the current role; ``NOT FOUND: …`` means
    the value was expected but could not be extracted.
    """

    # --- Common ---
    queue_item_raw: str = ""
    change_id: str = ""
    layer: str = ""
    role: str = ""

    # --- From task packet ---
    owner_files: str = ""
    contracts: str = ""
    scope: str = ""
    allowed_assumptions: str = ""
    allowed_scope: str = ""
    expected_behavior: str = ""
    failure_behavior: str = ""
    forbidden_scope: str = ""
    verification_commands: str = ""
    done_when: str = ""
    test_plan: str = ""

    # --- Reviewer / Fact Finder only ---
    git_diff: str = ""

    # --- Planner only ---
    project_context: str = ""
    success_criteria: str = ""
    non_goals: str = ""
    stop_conditions: str = ""

    # --- Integrator only ---
    worker_results: str = ""


class VariableExtractor:
    """Extract :class:`RoleVariables` from project files.

    Usage::

        extractor = VariableExtractor()
        variables = extractor.extract(project_root, queue_item)
    """

    def extract(
        self,
        project_root: Path,
        queue_item: QueueItem,
    ) -> RoleVariables:
        """Build a :class:`RoleVariables` from a queue item and its packet."""
        variables = RoleVariables()

        # --- From the queue item itself ---
        variables.queue_item_raw = queue_item.raw
        variables.change_id = queue_item.change_id or ""
        variables.layer = queue_item.layer.value if queue_item.layer else ""

        # Parse inline fields from the raw ready block.
        inline = extract_ready_block_fields(queue_item.raw)
        variables.role = inline.get("role", "")
        variables.forbidden_scope = (
            inline.get("forbidden shortcut", "")
            or inline.get("forbiddenshortcut", "")
            or inline.get("forbidden scope", "")
            or inline.get("forbiddenscope", "")
        )
        variables.verification_commands = inline.get(
            "verification command", ""
        ) or inline.get("verificationcommand", "")
        variables.verification_commands = (
            variables.verification_commands
            or inline.get("verification commands", "")
            or inline.get("verificationcommands", "")
        )
        variables.done_when = inline.get("done when", "") or inline.get("donewhen", "")

        # --- From the task packet (if change_id is set) ---
        if queue_item.change_id:
            pkt = packet_dir(project_root, queue_item.change_id)
            if pkt.is_dir():
                self._extract_from_packet(pkt, variables)

        return variables

    def extract_with_git_diff(
        self,
        project_root: Path,
        queue_item: QueueItem,
    ) -> RoleVariables:
        """Like :meth:`extract` but also fills ``git_diff`` (for reviewer)."""
        variables = self.extract(project_root, queue_item)
        variables.git_diff = _safe_git_diff(project_root)
        return variables

    def extract_for_role(
        self,
        project_root: Path,
        queue_item: QueueItem,
        role: str,
    ) -> RoleVariables:
        """Extract variables and fill role-specific extras.

        * ``reviewer`` / ``fact-finder-reviewer`` → also fills ``git_diff``.
        * ``planner``  → also fills ``project_context``.
        * Other roles  → no extras.
        """
        if role in (
            "reviewer",
            "reviewer-verifier",
            "verifier",
            "fact-finder-reviewer",
        ):
            variables = self.extract_with_git_diff(project_root, queue_item)
        else:
            variables = self.extract(project_root, queue_item)

        if role == "planner":
            variables.project_context = _build_project_context(project_root)

        return variables

    # Internal ---------------------------------------------------------------

    def _extract_from_packet(self, pkt: Path, variables: RoleVariables) -> None:
        """Read packet files and fill task-packet-derived variables."""
        tasks_path = pkt / "tasks.md"
        contracts_path = pkt / "contracts.md"
        tests_path = pkt / "tests.md"
        design_path = pkt / "design.md"

        if tasks_path.is_file():
            sections = extract_task_packet_sections(
                tasks_path.read_text(encoding="utf-8")
            )
            variables.owner_files = variables.owner_files or sections.get(
                "owner files", ""
            )
            variables.expected_behavior = variables.expected_behavior or sections.get(
                "expected behavior", ""
            )
            variables.failure_behavior = variables.failure_behavior or sections.get(
                "failure behavior", ""
            )
            variables.allowed_assumptions = (
                variables.allowed_assumptions or sections.get("allowed assumptions", "")
            )
            # Scope and allowed scope from task packet
            variables.scope = variables.scope or sections.get("scope", "")
            variables.allowed_scope = variables.allowed_scope or sections.get(
                "allowed scope", ""
            )
            # Packet-level fallbacks for fields not yet set from inline
            if not variables.forbidden_scope:
                variables.forbidden_scope = sections.get(
                    "forbidden scope", ""
                ) or sections.get("forbidden shortcuts", "")
            if not variables.verification_commands:
                variables.verification_commands = sections.get(
                    "verification commands", ""
                ) or sections.get("verification", "")
            if not variables.done_when:
                variables.done_when = sections.get("done when", "")
            # Planner extras
            variables.success_criteria = sections.get("success criteria", "")
            variables.non_goals = sections.get("non-goals", "") or sections.get(
                "non goals", ""
            )
            variables.stop_conditions = sections.get("stop conditions", "")

        if contracts_path.is_file():
            variables.contracts = contracts_path.read_text(encoding="utf-8")

        if tests_path.is_file():
            variables.test_plan = tests_path.read_text(encoding="utf-8")

        # Design doc as fallback scope source
        if not variables.scope and design_path.is_file():
            variables.scope = design_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Git diff helper
# ---------------------------------------------------------------------------


def _safe_git_diff(project_root: Path) -> str:
    """Run ``git diff HEAD`` and return output, or empty string on failure."""
    try:
        proc = subprocess.run(
            ["git", "diff", "HEAD"],
            cwd=project_root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return proc.stdout if proc.returncode == 0 else ""
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return ""


# ---------------------------------------------------------------------------
# Project context builder (for planner)
# ---------------------------------------------------------------------------


def _build_project_context(project_root: Path) -> str:
    """Build a lightweight project-context summary for the planner role.

    Reads checkpoint, lists change packets, and summarises queue state.
    """
    parts: list[str] = []

    # Checkpoint
    checkpoint_path = project_root / ".harness" / "run-checkpoint.md"
    if checkpoint_path.is_file():
        parts.append("## Checkpoint\n")
        parts.append(checkpoint_path.read_text(encoding="utf-8"))

    # Change packets
    changes_root = project_root / "docs" / "changes"
    if changes_root.is_dir():
        packet_ids = sorted(
            d.name for d in changes_root.iterdir() if d.is_dir() and d.name != "archive"
        )
        if packet_ids:
            parts.append("## Active Change Packets\n")
            parts.append("\n".join(f"- {pid}" for pid in packet_ids))

    # Queue
    queue_path = project_root / "NEXT.md"
    if queue_path.is_file():
        parts.append("## Queue (NEXT.md)\n")
        parts.append(queue_path.read_text(encoding="utf-8"))

    return "\n\n".join(parts) if parts else _not_found("PROJECT_CONTEXT")


# ---------------------------------------------------------------------------
# Utility: check if a variable is "not found"
# ---------------------------------------------------------------------------


def is_not_found(value: str) -> bool:
    """Return True if the value is a NOT FOUND sentinel."""
    return value.startswith(NOT_FOUND_PREFIX)


def fill_missing(variables: RoleVariables) -> RoleVariables:
    """Replace empty strings with NOT FOUND sentinels for required fields.

    This is called by the template renderer before substitution so that
    missing variables are visible in the rendered prompt.
    """
    # Only fill fields that are expected to have values for any role.
    # Role-specific fields (git_diff, project_context) are left empty
    # if not applicable.
    for f in fields(variables):
        current = getattr(variables, f.name)
        if current == "" and f.name not in _OPTIONAL_FIELDS:
            setattr(variables, f.name, _not_found(f.name.upper()))
    return variables


# Fields that are role-conditional and should NOT get NOT FOUND.
_OPTIONAL_FIELDS = frozenset(
    {
        "git_diff",
        "project_context",
        "success_criteria",
        "non_goals",
        "stop_conditions",
        "scope",
        "allowed_scope",
        "worker_results",
    }
)


__all__ = [
    "RoleVariables",
    "VariableExtractor",
    "NOT_FOUND_PREFIX",
    "is_not_found",
    "fill_missing",
]
