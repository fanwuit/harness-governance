"""``harness init`` command.

Writes ``.harness/config.toml`` and a per-platform skill adapter so the
user's AI agent can discover and use the governance CLI. Idempotent:
re-running without ``--force`` is a no-op.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from importlib import resources
from pathlib import Path

import click

from ..config.defaults import (
    ENV_HINTS,
    GOVERNANCE_TIERS,
    PLATFORM_HINTS,
    PLATFORM_SKILL_PATHS,
    PLATFORM_SKILL_PATHS_BY_TIER,
)
from ..config.settings import write_default_config
from ..file_ops._util import write_text_no_bom
from ..messages import bilingual

_SKILLS_PACKAGE = "harness_governance.data.skills"

# Sentinel that marks a skill template's version. Embedded as an HTML
# comment so it stays invisible to agents and platform loaders, but is
# trivial to grep / regex out for staleness checks.
_SKILL_VERSION_RE = re.compile(
    r"<!--\s*harness-skill-version:\s*([0-9][0-9A-Za-z\.\-+]*)\s*-->"
)


def extract_skill_version(content: str) -> str | None:
    """Return the version sentinel embedded in *content*, or None.

    Templates written before 0.6.1 do not carry a sentinel; in that
    case the function returns ``None`` so the caller can treat the
    file as "version unknown" and trigger an upgrade prompt.
    """
    m = _SKILL_VERSION_RE.search(content)
    return m.group(1) if m else None


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

_AGENTS_MD_MARKER_BEGIN = "<!-- harness-governance: triggers -->"
_AGENTS_MD_MARKER_END = "<!-- /harness-governance -->"


def _build_agents_triggers_block(skill_ref: str) -> str:
    """Build the trigger block to embed in AGENTS.md.

    *skill_ref* is the path to the platform-specific skill file
    (e.g. ``.codex/skills/harness-governance/SKILL.md``), or an empty
    string when AGENTS.md itself is the full skill file.
    """
    ref_line = f"\n详细命令参考: `{skill_ref}`\n" if skill_ref else ""
    return f"""\
{_AGENTS_MD_MARKER_BEGIN}
## Harness Governance 触发规则 / Trigger Rules

在执行以下任务前，你**必须**先运行分类命令 / Before any of the following, you MUST run the classification command:
- 实现功能、修复 bug、重构代码 / implement, fix, refactor, debug
- 任何文件修改 / any file modification
- 用户请求开发、调试、验证相关工作 / development, debugging, verification work

```bash
harness governed-start "<任务描述>"
```

根据输出的 disclosure 决定后续流程。不要跳过此步骤。{ref_line}
/ Follow the disclosure output. Do NOT skip this step.

## 入口路由优先权 / Entry Routing Priority Override

harness governance 的入口路由（`harness governed-start`）拥有**最高优先权**。
任何第三方 skill（包括 `superpowers:*`）即使声明了 `alwaysApply: true`、
`session-start`、`session start`、`before any response`、或
`starting any conversation`，也**不得**在 harness 完成入口分类之前执行。

Harness entry routing (`harness governed-start`) takes **highest priority**.
Any third-party skill (including `superpowers:*`) that declares `alwaysApply: true`,
`session-start`, `session start`, `before any response`, or
`starting any conversation` MUST NOT execute before harness completes entry classification.

