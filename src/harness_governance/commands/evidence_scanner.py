"""Artifact-level evidence scanner for ``harness check user-evidence``.

This module scans real test artifacts — Playwright trace zips, HAR HTTP
archives, and test source files — for forbidden selectors, fabricated
payloads, and mock response indicators. It augments the document-level
validation in :mod:`harness_governance.commands.check`.

Design principles:
- stdlib only (zipfile, json, re, pathlib).
- Graceful: never raises on malformed/missing artifacts.
- Additive: only adds findings; never removes doc-level validation.
"""

from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path

_FORBIDDEN_SELECTOR_PATTERNS: tuple[str, ...] = (
    "[data-test-only",
    '[data-testid="mock',
    ".lifecycle-actions",
    "button:first()",
    "hidden test panel",
    "test-only",
    "fixture-only",
    "acceptance drawer",
    "mock/fallback",
)

_NON_USER_NAV_SEGMENTS: tuple[str, ...] = (
    "test-fixture",
    "test-only",
    "127.0.0.1",
    "localhost",
)

_MOCK_RESPONSE_INDICATORS: tuple[str, ...] = (
    "x-mock",
    "x_mock",
)

_MOCK_RESOURCE_TYPES: tuple[str, ...] = (
    "mock",
    "fake",
)

_SAVE_METHODS: frozenset[str] = frozenset({"POST", "PUT", "PATCH"})

_TEST_SOURCE_SUFFIXES: tuple[str, ...] = (
    ".spec.ts",
    ".test.ts",
    ".spec.js",
    ".test.js",
    "_e2e.py",
    "_e2e.ts",
)

_RESULT_DIRS: tuple[str, ...] = (
    "test-results",
    "playwright-report",
    "e2e-results",
    "docs/verification",
)

_HAR_GLOBS: tuple[str, ...] = ("**/*.har",)
_TRACE_GLOBS: tuple[str, ...] = ("**/*.zip",)
_TEST_SOURCE_GLOBS: tuple[str, ...] = (
    "**/*.spec.ts",
    "**/*.test.ts",
    "**/*.spec.js",
    "**/*.test.js",
    "**/*_e2e.py",
    "**/*_e2e.ts",
)


def scan_evidence_artifacts(repo_root: Path, evidence_doc: Path) -> list[str]:
    """Discover and scan artifacts related to an evidence doc.

    Returns a list of human-readable finding strings. Empty list means
    no findings. Never raises on malformed/missing artifacts.
    """
    findings: list[str] = []
    har_files, trace_files, test_sources = _discover_artifacts(
        repo_root, evidence_doc
    )
    for har_path in har_files:
        findings.extend(_scan_har(har_path))
    for trace_path in trace_files:
        findings.extend(_scan_playwright_trace(trace_path))
    for src_path in test_sources:
        findings.extend(_scan_test_selectors(src_path))
    return findings


def _discover_artifacts(
    repo_root: Path, evidence_doc: Path
) -> tuple[list[Path], list[Path], list[Path]]:
    """Find HAR, trace, and test source artifacts to scan."""
    har_files: list[Path] = []
    trace_files: list[Path] = []
    test_sources: list[Path] = []

    evidence_text = ""
    try:
        evidence_text = evidence_doc.read_text(encoding="utf-8")
    except OSError:
        pass

    referenced_paths = _extract_paths_from_evidence(evidence_text, repo_root)

    for path in referenced_paths:
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix == ".har":
            har_files.append(path)
        elif suffix == ".zip":
            trace_files.append(path)
        elif path.name.endswith(_TEST_SOURCE_SUFFIXES):
            test_sources.append(path)

    for dir_name in _RESULT_DIRS:
        result_dir = repo_root / dir_name
        if not result_dir.is_dir():
            continue
        for pattern in _HAR_GLOBS:
            har_files.extend(p for p in result_dir.glob(pattern) if p.is_file())
        for pattern in _TRACE_GLOBS:
            candidate = list(result_dir.glob(pattern))
            for p in candidate:
                if p not in trace_files and _looks_like_trace(p):
                    trace_files.append(p)

    for pattern in _TEST_SOURCE_GLOBS:
        test_sources.extend(p for p in repo_root.glob(pattern) if p.is_file())

    seen: set[Path] = set()
    deduped_har: list[Path] = []
    for p in har_files:
        rp = p.resolve()
        if rp not in seen:
            seen.add(rp)
            deduped_har.append(p)

    seen2: set[Path] = set()
    deduped_trace: list[Path] = []
    for p in trace_files:
        rp = p.resolve()
        if rp not in seen2:
            seen2.add(rp)
            deduped_trace.append(p)

    seen3: set[Path] = set()
    deduped_src: list[Path] = []
    for p in test_sources:
        rp = p.resolve()
        if rp not in seen3:
            seen3.add(rp)
            deduped_src.append(p)

    return deduped_har, deduped_trace, deduped_src


