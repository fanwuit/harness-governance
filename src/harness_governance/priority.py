"""Cross-platform priority enforcement.

Scans all supported agent platform directories for third-party skills
that could hijack entry routing before harness governance runs its
classification.  Provides detect / warn / fix / verify primitives so
``harness check priority`` and ``harness governed-start`` can enforce
entry priority at the filesystem level, not just via prompt instructions.

Platforms
---------
* **directory-based** (claude-code, codex, windsurf) — skills live in
  sibling subdirectories.  Harness governance is ``harness-governance/``;
  competing skills can be renamed with a ``_`` prefix.
* **file-based** (cline, cursor, opencode) — each skill or rule is a
  standalone ``.md`` / ``.mdc`` file in a shared directory.  Competing
  files can be renamed with a ``_`` prefix.
* **agents-md** (qoderwork, generic) — the only instruction surface is
  ``AGENTS.md``.  We cannot rename it, so we strengthen the priority
  override text embedded in the file.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from . import messages
from .config.defaults import PLATFORM_SKILL_PATHS
from .models.schemas import CheckFinding, CheckResult

# ---------------------------------------------------------------------------
# Scan targets per platform
# ---------------------------------------------------------------------------
# Each entry: (root_dir, glob_pattern, is_directory_based, is_agents_md)
#
# *root_dir*     — the platform-specific directory to scan (relative to project root)
# *glob_pattern* — glob used to discover candidate skill / rule files
# *is_directory_based* — True when skills live in sibling dirs (each dir = one skill)
# *is_agents_md* — True when the only target is AGENTS.md (cannot rename)
#
# Values are derived from PLATFORM_SKILL_PATHS and PLATFORM_HINTS in
# :mod:`harness_governance.config.defaults`.

PLATFORM_SCAN_DIRS: dict[str, tuple[str, str, bool, bool]] = {
    "claude-code": (".claude/skills", ".claude/skills/*/SKILL.md", True, False),
    "codex": (".agents/skills", ".agents/skills/*/SKILL.md", True, False),
    "windsurf": (".windsurf/skills", ".windsurf/skills/*/SKILL.md", True, False),
    "opencode": (".opencode/agents", ".opencode/agents/*.md", False, False),
    "cline": (".clinerules", ".clinerules/*.md", False, False),
    "cursor": (".cursor/rules", ".cursor/rules/*.mdc", False, False),
    "qoderwork": ("", "AGENTS.md", False, True),
    "generic": ("", "AGENTS.md", False, True),
}

# The directory / file name that harness governance itself occupies.
HARNESS_SKILL_DIR = "harness-governance"
HARNESS_SKILL_FILE_BASES: frozenset[str] = frozenset(
    {"harness-governance.md", "harness-governance.mdc"}
)

# ---------------------------------------------------------------------------
# Hijack trigger patterns
# ---------------------------------------------------------------------------
# Each tuple: (field_name, compiled_regex, reason_message_id)
# *field_name* is the YAML frontmatter key to match (or "body" for body text).
# *compiled_regex* is a case-insensitive full / partial match.
# *reason_message_id* points into the messages catalog.

_HIJACK_PATTERNS: tuple[tuple[str, re.Pattern, str], ...] = (
    # Frontmatter patterns
    ("alwaysApply", re.compile(r"^\s*true\s*$", re.IGNORECASE), "priority.reason.always_apply"),
    ("description", re.compile(r"before any response", re.IGNORECASE), "priority.reason.before_any_response"),
    ("description", re.compile(r"session.start", re.IGNORECASE), "priority.reason.session_start"),
    ("description", re.compile(r"starting any conversation", re.IGNORECASE), "priority.reason.starting_any_conversation"),
)

# Phrases we also search for in the Markdown body (after the frontmatter).
_BODY_TRIGGER_PHRASES: tuple[str, ...] = (
    "before any response",
    "session start",
    "session-start",
    "starting any conversation",
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class SkillInfo:
    """Parsed metadata about one skill file found during a scan."""

    platform: str
    path: Path  # absolute path
    name: str | None  # from YAML frontmatter 'name', or None
    frontmatter: dict[str, str] = field(default_factory=dict)
    body_preview: str = ""  # first 500 chars of Markdown body


@dataclass(slots=True)
class CompetingSkill:
    """A skill that declares hijack-risk patterns."""

    platform: str
    path: Path  # absolute path
    skill_name: str  # frontmatter 'name' or derived from path
    reasons: tuple[str, ...]  # human-readable (already translated) reason strings


@dataclass(slots=True)
class FixResult:
    """Result of applying a priority fix for one competing skill."""

    platform: str
    path: Path  # original absolute path
    new_path: Path | None = None  # path after fix (None for agents-md platforms)
    action: str = ""  # "rename_dir", "rename_file", "strengthen_agents_md"
    success: bool = False
    detail: str = ""


# ---------------------------------------------------------------------------
# YAML frontmatter parser
# ---------------------------------------------------------------------------


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    """Extract YAML frontmatter from a Markdown document.

    Returns ``(fields, body)`` where *fields* is a flat dictionary of
    ``key: value`` pairs from the ``---`` delimited block and *body* is
    the remaining Markdown text after the closing ``---``.

    Handles only flat ``key: value`` pairs — nested structures and lists
    are silently skipped.  This is intentionally minimal: the frontmatter
    blocks in agent SKILL.md files are always flat.
    """
    stripped = text.lstrip("﻿")  # strip BOM if present
    if not stripped.startswith("---"):
        return {}, stripped

    # Find closing delimiter — must be on its own line.
    end_idx = -1
    for match in re.finditer(r"^---\s*$", stripped, re.MULTILINE):
        if match.start() == 0:
            continue  # skip the opening delimiter
        end_idx = match.start()
        break

    if end_idx < 0:
        # No closing delimiter — take everything after first line as body.
        body_start = stripped.index("\n") + 1 if "\n" in stripped else len(stripped)
        return {}, stripped[body_start:]

    frontmatter_block = stripped[4:end_idx]  # skip past opening "---\n"
    body = stripped[end_idx + len("---\n"):] if end_idx + 4 < len(stripped) else ""

    fields: dict[str, str] = {}
    for line in frontmatter_block.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Only handle flat "key: value" lines.
        colon_idx = line.find(":")
        if colon_idx <= 0:
            continue
        key = line[:colon_idx].strip()
        value = line[colon_idx + 1:].strip()
        # Strip surrounding quotes.
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
            value = value[1:-1]
        # Skip list markers (lines starting with "- " after a key: line).
        if value == "" or value == "|" or value == ">-":
            continue
        fields[key] = value

    return fields, body


# ---------------------------------------------------------------------------
# Platform scanning
# ---------------------------------------------------------------------------


def scan_platform_skills(project_root: Path, platform: str) -> list[SkillInfo]:
    """Find all skill / rule files for *platform* under *project_root*.

    The harness-governance skill itself is always excluded.
    """
    entry = PLATFORM_SCAN_DIRS.get(platform)
    if entry is None:
        return []

    _root_dir, glob_pattern, is_directory_based, is_agents_md = entry

    # agents-md platforms have no separate skill files to scan.
    if is_agents_md:
        return []

    candidates: list[Path] = sorted(project_root.glob(glob_pattern))
    result: list[SkillInfo] = []

    for candidate in candidates:
        # Exclude the harness-governance skill itself.
        if is_directory_based:
            # candidate is like .claude/skills/<name>/SKILL.md
            if candidate.parent.name == HARNESS_SKILL_DIR:
                continue
            skill_name = candidate.parent.name
        else:
            # candidate is like .clinerules/<name>.md
            if candidate.name.lower() in HARNESS_SKILL_FILE_BASES:
                continue
            skill_name = candidate.stem

        try:
            raw = candidate.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        frontmatter, body = parse_frontmatter(raw)
        name = frontmatter.get("name", skill_name)
        body_preview = body[:500]

        result.append(
            SkillInfo(
                platform=platform,
                path=candidate.resolve(),
                name=name,
                frontmatter=frontmatter,
                body_preview=body_preview,
            )
        )

    return result


# ---------------------------------------------------------------------------
# Competing-skill detection
# ---------------------------------------------------------------------------


def detect_competing_skills(project_root: Path) -> list[CompetingSkill]:
    """Scan all platforms and return skills that could hijack entry routing."""
    root = project_root.resolve()
    competing: list[CompetingSkill] = []

    for platform in PLATFORM_SCAN_DIRS:
        for info in scan_platform_skills(root, platform):
            reasons: list[str] = _detect_reasons(info)
            if not reasons:
                continue
            competing.append(
                CompetingSkill(
                    platform=platform,
                    path=info.path,
                    skill_name=info.name or info.path.stem,
                    reasons=tuple(reasons),
                )
            )

    return competing


def _detect_reasons(info: SkillInfo) -> list[str]:
    """Return a list of human-readable reasons why *info* is flagged."""
    reasons: list[str] = []

    # Check YAML frontmatter fields against patterns.
    for field_name, pattern, msg_id in _HIJACK_PATTERNS:
        value = info.frontmatter.get(field_name, "")
        if pattern.search(value):
            reasons.append(messages.t(msg_id))

    # Check body text for trigger phrases (frontmatter-only patterns like
    # alwaysApply don't apply to the body).
    body_lower = info.body_preview.lower()
    for phrase in _BODY_TRIGGER_PHRASES:
        if phrase in body_lower:
            reasons.append(
                messages.t("priority.reason.body_trigger", phrase=phrase)
            )
            break  # one body match is enough

    return reasons


# ---------------------------------------------------------------------------
# Priority check (returns standard CheckResult)
# ---------------------------------------------------------------------------


def check_priority(project_root: Path) -> CheckResult:
    """Top-level priority check — returns a :class:`CheckResult`.

    Designed to be called identically to :func:`check_routing`,
    :func:`check_packets`, etc.
    """
    competing = detect_competing_skills(project_root)
    platforms_affected: set[str] = {c.platform for c in competing}

    if not competing:
        return CheckResult(
            check="priority",
            passed=True,
            findings=(),
            inspected=len(PLATFORM_SCAN_DIRS),
        )

    findings = tuple(
        CheckFinding(
            check="priority",
            target=_rel_path(c.path, project_root),
            level="warning",
            message=messages.t(
                "priority.finding_reason",
                path=_rel_path(c.path, project_root),
                reason="; ".join(c.reasons),
            ),
        )
        for c in competing
    )

    return CheckResult(
        check="priority",
        passed=False,
        findings=findings,
        inspected=len(PLATFORM_SCAN_DIRS),
    )


# ---------------------------------------------------------------------------
# Fix application
# ---------------------------------------------------------------------------


def apply_fix(
    project_root: Path,
    competing: CompetingSkill,
) -> FixResult:
    """Apply a platform-specific fix to neutralise one competing skill.

    Directory-based platforms: rename the parent directory with a ``_`` prefix.
    File-based platforms: rename the file with a ``_`` prefix.
    AGENTS.md platforms: strengthen the priority override text (handled by
    ``apply_all_fixes`` via the init module's marker mechanism).
    """
    root = project_root.resolve()
    entry = PLATFORM_SCAN_DIRS.get(competing.platform)
    if entry is None:
        return FixResult(
            platform=competing.platform,
            path=competing.path,
            success=False,
            detail=f"Unknown platform: {competing.platform}",
        )

    _root_dir, _glob, is_directory_based, is_agents_md = entry

    if is_agents_md:
        # AGENTS.md fix is handled by apply_all_fixes (needs the init helpers).
        return FixResult(
            platform=competing.platform,
            path=competing.path,
            action="strengthen_agents_md",
            success=True,
            detail="AGENTS.md priority override will be strengthened.",
        )

    target = competing.path.resolve()
    if not target.exists():
        return FixResult(
            platform=competing.platform,
            path=target,
            success=False,
            detail="File no longer exists.",
        )

    if is_directory_based:
        # Rename the parent directory: .claude/skills/superpowers-foo/ -> _superpowers-foo/
        parent = target.parent
        new_name = f"_{parent.name}"
        new_parent = parent.with_name(new_name)
        return _do_rename(
            competing.platform, parent, new_parent, "rename_dir"
        )
    else:
        # Rename the file: .clinerules/custom.md -> _custom.md
        new_name = f"_{target.name}"
        new_path = target.with_name(new_name)
        return _do_rename(
            competing.platform, target, new_path, "rename_file"
        )


def _do_rename(
    platform: str,
    source: Path,
    dest: Path,
    action: str,
) -> FixResult:
    """Attempt a rename; return a FixResult regardless of outcome."""
    if not source.exists():
        return FixResult(
            platform=platform, path=source,
            success=False, detail="Source no longer exists.",
        )

    if dest.exists():
        return FixResult(
            platform=platform, path=source, new_path=dest,
            action=action, success=False,
            detail=messages.t(
                "priority.fix_skipped_exists",
                path=_short_path(source), new_path=_short_path(dest),
            ),
        )

    try:
        source.rename(dest)
    except OSError as exc:
        return FixResult(
            platform=platform, path=source,
            action=action, success=False, detail=str(exc),
        )

    return FixResult(
        platform=platform, path=source, new_path=dest,
        action=action, success=True,
        detail=messages.t(
            "priority.fix_applied",
            action=action, path=_short_path(source), new_path=_short_path(dest),
        ),
    )


def apply_all_fixes(
    project_root: Path,
    competing_skills: list[CompetingSkill],
) -> list[FixResult]:
    """Apply fixes for every competing skill; deduplicate AGENTS.md fixes."""
    results: list[FixResult] = []
    agents_md_done = False

    for c in competing_skills:
        entry = PLATFORM_SCAN_DIRS.get(c.platform)
        is_agents_md = entry[3] if entry else False

        if is_agents_md:
            if not agents_md_done:
                results.append(_strengthen_agents_md(project_root))
                agents_md_done = True
        else:
            results.append(apply_fix(project_root, c))

    return results


def _strengthen_agents_md(project_root: Path) -> FixResult:
    """Ensure AGENTS.md contains the strengthened priority override block.

    Delegates to the init module's ``_build_agents_triggers_block`` and
    ``_ensure_agents_md_triggers`` so there is exactly one author for the
    block text.
    """
    from .commands.init import _build_agents_triggers_block
    from .commands.init import _ensure_agents_md_triggers

    try:
        path = _ensure_agents_md_triggers(
            project_root, skill_ref="", force=True,
        )
        return FixResult(
            platform="generic/qoderwork",
            path=path,
            action="strengthen_agents_md",
            success=True,
            detail="AGENTS.md strengthened with entry priority override.",
        )
    except Exception as exc:
        return FixResult(
            platform="generic/qoderwork",
            path=project_root / "AGENTS.md",
            action="strengthen_agents_md",
            success=False,
            detail=str(exc),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _rel_path(abs_path: Path, project_root: Path) -> str:
    """Return a forward-slash relative path string, or the absolute path."""
    try:
        rel = abs_path.resolve().relative_to(project_root.resolve())
        return rel.as_posix()
    except ValueError:
        return abs_path.as_posix()


def _short_path(p: Path) -> str:
    """Return the last 2-3 segments of a path for display."""
    parts = p.parts
    if len(parts) <= 3:
        return str(p)
    return str(Path(*parts[-3:]))


__all__ = [
    "SkillInfo",
    "CompetingSkill",
    "FixResult",
    "PLATFORM_SCAN_DIRS",
    "HARNESS_SKILL_DIR",
    "parse_frontmatter",
    "scan_platform_skills",
    "detect_competing_skills",
    "check_priority",
    "apply_fix",
    "apply_all_fixes",
]