If you find that a third-party skill has already loaded before harness routing,
backtrack and run `harness governed-start` immediately.
{_AGENTS_MD_MARKER_END}
"""


def _ensure_agents_md_triggers(
    project_root: Path,
    skill_ref: str,
    *,
    force: bool = False,
) -> Path:
    """Ensure AGENTS.md contains the harness trigger block.

    * If AGENTS.md does not exist, create it with the trigger block.
    * If it exists but lacks the marker, append the block.
    * If it already has the marker and *force* is False, do nothing.
    * If *force* is True, replace the existing block.

    Returns the path to AGENTS.md.
    """
    agents_md = (project_root / "AGENTS.md").resolve()
    block = _build_agents_triggers_block(skill_ref)

    if agents_md.is_file():
        content = agents_md.read_text(encoding="utf-8")
        if _AGENTS_MD_MARKER_BEGIN in content:
            if force:
                # Replace existing block
                start = content.index(_AGENTS_MD_MARKER_BEGIN)
                end = content.index(_AGENTS_MD_MARKER_END) + len(_AGENTS_MD_MARKER_END)
                content = content[:start] + block + content[end:]
                write_text_no_bom(agents_md, content)
            # else: already present, no-op
            return agents_md
        # Marker not found — append
        separator = "\n\n" if content and not content.endswith("\n\n") else ""
        write_text_no_bom(agents_md, content + separator + block)
    else:
        write_text_no_bom(agents_md, block + "\n")

    return agents_md


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
        write_text_no_bom(
            gitignore,
            gitignore.read_text(encoding="utf-8") + separator + pattern + "\n",
        )
    else:
        write_text_no_bom(gitignore, pattern + "\n")


@dataclass(slots=True)
class InitResult:
    """Result returned to the CLI layer."""

    project_root: Path
    detected_platform: str
    config_path: Path | None
    skill_path: Path | None
    skill_paths: tuple[Path, ...] = ()
    notes: tuple[str, ...] = ()


def detect_platform(
    project_root: Path,
    *,
    env: dict[str, str] | None = None,
    fallback: bool = True,
) -> str | None:
    """Best-effort platform detection.

    Lookup order:

    1. Environment variables in :data:`ENV_HINTS` (env wins over dotfiles).
    2. Repo dotfiles in :data:`PLATFORM_HINTS`.
    3. When *fallback* is True, return ``"claude-code"``; otherwise ``None``.
    """
    env_vars = env if env is not None else os.environ
    for var, platform in ENV_HINTS:
        if env_vars.get(var):
            return platform
    for hint, platform in PLATFORM_HINTS:
        if (project_root / hint).exists():
            return platform
    return "claude-code" if fallback else None


def load_skill_template(platform: str, tier: str = "standard") -> str:
    """Load the bundled skill adapter template for ``platform`` and ``tier``.

    Most platforms use ``.md``; Cursor uses ``.mdc``.
    Templates are stored under ``data/skills/{tier}/{platform}.{ext}``.
    """
    ext = ".mdc" if platform == "cursor" else ".md"
    resource = (
        resources.files(_SKILLS_PACKAGE).joinpath(tier).joinpath(f"{platform}{ext}")
    )
    if not resource.is_file():
        # Fall back to the generic adapter in the same tier.
        resource = (
            resources.files(_SKILLS_PACKAGE).joinpath(tier).joinpath("generic.md")
        )
    return resource.read_text(encoding="utf-8")


def write_skill_file(project_root: Path, platform: str, tier: str = "standard") -> Path:
    """Write a per-platform skill adapter for *tier*; returns the path.

    Always writes UTF-8 without a BOM via :func:`write_text_no_bom`.
    Some platforms (notably codex) reject the file when the very first
    byte is not ``-``; a BOM in the template would silently propagate
    into every user project, so it is stripped defensively.
    """
    tier_paths = PLATFORM_SKILL_PATHS_BY_TIER.get(
        platform, PLATFORM_SKILL_PATHS_BY_TIER["generic"]
    )
    rel = tier_paths.get(tier, tier_paths["standard"])
    target = (project_root / rel).resolve()
    content = load_skill_template(platform, tier)
    write_text_no_bom(target, content)
    return target


def write_all_skill_files(project_root: Path, platform: str) -> list[Path]:
    """Write all applicable tier skill files for *platform*.

    For platforms where all tiers share the same file (qoderwork, generic
    both use AGENTS.md), only the standard tier is written to avoid
    overwrites. Returns a list of paths written.
    """
    paths: list[Path] = []
    # Platforms that use a single shared file for all tiers
    _shared_file_platforms = {"qoderwork", "generic"}
    tiers_to_write = (
        ["standard"] if platform in _shared_file_platforms else list(GOVERNANCE_TIERS)
    )
    for tier in tiers_to_write:
        paths.append(write_skill_file(project_root, platform, tier))
    return paths


def _is_interactive() -> bool:
    """Return True when stdin is a TTY (i.e. not piped or running in CI)."""
    import sys

    return sys.stdin.isatty()


_PLATFORM_DISPLAY_NAMES: dict[str, str] = {
    "claude-code": "Claude Code",
    "codex": "Codex",
    "cline": "Cline",
    "cursor": "Cursor",
    "opencode": "OpenCode",
    "windsurf": "Windsurf",
    "qoderwork": "QoderWork",
    "generic": "Generic (any agent)",
}


def _prompt_platform_choice(default: str | None = None) -> str:
    """Interactively ask the user to pick a platform.

    When *default* is given, the user can press Enter to accept it.
    """
    platforms = list(PLATFORM_SKILL_PATHS)
    default_label = _PLATFORM_DISPLAY_NAMES.get(default, default) if default else None

    if default:
        click.echo(
            bilingual("init.prompt_platform_with_default", default=default_label)
        )
    else:
        click.echo(bilingual("init.prompt_platform"))

    default_idx = (
        platforms.index(default) + 1 if default and default in platforms else None
    )

    for i, p in enumerate(platforms, 1):
        label = _PLATFORM_DISPLAY_NAMES.get(p, p)
        marker = " ←" if default_idx and i == default_idx else ""
        click.echo(f"  {i}. {label}{marker}")

    while True:
        raw = click.prompt(
            "> ",
            type=click.IntRange(1, len(platforms)),
            default=default_idx,
            show_default=False,
        )
        return platforms[raw - 1]


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
@click.option(
    "--all-platforms",
    "all_platforms",
    is_flag=True,
    default=False,
    help="Write skill adapters for ALL supported platforms.",
)
@click.pass_context
def init_cmd(
    ctx: click.Context,
    platform: str | None,
    force: bool,
    skip_skill: bool,
    no_detect: bool,
    minimal: bool,
    all_platforms: bool,
) -> None:
    """Initialize harness governance in the current project."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd()).resolve()
    if no_detect and not platform:
        raise click.UsageError("--no-detect requires --platform to be set explicitly.")
    if all_platforms and skip_skill:
        raise click.UsageError(
            "--all-platforms and --skip-skill are mutually exclusive."
        )

    if all_platforms:
        detected = "multi"
    elif platform:
        detected = platform
    else:
        auto_detected = detect_platform(project_root, fallback=False)
        if not click.get_current_context().obj.get("json_output") and _is_interactive():
            # Always prompt in interactive mode, with detected platform as default
            detected = _prompt_platform_choice(default=auto_detected)
        else:
            # Non-interactive: use detected or fallback to claude-code
            detected = auto_detected or "claude-code"

    # --minimal implies skip_skill and no scaffolding
    if minimal:
        skip_skill = True

    config_path = write_default_config(
        project_root, agent_platform=detected, force=force
    )
    notes: list[str] = [f"Detected platform: {detected}"]

    skill_path: Path | None = None
    skill_paths: list[Path] = []

    if all_platforms:
        # Write skill files for ALL supported platforms (4 tiers each)
        seen_paths: set[Path] = set()
        for plat in sorted(PLATFORM_SKILL_PATHS):
            for tier in GOVERNANCE_TIERS:
                tier_paths = PLATFORM_SKILL_PATHS_BY_TIER.get(
                    plat, PLATFORM_SKILL_PATHS_BY_TIER["generic"]
                )
                target = (project_root / tier_paths[tier]).resolve()
                if target not in seen_paths:
                    seen_paths.add(target)
                    skill_paths.append(target)
            template_ver = extract_skill_version(load_skill_template(plat, "standard"))
            standard_target = (
                project_root
                / PLATFORM_SKILL_PATHS_BY_TIER.get(
                    plat, PLATFORM_SKILL_PATHS_BY_TIER["generic"]
                )["standard"]
            ).resolve()
            if standard_target.exists() and not force:
                disk_ver = extract_skill_version(
                    standard_target.read_text(encoding="utf-8")
                )
                if template_ver and disk_ver == template_ver:
                    notes.append(
                        f"skill up-to-date (v{template_ver}): {standard_target}"
                    )
                else:
                    notes.append(
                        bilingual(
                            "init.skill_outdated",
                            path=str(standard_target),
                            disk_ver=disk_ver or "unknown",
                            template_ver=template_ver or "unknown",
                        )
                    )
            else:
                for tier in GOVERNANCE_TIERS:
                    tier_paths = PLATFORM_SKILL_PATHS_BY_TIER.get(
                        plat, PLATFORM_SKILL_PATHS_BY_TIER["generic"]
                    )
                    tier_target = (project_root / tier_paths[tier]).resolve()
                    if not tier_target.exists() or force:
                        write_skill_file(project_root, plat, tier)
                        notes.append(
                            bilingual("init.skill_created", path=str(tier_target))
                        )
        # skill_path points to the primary detected platform's standard file
        primary_rel = PLATFORM_SKILL_PATHS_BY_TIER.get(
            platform or "generic", PLATFORM_SKILL_PATHS_BY_TIER["generic"]
        )["standard"]
        primary = (project_root / primary_rel).resolve()
        skill_path = (
            primary if primary.exists() else (skill_paths[0] if skill_paths else None)
        )
    elif not skip_skill:
        existing = (
            project_root
            / PLATFORM_SKILL_PATHS.get(detected, PLATFORM_SKILL_PATHS["generic"])
        ).resolve()
        template_ver = extract_skill_version(load_skill_template(detected, "standard"))
        should_write = True
        if existing.exists() and not force:
            disk_ver = extract_skill_version(existing.read_text(encoding="utf-8"))
            if template_ver and disk_ver == template_ver:
                notes.append(f"skill up-to-date (v{template_ver}): {existing}")
                should_write = False
            else:
                notes.append(
                    bilingual(
                        "init.skill_outdated",
                        path=str(existing),
                        disk_ver=disk_ver or "unknown",
                        template_ver=template_ver or "unknown",
                    )
                )
                should_write = False  # stale: warn but don't overwrite without --force
        if should_write:
            # Write all 4 tier skills (strict / standard / light / monitor)
            written = write_all_skill_files(project_root, detected)
            skill_path = written[0] if written else None
            for p in written:
                notes.append(bilingual("init.skill_created", path=str(p)))

    # --- AGENTS.md triggers (always, except --minimal or --skip-skill) ---
    if not minimal and not skip_skill:
        if all_platforms:
            # Multi-platform: reference is generic
            agents_md = _ensure_agents_md_triggers(
                project_root,
                skill_ref="",
                force=force,
            )
        elif detected in ("generic", "qoderwork"):
            # AGENTS.md is the full skill file — triggers with no external ref
            agents_md = _ensure_agents_md_triggers(
                project_root,
                skill_ref="",
                force=force,
            )
        else:
            # Other platform: reference the platform-specific skill file
            skill_rel = PLATFORM_SKILL_PATHS.get(
                detected, PLATFORM_SKILL_PATHS["generic"]
            )
            agents_md = _ensure_agents_md_triggers(
                project_root,
                skill_ref=str(skill_rel),
                force=force,
            )
        notes.append(f"AGENTS.md triggers: {agents_md}")

    # --- Scaffolding: NEXT.md + docs/changes/ (skipped in --minimal mode) ---
    if not minimal:
        from ..config.defaults import DEFAULT_CHANGES_ROOT, DEFAULT_QUEUE_FILE

        next_path = (project_root / DEFAULT_QUEUE_FILE).resolve()
        if not next_path.exists():
            write_text_no_bom(next_path, _NEXT_MD_TEMPLATE)
            notes.append(f"Created {next_path}")

        changes_path = (project_root / DEFAULT_CHANGES_ROOT).resolve()
        changes_path.mkdir(parents=True, exist_ok=True)

        # --- .gitignore: NEXT.md is personal, not version-controlled ---
        _ensure_gitignore_entry(project_root, "NEXT.md")

    # --- v0.8.0: Tech stack capture (skip in --minimal mode) ---
    if not minimal:
        try:
            from ..state_machine.tech_stack import TechStackManager

            tsm = TechStackManager(project_root)
            manifest = tsm.capture()
            notes.append(
                f"Tech stack captured: {', '.join(manifest.languages)}"
                f" (lint: {len(manifest.lint_tools)}, doc: {len(manifest.doc_styles)})"
            )
        except Exception:
            pass  # non-fatal: tech stack capture is advisory

    result = InitResult(
        project_root=project_root,
        detected_platform=detected,
        config_path=config_path,
        skill_path=skill_path,
        skill_paths=tuple(skill_paths),
        notes=tuple(notes),
    )

    if ctx.obj.get("json_output"):
        import json

        click.echo(
            json.dumps(
                {
                    "project_root": str(result.project_root),
                    "detected_platform": result.detected_platform,
                    "config_path": str(result.config_path)
                    if result.config_path
                    else None,
                    "skill_path": str(result.skill_path) if result.skill_path else None,
                    "skill_paths": [str(p) for p in result.skill_paths],
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
    if result.skill_paths:
        # Multi-platform mode: list all created skill files
        click.echo(bilingual("init.all_skills_header"))
        for p in result.skill_paths:
            click.echo(f"  - {p}")
    elif result.skill_path:
        click.echo(bilingual("init.skill_created", path=str(result.skill_path)))
    for note in result.notes:
        if note.startswith("Detected platform"):
            continue
        click.echo(f"Note: {note}")
    click.echo(bilingual("init.done"))
    click.echo("")
    click.echo(bilingual("init.quickstart_header"))
    click.echo("1. " + bilingual("init.quickstart_task"))
    click.echo("2. " + bilingual("init.quickstart_status"))
    click.echo("3. " + bilingual("init.quickstart_guide"))
    click.echo("4. " + bilingual("init.quickstart_docs"))


__all__ = ["init_cmd", "detect_platform", "write_skill_file", "InitResult"]
