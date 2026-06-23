"""Contract-based tests for ``evidence_scanner``.

Each test maps to a behaviour contract in
``docs/contracts/user-evidence-artifact-scanning.md``.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from harness_governance.commands.evidence_scanner import scan_evidence_artifacts


def _make_evidence_doc(repo_root: Path, name: str = "save.md") -> Path:
    evidence_dir = repo_root / "docs" / "verification"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    path = evidence_dir / name
    path.write_text(
        """# Save loop

MVP complete.

## User-Perceived Integration Evidence
- Evidence level: real-user acceptance
- Real User Entry: Save button in the package editor toolbar
- User-Visible State: Editor shows the saved title after reload
- Persistence/External State: GET /packages/123 returns the same title
- Anti-Self-Proof Assertion: UI value, PUT payload, GET response, and reopened UI match
- Forbidden Test Shortcuts: none
- Command: npx playwright test --trace on
- Result: passed 2026-06-19
""",
        encoding="utf-8",
    )
    return path


def _make_har(repo_root: Path, entries: list[dict]) -> Path:
    har_path = repo_root / "test-results" / "save.har"
    har_path.parent.mkdir(parents=True, exist_ok=True)
    har_path.write_text(json.dumps({"log": {"entries": entries}}), encoding="utf-8")
    return har_path


def _make_trace_zip(repo_root: Path, events: list[dict]) -> Path:
    trace_path = repo_root / "test-results" / "trace.zip"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(trace_path, "w") as zf:
        lines = "\n".join(json.dumps(e) for e in events)
        zf.writestr("trace.trace", lines)
    return trace_path


def _make_test_source(repo_root: Path, name: str, content: str) -> Path:
    src_path = repo_root / "tests" / "e2e" / name
    src_path.parent.mkdir(parents=True, exist_ok=True)
    src_path.write_text(content, encoding="utf-8")
    return src_path


# --- C1: No-artifact no-op ------------------------------------------------


def test_no_artifacts_no_findings(tmp_repo: Path) -> None:
    """C1: no artifacts discovered -> no findings."""
    evidence = _make_evidence_doc(tmp_repo)
    findings = scan_evidence_artifacts(tmp_repo, evidence)
    assert findings == []


# --- C2: HAR empty payload -------------------------------------------------


def test_har_empty_post_data(tmp_repo: Path) -> None:
    """C2: POST with empty postData -> finding."""
    evidence = _make_evidence_doc(tmp_repo)
    _make_har(
        tmp_repo,
        [
            {
                "request": {"method": "POST", "url": "/api/save", "postData": {}},
                "response": {"status": 200},
            }
        ],
    )
    findings = scan_evidence_artifacts(tmp_repo, evidence)
    assert any("postData" in f.lower() or "payload" in f.lower() for f in findings)


# --- C3: HAR mock response -------------------------------------------------


def test_har_mock_response(tmp_repo: Path) -> None:
    """C3: response status 0 or X-Mock header -> finding."""
    evidence = _make_evidence_doc(tmp_repo)
    _make_har(
        tmp_repo,
        [
            {
                "request": {
                    "method": "POST",
                    "url": "/api/save",
                    "postData": {"text": "title=hello"},
                },
                "response": {"status": 0, "headers": []},
            }
        ],
    )
    findings = scan_evidence_artifacts(tmp_repo, evidence)
    assert any("mock" in f.lower() for f in findings)


# --- C4: Playwright trace forbidden selector ------------------------------


def test_trace_forbidden_selector(tmp_repo: Path) -> None:
    """C4: trace action event with forbidden selector -> finding."""
    evidence = _make_evidence_doc(tmp_repo)
    _make_trace_zip(
        tmp_repo,
        [
            {
                "type": "action",
                "apiName": "page.click",
                "params": {"selector": '[data-test-only="save"]'},
            },
        ],
    )
    findings = scan_evidence_artifacts(tmp_repo, evidence)
    assert any(
        "selector" in f.lower() or "data-test-only" in f.lower() for f in findings
    )


# --- C5: Trace non-user first navigation -----------------------------------


def test_trace_non_user_first_nav(tmp_repo: Path) -> None:
    """C5: first navigation to test-fixture URL -> finding."""
    evidence = _make_evidence_doc(tmp_repo)
    _make_trace_zip(
        tmp_repo,
        [
            {
                "type": "action",
                "apiName": "page.goto",
                "params": {"url": "http://localhost:3000/test-fixture"},
            },
        ],
    )
    findings = scan_evidence_artifacts(tmp_repo, evidence)
    assert any(
        "fixture" in f.lower() or "non-user" in f.lower() or "navigation" in f.lower()
        for f in findings
    )


# --- C6: Test source forbidden selector ------------------------------------


def test_test_source_forbidden_selector(tmp_repo: Path) -> None:
    """C6: test source file with forbidden selector -> finding."""
    evidence = _make_evidence_doc(tmp_repo)
    _make_test_source(
        tmp_repo,
        "save.spec.ts",
        'test("save", () => { page.click(".lifecycle-actions button:first()"); });',
    )
    findings = scan_evidence_artifacts(tmp_repo, evidence)
    assert any("selector" in f.lower() or "lifecycle" in f.lower() for f in findings)


# --- C7: Malformed artifact graceful skip ----------------------------------


def test_malformed_artifacts_graceful(tmp_repo: Path) -> None:
    """C7: malformed HAR / corrupt trace / empty source -> no crash."""
    evidence = _make_evidence_doc(tmp_repo)
    bad_har = tmp_repo / "test-results" / "bad.har"
    bad_har.parent.mkdir(parents=True, exist_ok=True)
    bad_har.write_text("{not valid json", encoding="utf-8")
    bad_zip = tmp_repo / "test-results" / "bad.zip"
    with zipfile.ZipFile(bad_zip, "w") as zf:
        zf.writestr("not_trace.txt", "garbage")
    findings = scan_evidence_artifacts(tmp_repo, evidence)
    assert isinstance(findings, list)


def test_empty_trace_graceful(tmp_repo: Path) -> None:
    """C7b: empty trace.trace -> no crash, no findings."""
    evidence = _make_evidence_doc(tmp_repo)
    _make_trace_zip(tmp_repo, [])
    findings = scan_evidence_artifacts(tmp_repo, evidence)
    assert isinstance(findings, list)


# --- C8: Doc-level checks unchanged (smoke) --------------------------------


def test_scan_does_not_raise_on_clean_repo(tmp_repo: Path) -> None:
    """C8: scanner does not interfere with doc-level checks on clean repo."""
    evidence_dir = tmp_repo / "docs" / "verification"
    evidence_dir.mkdir(parents=True, exist_ok=True)
    (evidence_dir / "docs-only.md").write_text(
        """# Docs only

## User-Perceived Integration Not Applicable
- Reason: Documentation-only change with no product path
- Replacement verification: harness check docs
- Residual risk: none
""",
        encoding="utf-8",
    )
    findings = scan_evidence_artifacts(tmp_repo, evidence_dir / "docs-only.md")
    assert findings == []


# --- Additional: HAR with valid payload passes ----------------------------


def test_har_valid_payload_no_finding(tmp_repo: Path) -> None:
    """HAR with non-empty postData and real status -> no finding."""
    evidence = _make_evidence_doc(tmp_repo)
    _make_har(
        tmp_repo,
        [
            {
                "request": {
                    "method": "POST",
                    "url": "/api/save",
                    "postData": {"text": "title=hello"},
                },
                "response": {"status": 200, "headers": []},
            }
        ],
    )
    findings = scan_evidence_artifacts(tmp_repo, evidence)
    assert not any("postData" in f.lower() or "payload" in f.lower() for f in findings)
    assert not any("mock" in f.lower() for f in findings)
