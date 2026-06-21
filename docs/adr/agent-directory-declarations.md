# ADR: Agent Directory Capability Declarations

## Decision

Agent platforms declare model candidates in a tiers-json declaration file placed in their
well-known config directory (`.claude/`, `.agents/`, `.opencode/`, etc.),
not in `.harness/config.toml`.

## Rationale

Harness core must remain platform-neutral and never encode model rankings.
Each agent platform knows its own models best. Putting declarations in
per-agent directories keeps the concern local to each platform and allows
projects to mix agents without central coordination.

## Consequences

- Harness core discovers declarations at runtime via directory scan
- No declaration = platform-generic fallback behavior
- Conflicts resolved by directory priority: `.claude/` > `.agents/` > `.opencode/` > etc.
