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
    "claude-code": Path(".claude/skills/harness-governance/SKILL.md"),
    "codex": Path(".codex/skills/harness-governance/SKILL.md"),
    "cline": Path(".clinerules/harness-governance.md"),
    "cursor": Path(".cursor/rules/harness-governance.md"),
    "opencode": Path(".opencode/agents/harness-governance.md"),
    "qoderwork": Path("AGENTS.md"),
    "generic": Path("AGENTS.md"),
}

# Detection priority: first match wins.
PLATFORM_HINTS: tuple[tuple[str, str], ...] = (
    (".claude", "claude-code"),
    (".codex", "codex"),
    (".clinerules", "cline"),
    (".cursor", "cursor"),
    (".qoderwork", "qoderwork"),
    (".opencode", "opencode"),
    ("AGENTS.md", "generic"),
)

# Env vars that hint at a specific platform regardless of repo dotfiles.
ENV_HINTS: tuple[tuple[str, str], ...] = (
    ("CLAUDE_CODE", "claude-code"),
    ("CODEX_HOME", "codex"),
    ("CLINE_SESSION", "cline"),
    ("CURSOR_TRACE_ID", "cursor"),
    ("QODERWORK_SESSION", "qoderwork"),
)