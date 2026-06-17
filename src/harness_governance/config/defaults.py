"""Default path and constant values.

These are the defaults that ship with the package. Real projects can
override them in ``.harness/config.toml``; :mod:`.settings` is
responsible for merging the defaults with the on-disk file.
"""

from __future__ import annotations

from pathlib import Path

# Default location of the project-level config written by
# ``harness init`` and read by every other command.
DEFAULT_HARNESS_DIR = Path(".harness")
DEFAULT_CONFIG_FILE = DEFAULT_HARNESS_DIR / "config.toml"

# Markdown file conventions documented in plan.md.
DEFAULT_QUEUE_FILE = Path("NEXT.md")
DEFAULT_CHANGES_ROOT = Path("docs/changes")
DEFAULT_PLANNING_ROOT = Path(".planning")
DEFAULT_CHECKPOINT_FILE = DEFAULT_HARNESS_DIR / "run-checkpoint.md"
DEFAULT_STATUS_FILE = DEFAULT_HARNESS_DIR / "status.md"
DEFAULT_STATUS_JSON = DEFAULT_HARNESS_DIR / "status.json"
DEFAULT_INVOCATIONS_LOG = DEFAULT_HARNESS_DIR / "invocations.ndjson"
DEFAULT_SESSIONS_DIR = DEFAULT_HARNESS_DIR / "sessions"

# Status values used by change packets. ``check-change-packet.mjs``
# rejects anything outside this set.
ALLOWED_PACKET_STATUSES: frozenset[str] = frozenset(
    {"draft", "ready", "active", "blocked", "done", "archived"}
)

# Templates required for a valid change packet, in canonical order.
REQUIRED_PACKET_FILES: tuple[str, ...] = (
    "proposal.md",
    "design.md",
    "tasks.md",
    "contracts.md",
    "verification.md",
)

# Skill path templates per platform. ``harness init`` uses these to
# figure out where to write the per-platform SKILL.md adapter.
PLATFORM_SKILL_PATHS: dict[str, Path] = {
    "claude-code": Path(".claude/skills/harness-governance-standard/SKILL.md"),
    "codex": Path(".agents/skills/harness-governance-standard/SKILL.md"),
    "cline": Path(".clinerules/harness-governance-standard.md"),
    "cursor": Path(".cursor/rules/harness-governance-standard.mdc"),
    "opencode": Path(".opencode/agents/harness-governance-standard.md"),
    "windsurf": Path(".windsurf/skills/harness-governance-standard/SKILL.md"),
    "qoderwork": Path("AGENTS.md"),
    "generic": Path("AGENTS.md"),
}

# Per-tier skill paths (strict / standard / light).
# ``harness init`` writes three skill files per platform using these paths.
PLATFORM_SKILL_PATHS_BY_TIER: dict[str, dict[str, Path]] = {
    "claude-code": {
        "strict": Path(".claude/skills/harness-governance-strict/SKILL.md"),
        "standard": Path(".claude/skills/harness-governance-standard/SKILL.md"),
        "light": Path(".claude/skills/harness-governance-light/SKILL.md"),
        "monitor": Path(".claude/skills/harness-governance-monitor/SKILL.md"),
    },
    "codex": {
        "strict": Path(".agents/skills/harness-governance-strict/SKILL.md"),
        "standard": Path(".agents/skills/harness-governance-standard/SKILL.md"),
        "light": Path(".agents/skills/harness-governance-light/SKILL.md"),
        "monitor": Path(".agents/skills/harness-governance-monitor/SKILL.md"),
    },
    "cline": {
        "strict": Path(".clinerules/harness-governance-strict.md"),
        "standard": Path(".clinerules/harness-governance-standard.md"),
        "light": Path(".clinerules/harness-governance-light.md"),
        "monitor": Path(".clinerules/harness-governance-monitor.md"),
    },
    "cursor": {
        "strict": Path(".cursor/rules/harness-governance-strict.mdc"),
        "standard": Path(".cursor/rules/harness-governance-standard.mdc"),
        "light": Path(".cursor/rules/harness-governance-light.mdc"),
        "monitor": Path(".cursor/rules/harness-governance-monitor.mdc"),
    },
    "opencode": {
        "strict": Path(".opencode/agents/harness-governance-strict.md"),
        "standard": Path(".opencode/agents/harness-governance-standard.md"),
        "light": Path(".opencode/agents/harness-governance-light.md"),
        "monitor": Path(".opencode/agents/harness-governance-monitor.md"),
    },
    "windsurf": {
        "strict": Path(".windsurf/skills/harness-governance-strict/SKILL.md"),
        "standard": Path(".windsurf/skills/harness-governance-standard/SKILL.md"),
        "light": Path(".windsurf/skills/harness-governance-light/SKILL.md"),
        "monitor": Path(".windsurf/skills/harness-governance-monitor/SKILL.md"),
    },
    "qoderwork": {
        "strict": Path("AGENTS.md"),
        "standard": Path("AGENTS.md"),
        "light": Path("AGENTS.md"),
        "monitor": Path("AGENTS.md"),
    },
    "generic": {
        "strict": Path("AGENTS.md"),
        "standard": Path("AGENTS.md"),
        "light": Path("AGENTS.md"),
        "monitor": Path("AGENTS.md"),
    },
}

# Backward-compatible tier list for iteration.
GOVERNANCE_TIERS: tuple[str, ...] = ("strict", "standard", "light", "monitor")

# Detection priority: first match wins.
PLATFORM_HINTS: tuple[tuple[str, str], ...] = (
    (".claude", "claude-code"),
    (".agents", "codex"),
    (".clinerules", "cline"),
    (".cursor", "cursor"),
    (".qoderwork", "qoderwork"),
    (".opencode", "opencode"),
    (".windsurf", "windsurf"),
)

# Env vars that hint at a specific platform regardless of repo dotfiles.
ENV_HINTS: tuple[tuple[str, str], ...] = (
    ("CLAUDE_CODE", "claude-code"),
    ("CODEX_HOME", "codex"),
    ("CLINE_SESSION", "cline"),
    ("CURSOR_TRACE_ID", "cursor"),
    ("QODERWORK_SESSION", "qoderwork"),
    ("OPENCODE_SESSION", "opencode"),
    ("WINDSURF_SESSION", "windsurf"),
)
