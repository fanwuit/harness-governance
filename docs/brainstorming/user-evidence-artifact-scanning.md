# Brainstorming: User-Evidence Artifact Scanning

## Option A: Integrated scanner in check.py

- Best when: the enhancement is small and self-contained.
- Benefit: no new module, no import surface change.
- Cost: check.py grows beyond 1600 lines; harder to test scanner in isolation.
- Risk: mixing doc-parsing and binary/JSON artifact parsing in one file blurs
  responsibility.
- Evidence needed: none beyond existing tests.

## Option B: Separate `evidence_scanner.py` module (Recommended)

- Best when: scanner logic is non-trivial and benefits from isolated unit
  tests.
- Benefit: `check.py` stays focused on doc-level validation; scanner is
  unit-testable with synthetic HAR/trace/selector fixtures; clear public
  API (`scan_evidence_artifacts(repo_root, evidence_path) -> list[Finding]`).
- Cost: one new source module + one new test file.
- Risk: import boundary must be stable; check.py must call scanner
  opportunistically (skip on missing artifacts, never crash).
- Evidence needed: synthetic HAR, synthetic Playwright trace zip, synthetic
  test source with forbidden selectors.

## Option C: New CLI subcommand `harness check evidence-artifacts`

- Best when: artifact scanning should be opt-in to avoid surprising derived
  projects.
- Benefit: explicit, no regression risk for projects without artifacts.
- Cost: users must remember to run it — defeats the "gate" purpose.
- Risk: evidence gate becomes two commands, easy to skip the stricter one.
- Evidence needed: none.

## Ranked Recommendation

1. **Option B** — separate `evidence_scanner.py`, auto-integrated into
   `check_user_evidence`. Scanner runs after doc-level validation; only
   adds findings when artifacts are present. Graceful no-op when absent.
2. Option A — acceptable fallback if module count is a concern.
3. Option C — rejected for v2; the gate must be automatic.

## Non-Goals (v2)

- Full Playwright trace replay / rendering.
- AST-based test source analysis.
- Live network capture or proxying.
- Mandatory artifact requirement for all projects.
- HAR schema validation beyond save-flow payload presence.

## Deferred

- Selector allowlist (project declares which selectors are real user entries).
- Playwright trace screenshot comparison.
- HAR response body content assertion (payload-vs-UI matching).
