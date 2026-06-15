"""``harness init`` command.

Writes ``.harness/config.toml`` and a per-platform skill adapter so the
user's AI agent can discover and use the governance CLI. Idempotent:
re-running without ``--force`` is a no-op.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

import click

from ..config.defaults import ENV_HINTS, PLATFORM_HINTS, PLATFORM_SKILL_PATHS
from ..config.settings import write_default_config
from ..messages import bilingual

_SKILLS_PACKAGE = "harness_governance.data.skills"

_NEXT_MD_TEMPLATE = """\
<!-- Harness Governance Queue (NEXT.md)

Status labels: [ready] [active] [blocked] [done] [not-now]
Fields:  - Layer: <layer-name>
         - Change: <change-id>       (links to docs/changes/<id>/)
         Role: <role-name>
         Verification command: <cmd>
         Done when: <criteria>
         Forbidden shortcut: <what to avoid>

Uncomment the example below or replace with your own queue items.
-->

<!--
[ready] Example: implement feature X
- Layer: implementation
- Change: feature-x
Role: Implementer
Verification command: npm test
Done when: feature X works end-to-end
Forbidden shortcut: no mock data in production
-->
"""


def _ensure_gitignore_entry(project_root: Path, pattern: str) -> None:
    """Append *pattern* to ``.gitignore`` if not already present.

    Creates the file when it does not exist.  Does nothing when the
    pattern (or a leading-slash variant) is already listed.
    """
    gitignore = project_root / ".gitignore"
    if gitignore.is_file():
        existing = gitignore.read_text(encoding="utf-8").splitlines()
        if any(line.strip() in (pattern, f"/{pattern}") for line in existing):
            return
        separator = "\n" if existing and existing[-1].strip() else ""
        gitignore.write_text(
            gitignore.read_text(encoding="utf-8") + separator + pattern + "\n",
            encoding="utf-8",
        )
    else:
        gitignore.write_text(pattern + "\n", encoding="utf-8")


@dataclass(slots=True)
class InitResult:
    """Result returned to the CLI layer."""

    project_root: Path
    detected_platform: str
    config_path: Path | None
    skill_path: Path | None
    notes: tuple[str, ...] = ()


def detect_platform(project_root: Path, *, env: dict[str, str] | None = None) -> str:
    """Best-effort platform detection.

    Lookup order:

    1. Environment variables in :data:`ENV_HINTS` (env wins over dotfiles).
    2. Repo dotfiles in :data:`PLATFORM_HINTS`.
    3. Fallback to ``claude-code``.
    """
    env_vars = env if env is not None else os.environ
    for var, platform in ENV_HINTS:
        if env_vars.get(var):
            return platform
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
@click.option(
    "--no-detect",
    is_flag=True,
    default=False,
    help="Skip auto-detection; require --platform to be set explicitly.",
)
@click.option(
    "--minimal",
    is_flag=True,
    default=False,
    help="Only write .harness/config.toml; skip skill adapter, NEXT.md, and scaffolding.",
)
@click.pass_context
def init_cmd(
    ctx: click.Context,
    platform: str | None,
    force: bool,
    skip_skill: bool,
    no_detect: bool,
    minimal: bool,
) -> None:
    """Initialize harness governance in the current project."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd()).resolve()
    if no_detect and not platform:
        raise click.UsageError(
            "--no-detect requires --platform to be set explicitly."
        )
    detected = platform or detect_platform(project_root)

    # --minimal implies skip_skill and no scaffolding
    if minimal:
        skip_skill = True

    config_path = write_default_config(project_root, agent_platform=detected, force=force)
    notes: list[str] = [f"Detected platform: {detected}"]

    skill_path: Path | None = None
    if not skip_skill:
        existing = (project_root / PLATFORM_SKILL_PATHS.get(detected, PLATFORM_SKILL_PATHS["generic"])).resolve()
        if existing.exists() and not force:
            notes.append(bilingual("init.skill_exists", path=str(existing)))
        else:
            skill_path = write_skill_file(project_root, detected)
            notes.append(bilingual("init.skill_created", path=str(skill_path)))

    # --- Scaffolding: NEXT.md + docs/changes/ (skipped in --minimal mode) ---
    if not minimal:
        from ..config.defaults import DEFAULT_CHANGES_ROOT, DEFAULT_QUEUE_FILE

        next_path = (project_root / DEFAULT_QUEUE_FILE).resolve()
        if not next_path.exists():
            next_path.write_text(_NEXT_MD_TEMPLATE, encoding="utf-8")
            notes.append(f"Created {next_path}")

        changes_path = (project_root / DEFAULT_CHANGES_ROOT).resolve()
        changes_path.mkdir(parents=True, exist_ok=True)

        # --- .gitignore: NEXT.md is personal, not version-controlled ---
        _ensure_gitignore_entry(project_root, "NEXT.md")

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

    if minimal:
        click.echo(bilingual("init.detected", platform=result.detected_platform))
        if result.config_path:
            click.echo(bilingual("init.config_created", path=str(result.config_path)))
        click.echo(bilingual("init.minimal_done"))
        return

    click.echo(bilingual("init.detected", platform=result.detected_platform))
    if result.config_path:
        click.echo(bilingual("init.config_created", path=str(result.config_path)))
    if result.skill_path:
        click.echo(bilingual("init.skill_created", path=str(result.skill_path)))
    for note in result.notes:
        if note.startswith("Detected platform"):
            continue
        click.echo(f"Note: {note}")
    click.echo(bilingual("init.done"))


__all__ = ["init_cmd", "detect_platform", "write_skill_file", "InitResult"]