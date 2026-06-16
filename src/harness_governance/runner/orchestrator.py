"""Orchestrator prompt builder for the Subagent runner.

Assembles a complete orchestrator prompt by combining:

1. The orchestrator rules template (``orchestrator.md``).
2. Pre-rendered role prompts (planner, contract-writer, implementer, reviewer).
3. Queue item context, checkpoint, and execution mode.

The output is a single Markdown document that an agent can load to
execute the orchestration loop — dispatching subagents via Agent tool,
collecting structured JSON results, and writing state via CLI commands.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from ..file_ops.checkpoint import Checkpoint
from ..file_ops.queue import read_queue
from ..models.schemas import QueueItem
from .template_renderer import TemplateRenderer
from .variables import RoleVariables, VariableExtractor

# Platform-specific dispatch instructions for the orchestrator template.
_PLATFORM_DISPATCH: dict[str, str] = {
    "claude-code": (
        "Use the Agent tool to spawn a subagent:\n"
        "   - `agent_type: general-purpose`\n"
        "   - Pass the pre-rendered role prompt as the subagent's task"
    ),
    "codex": (
        "Use Codex's built-in task/agent delegation (NOT an external process):\n"
        "   - Dispatch a subagent within the current session\n"
        "   - Pass the pre-rendered role prompt as the subagent's instructions\n"
        "   - Do NOT use `codex exec` — that spawns a fresh CLI process, not a subagent"
    ),
    "cline": (
        "Use Cline's native task delegation:\n"
        "   - Dispatch a sub-task within the current Cline session\n"
        "   - Pass the pre-rendered role prompt as the sub-task's instructions"
    ),
    "cursor": (
        "Use Cursor's native Agent mode sub-task:\n"
        "   - Dispatch via Cursor's built-in agent delegation within the session\n"
        "   - Pass the pre-rendered role prompt as the sub-task's instructions"
    ),
    "opencode": (
        "Use OpenCode's native subagent spawning:\n"
        "   - Dispatch a subagent within the current OpenCode session\n"
        "   - Pass the pre-rendered role prompt as the subagent's instructions"
    ),
    "windsurf": (
        "Use Windsurf Cascade's native delegation:\n"
        "   - Dispatch a sub-task within the current Windsurf session\n"
        "   - Pass the pre-rendered role prompt as the sub-task's instructions"
    ),
    "qoderwork": (
        "Use the Task tool to spawn a subagent:\n"
        "   - `subagent_type: general-purpose`\n"
        "   - Pass the pre-rendered role prompt as the subagent's task"
    ),
    "generic": (
        "Dispatch a subagent using your platform's native subagent mechanism:\n"
        "   - Do NOT spawn an external CLI process\n"
        "   - Pass the pre-rendered role prompt text as-is"
    ),
}

# Platform-specific hard-gate fallback instructions.
_PLATFORM_HARD_GATE: dict[str, str] = {
    "claude-code": (
        "Run in the main conversation (not a subagent) when:\n"
        "- The user explicitly asks for it\n"
        "- Release or phase closeout is involved\n"
        "- Security, persistence, deployment, or cross-repository behavior changes\n"
        "- Subagent findings conflict with main-window evidence"
    ),
    "codex": (
        "Run in the main Codex session (not a subagent) when:\n"
        "- The user explicitly asks for it\n"
        "- Release or phase closeout is involved\n"
        "- Security, persistence, deployment, or cross-repository behavior changes\n"
        "- Subagent findings conflict with main-window evidence\n"
        "- Do NOT fall back to `codex exec` for this — stay in the current session"
    ),
    "cline": (
        "Run in the main Cline conversation (not a sub-task) when:\n"
        "- The user explicitly asks for it\n"
        "- Release or phase closeout is involved\n"
        "- Security, persistence, deployment, or cross-repository behavior changes\n"
        "- Sub-task findings conflict with main-window evidence"
    ),
    "cursor": (
        "Run in the main Cursor Agent conversation (not a sub-task) when:\n"
        "- The user explicitly asks for it\n"
        "- Release or phase closeout is involved\n"
        "- Security, persistence, deployment, or cross-repository behavior changes\n"
        "- Sub-task findings conflict with main-window evidence"
    ),
    "opencode": (
        "Run directly in the main OpenCode session (not a subagent) when:\n"
        "- The user explicitly asks for it\n"
        "- Release or phase closeout is involved\n"
        "- Security, persistence, deployment, or cross-repository behavior changes\n"
        "- Subagent findings conflict with main-window evidence"
    ),
    "windsurf": (
        "Run directly in the main Windsurf Cascade session (not a sub-task) when:\n"
        "- The user explicitly asks for it\n"
        "- Release or phase closeout is involved\n"
        "- Security, persistence, deployment, or cross-repository behavior changes\n"
        "- Sub-task findings conflict with main-window evidence"
    ),
    "qoderwork": (
        "Run directly in the main session (not a subagent) when:\n"
        "- The user explicitly asks for it\n"
        "- Release or phase closeout is involved\n"
        "- Security, persistence, deployment, or cross-repository behavior changes\n"
        "- Subagent findings conflict with main-window evidence"
    ),
    "generic": (
        "Run in the main session instead of a subagent when:\n"
        "- The user explicitly asks for it\n"
        "- Release or phase closeout is involved\n"
        "- Security, persistence, deployment, or cross-repository behavior changes\n"
        "- Subagent findings conflict with main-window evidence"
    ),
}


@dataclass(slots=True)
class OrchestratorPrompt:
    """The fully assembled orchestrator prompt."""

    text: str
    roles_needed: list[str]
    queue_item_raw: str
    missing_variables: list[str]


class OrchestratorPromptBuilder:
    """Build a complete orchestrator prompt from project files."""

    def __init__(self) -> None:
        self._renderer = TemplateRenderer()
        self._extractor = VariableExtractor()

    def build(
        self,
        *,
        project_root: Path,
        queue_file: Path = Path("NEXT.md"),
        checkpoint_file: Path | None = None,
        mode: Literal["bounded", "boundary"] = "bounded",
        max_rounds: int = 1,
        platform: str | None = None,
    ) -> OrchestratorPrompt:
        """Build the full orchestrator prompt.

        Steps:
        1. Read NEXT.md → find first [ready] or [active] item.
        2. Extract variables for each required role.
        3. Render role prompts.
        4. Load orchestrator template and embed pre-rendered prompts.
        5. Append state management instructions.

        If ``platform`` is None, defaults to ``"generic"``.
        """
        project_root = project_root.resolve()
        queue_path = (project_root / queue_file).resolve()

        # 1. Find target queue item
        items = read_queue(queue_path)
        target = next((i for i in items if i.ready), None) or next(
            (i for i in items if i.active), None
        )
        if target is None:
            raise ValueError("No [ready] or [active] item found in queue")

        return self.build_for_item(
            project_root=project_root,
            queue_item=target,
            checkpoint_file=checkpoint_file,
            mode=mode,
            max_rounds=max_rounds,
            platform=platform,
        )

    def build_for_item(
        self,
        *,
        project_root: Path,
        queue_item: QueueItem,
        checkpoint_file: Path | None = None,
        mode: Literal["bounded", "boundary"] = "bounded",
        max_rounds: int = 1,
        platform: str | None = None,
    ) -> OrchestratorPrompt:
        """Build the orchestrator prompt for a specific queue item."""
        project_root = project_root.resolve()
        effective_platform = platform or "generic"

        # 2. Determine required roles from the ready item
        roles_needed = self._determine_roles(queue_item)

        # 3. Extract variables and render role prompts
        rendered_prompts: dict[str, str] = {}
        all_missing: list[str] = []

        for role in roles_needed:
            variables = self._extractor.extract_for_role(
                project_root, queue_item, role
            )
            rendered = self._renderer.render(role, variables)
            rendered_prompts[role] = rendered
            unresolved = self._renderer.find_unresolved(rendered)
            all_missing.extend(unresolved)

        # 4. Load orchestrator template
        orchestrator_template = self._renderer.load_template("orchestrator")

        # 5. Assemble the complete prompt
        prompt_text = self._assemble(
            template=orchestrator_template,
            rendered_prompts=rendered_prompts,
            queue_item=queue_item,
            checkpoint_file=checkpoint_file,
            project_root=project_root,
            mode=mode,
            max_rounds=max_rounds,
            platform=effective_platform,
        )

        return OrchestratorPrompt(
            text=prompt_text,
            roles_needed=roles_needed,
            queue_item_raw=queue_item.raw,
            missing_variables=all_missing,
        )

    # Internal helpers -------------------------------------------------------

    def _determine_roles(self, queue_item: QueueItem) -> list[str]:
        """Determine which roles are needed based on the queue item.

        If the item has an explicit ``Role:`` field, use that role only.
        Otherwise, infer from the layer or return the full pipeline.
        """
        from ..file_ops.queue import extract_ready_block_fields

        fields = extract_ready_block_fields(queue_item.raw)
        role_value = fields.get("role", "").strip().lower()

        role_map = {
            # Core pipeline roles
            "planner": ["planner"],
            "contract writer": ["contract-writer"],
            "contract/test writer": ["contract-writer"],
            "implementer": ["implementer"],
            "reviewer": ["reviewer"],
            "reviewer/verifier": ["reviewer"],
            # Governance roles
            "adr writer": ["adr-writer"],
            "adr-writer": ["adr-writer"],
            "fact finder": ["fact-finder-reviewer"],
            "fact finder reviewer": ["fact-finder-reviewer"],
            "fact-finder-reviewer": ["fact-finder-reviewer"],
            "readiness gate writer": ["readiness-gate-writer"],
            "readiness-gate-writer": ["readiness-gate-writer"],
            "document gardener": ["document-gardener"],
            "document-gardener": ["document-gardener"],
            "integrator": ["integrator"],
        }

        if role_value in role_map:
            return role_map[role_value]

        # Infer from layer if no explicit role
        layer_value = fields.get("layer", "").strip().lower()
        layer_to_role = {
            "adr": ["adr-writer"],
            "fact-discovery": ["fact-finder-reviewer"],
            "readiness": ["readiness-gate-writer"],
        }
        if layer_value in layer_to_role:
            return layer_to_role[layer_value]

        # No explicit role and no layer hint → full core pipeline
        return ["planner", "contract-writer", "implementer", "reviewer"]

    def _assemble(
        self,
        *,
        template: str,
        rendered_prompts: dict[str, str],
        queue_item: QueueItem,
        checkpoint_file: Path | None,
        project_root: Path,
        mode: str,
        max_rounds: int,
        platform: str = "generic",
    ) -> str:
        """Assemble the complete orchestrator prompt document."""
        sections: list[str] = []

        # Substitute platform-specific placeholders in the template
        dispatch_text = _PLATFORM_DISPATCH.get(
            platform, _PLATFORM_DISPATCH["generic"]
        )
        hard_gate_text = _PLATFORM_HARD_GATE.get(
            platform, _PLATFORM_HARD_GATE["generic"]
        )
        resolved_template = template.replace("{{DISPATCH_INSTRUCTION}}", dispatch_text)
        resolved_template = resolved_template.replace("{{HARD_GATE_COMMAND}}", hard_gate_text)

        # Orchestrator rules
        sections.append(resolved_template)

        # Pre-rendered role prompts
        sections.append("\n---\n\n# Pre-Rendered Role Prompts\n")

        role_labels = {
            # Core pipeline
            "planner": "PLANNER_PROMPT",
            "contract-writer": "CONTRACT_WRITER_PROMPT",
            "implementer": "IMPLEMENTER_PROMPT",
            "reviewer": "REVIEWER_PROMPT",
            # Governance
            "adr-writer": "ADR_WRITER_PROMPT",
            "fact-finder-reviewer": "FACT_FINDER_REVIEWER_PROMPT",
            "readiness-gate-writer": "READINESS_GATE_WRITER_PROMPT",
            "document-gardener": "DOCUMENT_GARDENER_PROMPT",
            "integrator": "INTEGRATOR_PROMPT",
        }

        for role, prompt_text in rendered_prompts.items():
            label = role_labels.get(role, role.upper().replace("-", "_") + "_PROMPT")
            sections.append(f"## {label}\n\n```role-prompt\n{prompt_text}\n```\n")

        # Queue item context
        sections.append(
            f"\n---\n\n# Current Queue Item\n\n```\n{queue_item.raw}\n```\n"
        )

        # Checkpoint (if exists)
        if checkpoint_file is not None:
            cp_path = (project_root / checkpoint_file).resolve()
            if cp_path.is_file():
                cp_text = cp_path.read_text(encoding="utf-8")
                sections.append(f"\n# Current Checkpoint\n\n{cp_text}\n")

        # Execution parameters
        sections.append(
            f"\n---\n\n# Execution Parameters\n\n"
            f"- Mode: `{mode}`\n"
            f"- Max rounds: `{max_rounds}`\n"
            f"- Project root: `{project_root}`\n"
        )

        return "\n".join(sections)


__all__ = ["OrchestratorPromptBuilder", "OrchestratorPrompt"]
