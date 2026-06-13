"""``harness init`` command.

Writes ``.harness/config.toml`` and a per-platform skill adapter so the
user's AI agent can discover and use the governance CLI. Idempotent:
re-running without ``--force`` is a no-op.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from pathlib import Path

import click

from ..config.defaults import PLATFORM_HINTS, PLATFORM_SKILL_PATHS
from ..config.settings import write_default_config

_SKILLS_PACKAGE = "harness_governance.data.skills"


@dataclass(slots=True)
class InitResult:
    """Result returned to the CLI layer."""

    project_root: Path
    detected_platform: str
    config_path: Path | None
    skill_path: Path | None
    notes: tuple[str, ...] = ()


def detect_platform(project_root: Path) -> str:
    """Best-effort platform detection based on existing dotfiles."""
    for hint, platform in PLATFORM_HINTS:
        if (project_root / hint).exists():
            return platform
    return "claude-code"


def load_skill_template(platform: str) -> str:
    """Load the bundled skill adapter template for ``platform``."""
    resource = resources.files(_SKILLS_PACKAGE).joinpath(f"{platform}.md")
    if not resource.is_file():
        # Fall back to the generic adapter.
        resource = resources.files(_SKILLS_PACKAGE).joinpath("generic.md")
    return resource.read_text(encoding="utf-8")


def write_skill_file(project_root: Path, platform: str) -> Path:
    """Write the per-platform skill adapter; returns the path."""
    rel = PLATFORM_SKILL_PATHS.get(platform, PLATFORM_SKILL_PATHS["generic"])
    target = (project_root / rel).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(load_skill_template(platform), encoding="utf-8")
    return target


@click.command("init")
@click.option(
    "--platform",
    "platform",
    default=None,
    type=click.Choice(sorted(PLATFORM_SKILL_PATHS)),
    help="Override automatic platform detection.",
)
@click.option(
    "--force/--no-force",
    default=False,
    help="Overwrite existing config and skill files.",
)
@click.option(
    "--skip-skill",
    is_flag=True,
    default=False,
    help="Only write .harness/config.toml; skip the per-platform skill adapter.",
)
@click.pass_context
def init_cmd(
    ctx: click.Context,
    platform: str | None,
    force: bool,
    skip_skill: bool,
) -> None:
    """Initialize harness governance in the current project."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd()).resolve()
    detected = platform or detect_platform(project_root)

    config_path = write_default_config(project_root, agent_platform=detected, force=force)
    notes: list[str] = [f"Detected platform: {detected}"]

    skill_path: Path | None = None
    if not skip_skill:
        existing = (project_root / PLATFORM_SKILL_PATHS.get(detected, PLATFORM_SKILL_PATHS["generic"])).resolve()
        if existing.exists() and not force:
            notes.append(f"Skill file already exists at {existing}; use --force to overwrite.")
        else:
            skill_path = write_skill_file(project_root, detected)
            notes.append(f"Wrote skill file: {skill_path}")

    result = InitResult(
        project_root=project_root,
        detected_platform=detected,
        config_path=config_path,
        skill_path=skill_path,
        notes=tuple(notes),
    )

    if ctx.obj.get("json_output"):
        import json

        click.echo(
            json.dumps(
                {
                    "project_root": str(result.project_root),
                    "detected_platform": result.detected_platform,
                    "config_path": str(result.config_path) if result.config_path else None,
                    "skill_path": str(result.skill_path) if result.skill_path else None,
                    "notes": list(result.notes),
                },
                indent=2,
            )
        )
        return

    click.echo(f"Detected: {result.detected_platform}")
    if result.config_path:
        click.echo(f"Created: {result.config_path}")
    if result.skill_path:
        click.echo(f"Created: {result.skill_path}")
    for note in result.notes:
        if note.startswith("Detected platform"):
            continue
        click.echo(f"Note: {note}")
    click.echo("Done. Your agent will now use harness governance for engineering work.")


__all__ = ["init_cmd", "detect_platform", "write_skill_file", "InitResult"]