def _extract_paths_from_evidence(text: str, repo_root: Path) -> list[Path]:
    """Extract file paths mentioned in evidence doc Command/Result fields."""
    paths: list[Path] = []
    for m in re.finditer(r"[\w/.\-]+\.(?:har|zip|spec\.ts|test\.ts|spec\.js|test\.js|py|ts)", text):
        candidate = m.group(0)
        full = repo_root / candidate
        if full.is_file():
            paths.append(full)
        else:
            for parent in (repo_root, repo_root / "tests", repo_root / "e2e"):
                alt = parent / candidate
                if alt.is_file():
                    paths.append(alt)
                    break
    return paths


def _looks_like_trace(path: Path) -> bool:
    """Heuristically check if a zip is a Playwright trace."""
    try:
        with zipfile.ZipFile(path, "r") as zf:
            names = zf.namelist()
    except (zipfile.BadZipFile, OSError):
        return False
    return any("trace.trace" in name for name in names)


def _scan_har(path: Path) -> list[str]:
    """Scan a HAR file for empty payloads and mock responses."""
    findings: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError, UnicodeDecodeError):
        return findings

    if not isinstance(data, dict):
        return findings
    entries = data.get("log", {}).get("entries", [])
    if not isinstance(entries, list):
        return findings

    for i, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        request = entry.get("request", {})
        response = entry.get("response", {})
        if not isinstance(request, dict):
            request = {}
        if not isinstance(response, dict):
            response = {}

        method = str(request.get("method", "")).upper()
        url = str(request.get("url", ""))

        if method in _SAVE_METHODS:
            post_data = request.get("postData", {})
            if isinstance(post_data, dict):
                text = post_data.get("text", "")
            else:
                text = ""
            if not text:
                findings.append(
                    f"HAR entry {i}: {method} {url} has empty request payload "
                    f"(postData.text missing or empty)"
                )

        status = response.get("status")
        if status == 0:
            findings.append(
                f"HAR entry {i}: {method} {url} has mock response status 0"
            )

        headers = response.get("headers", [])
        if isinstance(headers, list):
            for header in headers:
                if isinstance(header, dict):
                    name = str(header.get("name", "")).lower()
                    if any(ind in name for ind in _MOCK_RESPONSE_INDICATORS):
                        findings.append(
                            f"HAR entry {i}: {method} {url} has mock "
                            f"response header {header.get('name')}"
                        )
                        break

        resource_type = str(entry.get("_resourceType", "")).lower()
        if any(rt in resource_type for rt in _MOCK_RESOURCE_TYPES):
            findings.append(
                f"HAR entry {i}: {method} {url} has mock resource type "
                f"'{entry.get('_resourceType')}'"
            )

    return findings


def _scan_playwright_trace(path: Path) -> list[str]:
    """Scan a Playwright trace zip for forbidden selectors and non-user nav."""
    findings: list[str] = []
    try:
        with zipfile.ZipFile(path, "r") as zf:
            trace_names = [
                n for n in zf.namelist() if n.endswith("trace.trace")
            ]
            if not trace_names:
                return findings
            raw = zf.read(trace_names[0])
    except (zipfile.BadZipFile, OSError, KeyError):
        return findings

    try:
        text = raw.decode("utf-8", errors="replace")
    except (UnicodeDecodeError, AttributeError):
        return findings

    first_nav_checked = False
    for line_num, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue

        event_type = event.get("type", "")
        api_name = event.get("apiName", "")
        params = event.get("params", {})
        if not isinstance(params, dict):
            params = {}

        selector = str(params.get("selector", ""))
        if selector:
            lower_sel = selector.lower()
            for pattern in _FORBIDDEN_SELECTOR_PATTERNS:
                if pattern.lower() in lower_sel:
                    findings.append(
                        f"Playwright trace line {line_num}: action "
                        f"'{api_name}' uses forbidden selector '{selector}' "
                        f"(matched pattern: {pattern})"
                    )
                    break

        url = str(params.get("url", ""))
        if url and not first_nav_checked:
            if "goto" in api_name.lower() or event_type == "navigation":
                lower_url = url.lower()
                if any(seg in lower_url for seg in _NON_USER_NAV_SEGMENTS):
                    findings.append(
                        f"Playwright trace line {line_num}: first navigation "
                        f"targets non-user URL '{url}'"
                    )
                first_nav_checked = True

    return findings


def _scan_test_selectors(path: Path) -> list[str]:
    """Scan a test source file for forbidden selector patterns."""
    findings: list[str] = []
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return findings

    lower = text.lower()
    for pattern in _FORBIDDEN_SELECTOR_PATTERNS:
        if pattern.lower() in lower:
            findings.append(
                f"Test source {path.name}: contains forbidden selector "
                f"pattern '{pattern}'"
            )

    return findings


__all__ = [
    "scan_evidence_artifacts",
]
