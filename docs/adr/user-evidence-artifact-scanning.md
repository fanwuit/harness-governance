# ADR: User-Evidence Artifact Scanning (v2)

## Decision

Enhance `harness check user-evidence` with artifact-level scanning via a
new `src/harness_governance/commands/evidence_scanner.py` module that parses
Playwright trace zips, HAR HTTP archives, and test source files for forbidden
selectors, fabricated payloads, and mock response indicators.

## Rationale

Artifact scanning must remain close to `harness check user-evidence` while
staying isolated from the general-purpose document checker. A separate scanner
module keeps binary/JSON parsing testable and avoids expanding
`src/harness_governance/commands/check.py` with format-specific parsing code.

## Status

Accepted

## Context

The v1 user-evidence gate validates Markdown field completeness only.
Agents can write convincing evidence docs while tests bypass the real
user entry — clicking hidden buttons, sending fabricated payloads, or
using internal test-only selectors. upgrade.md task #3 requests
enhancement to Playwright trace / request payload / selector scanning.

## Alternatives Considered

1. **Integrated in `src/harness_governance/commands/check.py`** — rejected; `src/harness_governance/commands/check.py` already 1600+ lines,
   mixing binary/JSON artifact parsing with doc parsing blurs responsibility.
2. **New CLI subcommand** — rejected; opt-in subcommand defeats the
   automatic gate purpose; users would skip the stricter check.
3. **Full Playwright trace replay** — rejected; requires playwright runtime
   dependency, too heavy for a stdlib-only governance tool.

## Consequences

**Positive:**
- Evidence docs are backed by real artifact inspection, not just text.
- Agents cannot bypass the gate with well-written docs + shortcut tests.
- Graceful no-op for projects without artifacts (no regression).

**Negative:**
- One new source module and one new test file.
- Playwright trace format may vary across versions; defensive parsing
  adds complexity.
- False positive risk in selector scanning; mitigated by curated pattern
  list.

**Long-term:**
- Scanner can be extended with screenshot comparison, AST analysis, and
  payload-vs-UI matching in future versions without changing the public
  API.

## Validation

1. Existing user-evidence tests pass (no regression).
2. New tests: HAR empty payload, HAR mock response, trace forbidden
   selector, trace non-user first URL, test source forbidden selector,
   malformed artifact graceful skip, no-artifacts no-op.
3. `harness check all` still passes on harness-governance's own
   verification docs.
4. `ruff check`, `mypy`, `pytest` all pass.
