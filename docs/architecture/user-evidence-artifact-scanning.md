# Architecture: User-Evidence Artifact Scanning

## Boundaries

The scanner is an internal library used by `harness check user-evidence`. It
does not add a public CLI command, does not replay browser traces, and does not
introduce third-party runtime dependencies.

## Boundary Diagram

```
docs/verification/*.md          evidence_scanner.py            check.py
       |                               |                          |
       v                               v                          v
 +-----------+   +-----------------------------------+   +------------------+
 | evidence  |-->| scan_evidence_artifacts()         |-->| check_user_evidence()|
 | doc text  |   |  _scan_playwright_trace(zip)      |   |  doc-level checks  |
 +-----------+   |  _scan_har(json)                  |   |  + artifact findings|
                 |  _scan_test_selectors(source)     |   +------------------+
                 |  _discover_artifact_paths()       |
                 +-----------------------------------+
                          |
        +-----------------+-----------------+
        v                 v                 v
  *.har (JSON)    trace.zip (zip)    *.spec.ts / _e2e.py
  well-known      well-known         referenced test
  result dirs     result dirs        source files
```

## Component Responsibilities

### `evidence_scanner.py` (new)

- **Public API**: `scan_evidence_artifacts(repo_root, evidence_path) -> list[str]`
- **Responsibility**: discover and scan HAR, Playwright trace, and test
  source artifacts related to a given evidence doc. Return human-readable
  finding strings.
- **Ownership**: harness-governance core.
- **Boundary**: stdlib only (zipfile, json, re, pathlib). No third-party
  dependencies.

### `check.py` (modified)

- **Responsibility**: call `scan_evidence_artifacts` after doc-level
  validation in `_validate_user_evidence_file`. Convert returned strings
  to `CheckFinding` objects.
- **Ownership**: harness-governance core.
- **Boundary**: scanner is optional — import inside the function to avoid
  import cost when user-evidence check is not run.

### `tests/test_commands/test_evidence_scanner.py` (new)

- **Responsibility**: unit-test each scanner function with synthetic
  artifacts (in-memory HAR JSON, in-memory trace zip, temp test source).
- **Ownership**: harness-governance test suite.

## Data Flow

1. `check_user_evidence(repo_root)` iterates evidence files.
2. For each file, `_validate_user_evidence_file` runs doc-level checks (v1).
3. After doc-level checks, call `scan_evidence_artifacts(repo_root, path)`.
4. Scanner discovers artifact candidates:
   - Parse evidence doc `Command` and `Result` fields for file paths.
   - Scan well-known result directories: `test-results/`,
     `playwright-report/`, `e2e-results/`, `docs/verification/` siblings.
   - Match `.har` files and `*.zip` (trace) files.
   - Match test source files (`.spec.ts`, `.test.ts`, `_e2e.py`, etc.).
5. Scanner runs three sub-scanners on discovered artifacts.
6. Findings (strings) returned to check.py, converted to `CheckFinding`
   with `level="error"`.

## ADR Candidates

1. **ADR: Artifact scanning is additive and graceful** — scanner never
   blocks projects without artifacts; it only adds findings when artifacts
   are present and problematic. Rationale: avoids regression for doc-only
   and derived projects.

2. **ADR: stdlib-only artifact parsing** — no playwright or har2
   dependency. Rationale: keeps harness-governance dependency-free;
   defensive parsing handles format variation.

3. **ADR: Scanner module separate from check.py** —
   `evidence_scanner.py` as a standalone module. Rationale: testability
   and single-responsibility.

## Owners

All new components are owned by the harness-governance core package. No
external team boundaries are crossed. The scanner is an internal library
module, not a public CLI surface.
