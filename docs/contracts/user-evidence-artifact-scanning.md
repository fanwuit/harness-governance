# Contract: User-Evidence Artifact Scanning

## Public API

```
scan_evidence_artifacts(repo_root: Path, evidence_path: Path) -> list[str]
```

Returns a list of human-readable finding strings. Empty list = no findings.
Never raises on malformed/missing artifacts (graceful).

## Field Specifications

### API parameters (matched against Python AST)

| Name | Type | Required | Description |
|---|---|---|---|
| repo_root | Path | yes | Repository root for resolving relative paths |
| evidence_doc | Path | yes | Path to the evidence Markdown file being validated |

### Module-level constants

The scanner defines these constants (names prefixed with `_` are private and
intentionally excluded from AST alignment; they are covered by behaviour
contracts C1-C8):

- `FORBIDDEN_SELECTOR_PATTERNS` — curated forbidden selector strings
- `NON_USER_NAV_SEGMENTS` — URL segments indicating non-user navigation
- `MOCK_RESPONSE_INDICATORS` — headers indicating mock responses
- `MOCK_RESOURCE_TYPES` — resource types indicating mock responses
- `SAVE_METHODS` — HTTP methods requiring payload validation
- `TEST_SOURCE_SUFFIXES` — file suffixes identifying test sources
- `RESULT_DIRS` — well-known directories for artifact discovery

## Behaviour Contracts

### C1: No-artifact no-op

The system MUST produce no findings when no HAR, trace, or test source
artifacts are discoverable for a given evidence doc.
Verified by: `test_no_artifacts_no_findings`.

### C2: HAR empty payload detection

The system MUST report a finding when a HAR file contains a POST, PUT, or
PATCH entry with empty or missing `request.postData.text`.
Verified by: `test_har_empty_post_data`.

### C3: HAR mock response detection

The system MUST report a finding when a HAR entry response has status 0,
or headers containing `X-Mock`, or `_resourceType` containing `mock`.
Verified by: `test_har_mock_response`.

### C4: Playwright trace forbidden selector

The system MUST report a finding when a Playwright trace zip contains an
action event whose `params.selector` matches a forbidden pattern
(`[data-test-only`, `.lifecycle-actions`, `button:first()`, etc.).
Verified by: `test_trace_forbidden_selector`.

### C5: Trace non-user first navigation

The system MUST report a finding when the first navigation event in a
trace targets a URL containing `localhost:*/test-fixture`, `127.0.0.1`,
or `test-only` path segments (indicating a non-user entry).
Verified by: `test_trace_non_user_first_nav`.

### C6: Test source forbidden selector

The system MUST report a finding when a test source file
(`.spec.ts`, `.test.ts`, `_e2e.py`, etc.) contains a forbidden selector
pattern.
Verified by: `test_test_source_forbidden_selector`.

### C7: Malformed artifact graceful skip

The system MUST NOT crash when a HAR file is malformed JSON, a trace zip
is corrupt, or a test source file is empty. It MUST skip the artifact and
continue.
Verified by: `test_malformed_artifacts_graceful`.

### C8: Doc-level checks unchanged

The system MUST preserve all existing v1 doc-level validation behaviour.
Existing tests in `test_check_cmd.py` MUST pass unchanged.
Verified by: `test_existing_user_evidence_tests_pass`.

## Failure Cases

- Malformed HAR JSON → skip, no finding (cannot validate).
- Corrupt trace zip → skip, no finding.
- Empty trace.trace → skip, no finding.
- Unreadable test source → skip, no finding.
- Evidence doc with no Command/Result paths and no well-known result dirs
  → no artifacts discovered, no findings.

## Out of Scope

- Playwright trace replay or screenshot comparison.
- AST-based test source analysis.
- HAR response body content assertion.
- Selector allowlist per project.
- Live network capture.
