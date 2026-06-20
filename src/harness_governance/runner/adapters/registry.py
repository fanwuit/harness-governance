"""Adapter registry — maps (role, tier, platform) → AgentExecutor.

Resolves adapter configurations from agent directory declarations
(``tiers.json``) and instantiates the appropriate executor.

Harness core never encodes model rankings; it discovers them from
per-agent ``tiers.json`` files at runtime.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from ...models.schemas import (
    AGENT_CONFIG_DIRS,
    AGENT_TIERS_FILE,
    AgentCapabilityDeclaration,
    CapabilityTier,
)
from ...state_machine.agent_declarations import discover_declarations
from ..base import AgentExecutor
from .codex_cli import CodexCliExecutor
from .generic import SubprocessAgentExecutor

class SubagentExecutor(SubprocessAgentExecutor):
    """A subagent executor that delegates to the platform's CLI.

    Uses a simple subprocess command that accepts the prompt as a
    final argument.  The ``model_label`` from ``tiers.json`` is used
    as the command name.
    """

    def __init__(
        self,
        model_label: str = "python3",
        workdir: Path | None = None,
    ) -> None:
        command_template = f"{model_label} -c {{prompt}}"
        super().__init__(
            command_template=command_template,
            prompt_as_arg=False,
            workdir=workdir or Path.cwd(),
            stream_output=True,
        )


_ADAPTER_FACTORIES: dict[str, type[AgentExecutor]] = {
    "subprocess": SubprocessAgentExecutor,
    "subagent": SubagentExecutor,
    "codex-cli": CodexCliExecutor,
}


def register_adapter_type(name: str, cls: type[AgentExecutor]) -> None:
    """Register a custom adapter type so it can be referenced in tiers.json."""
    _ADAPTER_FACTORIES[name] = cls


def resolve_executor(
    role: str,
    tier: CapabilityTier | str,
    project_root: Path | None = None,
    declarations: Sequence[AgentCapabilityDeclaration] | None = None,
    workdir: Path | None = None,
) -> AgentExecutor | None:
    """Resolve an ``AgentExecutor`` for a (role, tier) pair.

    Looks up agent declarations, finds the first matching adapter
    configuration, and instantiates the executor.  Returns ``None``
    when no declaration matches or the adapter type is unknown.
    """
    if declarations is None and project_root is not None:
        declarations = discover_declarations(project_root)

    if not declarations:
        return None

    tier_str = tier.value if isinstance(tier, CapabilityTier) else tier

    for decl in declarations:
        for route in decl.adapters:
            if route.role == role and route.required_tier.value == tier_str:
                factory = _ADAPTER_FACTORIES.get(route.adapter)
                if factory is None:
                    continue

                kwargs: dict = {"workdir": workdir or Path.cwd()}
                if route.model_label:
                    if factory == CodexCliExecutor:
                        kwargs["model"] = route.model_label
                    elif factory == SubprocessAgentExecutor:
                        kwargs["command_template"] = route.model_label
                    elif factory == SubagentExecutor:
                        kwargs["model_label"] = route.model_label

                try:
                    return factory(**kwargs)
                except Exception:
                    continue

    return None


def available_executors(
    declarations: Sequence[AgentCapabilityDeclaration] | None = None,
    project_root: Path | None = None,
) -> list[dict[str, str]]:
    """List all available (role, tier, adapter) combinations."""
    if declarations is None and project_root is not None:
        declarations = discover_declarations(project_root)
    if not declarations:
        return []

    result: list[dict[str, str]] = []
    for decl in declarations:
        for route in decl.adapters:
            result.append(
                {
                    "platform": decl.platform,
                    "role": route.role,
                    "required_tier": route.required_tier.value,
                    "adapter": route.adapter,
                    "model_label": route.model_label or "",
                }
            )
    return result


__all__ = [
    "register_adapter_type",
    "resolve_executor",
    "available_executors",
]
