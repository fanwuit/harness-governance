# Brief: User-Evidence Artifact Scanning

## Goal

Enhance `harness check user-evidence` from document-level field validation
to also scan real test artifacts — Playwright trace zips, HAR HTTP archives,
and test source files — so that evidence docs claiming "real-user acceptance"
are backed by artifacts that do not use forbidden selectors, fabricated
payloads, or internal test-only entry points.

## Context

- Current v1 (`check_user_evidence`) validates Markdown field completeness
  and forbidden-term presence in doc text only.
- Agents can write convincing evidence docs while tests bypass the real user
  entry (hidden buttons, mock payloads, internal selectors).
- upgrade.md task #3 requests Playwright trace / request payload / selector
  scanning.

## Non-Goals

- Full Playwright trace replay or rendering.
- AST-based test source analysis.
- Live network capture or proxying.
- Mandatory artifact requirement for projects without user-perceived features.
- HAR schema validation beyond save-flow payload presence.

## Options Considered

See `docs/brainstorming/user-evidence-artifact-scanning.md`.
- Option A: integrated in check.py — rejected (file too large).
- Option B: separate `evidence_scanner.py` — selected.
- Option C: new CLI subcommand — rejected (defeats automatic gate).

## Decision / Direction

Create `src/harness_governance/commands/evidence_scanner.py` with three
scanner functions:

1. `scan_playwright_trace(path) -> list[str]` — parse zip, read
   `trace.trace` JSONL, detect forbidden selectors in action events and
   non-user-navigation first URLs.
2. `scan_har(path) -> list[str]` — parse HAR JSON, flag POST/PUT/PATCH
   with empty postData, mock response indicators, and missing readback
   GET after save.
3. `scan_test_selectors(path) -> list[str]` — scan test source files for
   forbidden selector patterns.

`check_user_evidence` calls `scan_evidence_artifacts(repo_root, evidence_path)`
after doc-level validation. Findings are additive; scanner is a graceful
no-op when no artifacts are found.

## Risks / Unknowns

- Playwright trace format may vary across versions — parse defensively,
  skip unparseable traces.
- False positives in selector scanning — use a curated forbidden pattern
  list, not broad regex.
- Performance — only scan files referenced by evidence docs or well-known
  result directories, never the whole repo.
- Derived project regression — scanner is additive; absent artifacts produce
  no findings.

## Success Criteria

1. `check_user_evidence` passes on projects with doc-only evidence and no
   artifacts (no regression).
2. `check_user_evidence` fails when a HAR file shows POST/PUT with empty
   postData for a save-flow evidence doc.
3. `check_user_evidence` fails when a Playwright trace contains a forbidden
   selector (e.g. `[data-test-only`) in an action event.
4. `check_user_evidence` fails when a test source file contains a forbidden
   selector pattern.
5. Scanner is graceful (no crash) on malformed/empty trace or HAR files.
6. All existing user-evidence tests still pass.
7. New tests cover: HAR empty payload, HAR mock response, trace forbidden
   selector, trace non-user first URL, test source forbidden selector,
   malformed artifact graceful skip, no-artifacts no-op.

## Next Layer

Architecture — design the module structure, public API, and integration
points with `check.py`.
