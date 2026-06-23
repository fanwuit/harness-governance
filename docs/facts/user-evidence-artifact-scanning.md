# Facts: User-Evidence Artifact Scanning

## Current State (v1 — document-level)

`check_user_evidence()` in `src/harness_governance/commands/check.py` validates
Markdown field completeness in `docs/verification/*.md` and
`docs/changes/*/verification.md`. It checks:

- Required fields non-empty (Evidence level, Real User Entry, etc.)
- Evidence level is smoke / contract / real-user acceptance
- Closure claims (MVP complete, closed loop complete, user-visible save complete)
  require real-user acceptance
- Forbidden shortcut terms in doc text (`.lifecycle-actions`, `button:first`,
  `hidden test panel`, `test-only`, `fixture-only`, `acceptance drawer`,
  `mock/fallback`, `mock all`, `assert called`, `skip e2e`, `todo evidence`,
  `not tested`)

## Target Artifact Formats

### Playwright Trace (`.zip`)

- A zip archive containing `trace.trace` (JSONL — one JSON object per line)
  plus a `resources/` directory.
- Each event line is a JSON object with fields: `type`, `apiName`,
  `params.selector`, `params.url`, `startTime`, `endTime`, etc.
- Action events (`type: action`) carry the selector and url used.
- The first navigation event should target a real user URL, not an internal
  test fixture URL.
- v2 must parse defensively: skip unparseable traces, never crash.

### HAR 1.2 (`.har`)

- Standard JSON: `{ "log": { "entries": [ { "request": {...}, "response": {...} } ] } }`
- `request.method`, `request.url`, `request.postData.text`
- `response.status`, `response.content.text`
- For save-like flows: POST/PUT/PATCH must have non-empty `postData.text`.
- Mocked responses often have `response.status: 0` or
  `_resourceType: "mock"` / `X-Mock: true` headers.

### Selector Source Scan

- Scan test source files (`.spec.ts`, `.test.ts`, `.spec.js`, `.test.js`,
  `_e2e.py`, `_e2e.ts`, `e2e/`) for forbidden selector patterns.
- Forbidden patterns (extend existing `_USER_EVIDENCE_FORBIDDEN_SHORTCUTS`):
  `[data-test-only`, `[data-testid="mock`, `.lifecycle-actions`,
  `button:first()`, `hidden`, `test-only`, `fixture-only`,
  `acceptance drawer`, `mock/fallback`.

## Assumptions / Risks

Assumption: evidence docs may reference artifact paths in the `Command` or
`Result` field (e.g. `pytest tests/e2e/save_loop.py --trace`).
Risk: path extraction is heuristic; v2 scans well-known directories
(`test-results/`, `playwright-report/`, `e2e-results/`, `docs/verification/`)
and any `.har` / `.zip` (trace) files referenced in the evidence doc.

Assumption: artifact scanning is additive — doc-level checks remain the base
layer; artifact checks add stricter findings when artifacts are present.
Risk: projects without artifacts must not regress; v2 only adds findings,
never removes existing doc-level validation.
