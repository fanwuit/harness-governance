"""Change packet file operations.

Encapsulates ``docs/changes/{id}/`` creation, template instantiation,
and the structural checks documented in
``harness-engineering/scripts/check-change-packet.mjs``.
"""

from __future__ import annotations

import re
from datetime import date
from importlib import resources
from pathlib import Path
from typing import Iterable

from ..config.defaults import ALLOWED_PACKET_STATUSES, REQUIRED_PACKET_FILES
from ..messages import bilingual
from ..models.schemas import ChangePacketInitResult, ChangePacketSummary
from ._cache import PACKET_CACHE, file_cache
from ._util import assert_inside, validate_change_id

_TEMPLATES_PACKAGE = "harness_governance.data.templates.change-packet"
_REFERENCES_PACKAGE = "harness_governance.data.references"

# A line of the form "- [ ] ..." or "- [x] ..." in tasks.md.
_CHECKBOX_RE = re.compile(r"^\s*-\s+\[[ xX]\]\s+\S", re.MULTILINE)
# "Status: <value>" lines inside any packet file.
_STATUS_RE = re.compile(r"^Status\s*:\s*([A-Za-z-]+)\s*$", re.IGNORECASE | re.MULTILINE)
# A line declaring a contract artifact.
_CONTRACT_ARTIFACT_RE = re.compile(
    r"^\s*-\s*(?:artifact|path|schema|example|fixture|probe|check script"
    r"|acceptance test|documentation invariant)\s*:\s*\S",
    re.IGNORECASE,
)
# Either an explicit "blocked reason:" line or a nearby blocked/because
# phrasing.
_BLOCKED_REASON_RE = re.compile(
    r"\bblocked reason\s*:\s*\S",
    re.IGNORECASE,
)
_BLOCKED_PROSE_RE = re.compile(
    r"\bblocked\b[\s\S]{0,120}\b(?:because|reason|missing evidence|无法|缺少|等待|原因)\b",
    re.IGNORECASE,
)
# Verification evidence: a command line, a pass/fail line, or a reason line.
_VERIFICATION_CMD_RE = re.compile(
    r"^\s*-\s*(?:npm|node|python|pytest|cargo|go test|mvn|gradle|dotnet)\b",
    re.IGNORECASE,
)
_VERIFICATION_OUTCOME_RE = re.compile(
    r"^\s*-\s*(?:pass|passed|fail|failed|skipped|blocked)\b",
    re.IGNORECASE,
)
_VERIFICATION_REASON_RE = re.compile(
    r"^\s*-\s*(?:reason|risk|follow-up|blocked)\s*:\s*\S",
    re.IGNORECASE,
)
_UNABLE_TO_VERIFY_RE = re.compile(r"unable to verify", re.IGNORECASE)

# Backlink keywords for archived packets.
_BACKLINK_TARGET_RE = re.compile(
    r"\b(?:ADR|README|contract|contracts|schema|fixture|probe|verification"
    r"|NEXT\.md|TODO\.md|backlog|queue|index|项目索引|队列|验证|契约)\b",
    re.IGNORECASE,
)
_BACKLINK_ACTION_RE = re.compile(
    r"\b(?:link|linked|backlink|synced|copied|updated|回链|同步|写回|归档回)\b",
    re.IGNORECASE,
)


def load_packet_template(name: str) -> str:
    """Return the raw text of a change-packet template file."""
    resource = resources.files(_TEMPLATES_PACKAGE).joinpath(name)
    if not resource.is_file():
        raise FileNotFoundError(f"Template not found in package data: {name}")
    return resource.read_text(encoding="utf-8")


def packet_dir(project_root: Path, change_id: str) -> Path:
    """Return the absolute packet directory for ``change_id``."""
    validate_change_id(change_id)
    return (project_root / "docs" / "changes" / change_id).resolve()


def init_packet(
    project_root: Path,
    change_id: str,
    *,
    force: bool = False,
    today: date | None = None,
) -> ChangePacketInitResult:
    """Create a packet directory under ``docs/changes/{id}/``.

    Existing files are preserved unless ``force`` is true, in which
    case missing template files are filled in but present files are
    left untouched (matching the legacy ``init-change-packet.mjs``
    semantics).
    """
    validate_change_id(change_id)
    root_abs = project_root.resolve()
    target = (root_abs / "docs" / "changes" / change_id).resolve()
    assert_inside(root_abs, target)

    if target.exists() and not force and any(target.iterdir()):
        raise FileExistsError(
            bilingual(
                "packet.exists",
                path=str(target.relative_to(root_abs)),
            )
        )

    target.mkdir(parents=True, exist_ok=True)
    today_str = (today or date.today()).isoformat()

    created: list[str] = []
    for filename in REQUIRED_PACKET_FILES:
        file_path = target / filename
        if file_path.exists():
            continue
        text = load_packet_template(filename)
        text = text.replace("{{CHANGE_ID}}", change_id).replace("{{TODAY}}", today_str)
        file_path.write_text(text, encoding="utf-8")
        created.append(filename)

    return ChangePacketInitResult(
        change_id=change_id,
        packet_dir=target,
        created_files=tuple(created),
        today=today or date.today(),
    )


def discover_packets(project_root: Path) -> list[Path]:
    """Return all packet directories under ``docs/changes/``.

    Live packets and ``archive/*`` are both returned; the caller decides
    which to inspect. Result is cached at the function level and
    invalidated when ``docs/changes/`` mtime changes.
    """
    return _discover_packets_cached(project_root)


@file_cache
def _discover_packets_cached(project_root: Path) -> list[Path]:
    changes_root = (project_root / "docs" / "changes").resolve()
    if not changes_root.is_dir():
        return []

    found: list[Path] = []
    for entry in sorted(changes_root.iterdir()):
        if entry.is_dir() and entry.name != "archive":
            found.append(entry)
    archive_root = changes_root / "archive"
    if archive_root.is_dir():
        for entry in sorted(archive_root.iterdir()):
            if entry.is_dir():
                found.append(entry)
    return found


def resolve_packet_path(project_root: Path, target: str) -> Path:
    """Resolve a packet reference given on the CLI.

    Accepts an absolute path, a repo-relative path, or a change id.
    """
    candidate = Path(target)
    if candidate.is_absolute() and candidate.is_dir():
        return candidate.resolve()

    repo_relative = (project_root / target).resolve()
    if repo_relative.is_dir():
        return repo_relative

    packet_candidate = (project_root / "docs" / "changes" / target).resolve()
    if packet_candidate.is_dir():
        return packet_candidate

    raise FileNotFoundError(bilingual("packet.not_found", target=target))


def check_packet(
    packet_dir_path: Path,
    *,
    project_root: Path | None = None,
) -> tuple[list[str], ChangePacketSummary]:
    """Validate one packet directory.

    Returns ``(errors, summary)``. ``errors`` is a list of human-readable
    failure messages; ``summary`` is always returned so the caller can
    produce a dashboard row even when the packet is invalid.
    """
    errors: list[str] = []
    label = _rel(packet_dir_path, project_root)
    if not packet_dir_path.exists():
        return (
            [bilingual("packet.label_does_not_exist", label=label)],
            _empty_summary(packet_dir_path),
        )
    if not packet_dir_path.is_dir():
        return (
            [bilingual("packet.label_not_a_dir", label=label)],
            _empty_summary(packet_dir_path),
        )

    texts: dict[str, str] = {}
    for filename in REQUIRED_PACKET_FILES:
        file_path = packet_dir_path / filename
        if not file_path.exists():
            errors.append(bilingual("packet.label_missing_file", label=label, filename=filename))
            continue
        texts[filename] = file_path.read_text(encoding="utf-8")

    tasks_text = texts.get("tasks.md", "")
    if tasks_text and not _CHECKBOX_RE.search(tasks_text):
        errors.append(bilingual("packet.label_missing_checkbox", label=label))

    status_value = "draft"
    for filename, text in texts.items():
        for match in _STATUS_RE.finditer(text):
            value = match.group(1).lower()
            if value not in ALLOWED_PACKET_STATUSES:
                errors.append(
                    bilingual(
                        "packet.label_invalid_status",
                        label=label,
                        filename=filename,
                        value=match.group(1),
                    )
                )
            else:
                status_value = value

    contracts_text = texts.get("contracts.md", "")
    if contracts_text and not _has_contract_artifact(contracts_text) and not _has_blocked_reason(contracts_text):
        errors.append(bilingual("packet.label_missing_contract_artifact", label=label))

    verification_text = texts.get("verification.md", "")
    if verification_text and not _has_verification_evidence(verification_text):
        errors.append(bilingual("packet.label_missing_verification", label=label))

    combined = "\n".join(texts.values())
    if _is_archived(packet_dir_path, combined, project_root) and not _has_archive_backlink(combined):
        errors.append(bilingual("packet.label_archived_no_backlink", label=label))

    summary = ChangePacketSummary(
        change_id=packet_dir_path.name,
        path=packet_dir_path,
        status=status_value,
    )
    return errors, summary


def check_all_packets(project_root: Path) -> tuple[list[str], list[ChangePacketSummary]]:
    """Check every packet under ``docs/changes/``."""
    all_errors: list[str] = []
    summaries: list[ChangePacketSummary] = []
    for packet_dir_path in discover_packets(project_root):
        errors, summary = check_packet(packet_dir_path, project_root=project_root)
        all_errors.extend(errors)
        summaries.append(summary)
    return all_errors, summaries


# Internal helpers ----------------------------------------------------------


def _rel(packet_dir_path: Path, project_root: Path | None) -> str:
    if project_root is None:
        return str(packet_dir_path)
    try:
        return str(packet_dir_path.resolve().relative_to(project_root.resolve()))
    except ValueError:
        return str(packet_dir_path)


def _empty_summary(packet_dir_path: Path) -> ChangePacketSummary:
    return ChangePacketSummary(
        change_id=packet_dir_path.name,
        path=packet_dir_path,
        status="draft",
        missing_files=REQUIRED_PACKET_FILES,
    )


def _has_contract_artifact(text: str) -> bool:
    return any(_CONTRACT_ARTIFACT_RE.match(line) for line in text.splitlines())


def _has_blocked_reason(text: str) -> bool:
    return bool(_BLOCKED_REASON_RE.search(text) or _BLOCKED_PROSE_RE.search(text))


def _has_verification_evidence(text: str) -> bool:
    lines = [line.strip() for line in text.splitlines()]
    if any(_VERIFICATION_CMD_RE.match(line) for line in lines):
        return True
    if any(_VERIFICATION_OUTCOME_RE.match(line) for line in lines):
        return True
    if _UNABLE_TO_VERIFY_RE.search(text) and any(
        _VERIFICATION_REASON_RE.match(line) for line in lines
    ):
        return True
    return False


def _is_archived(packet_dir_path: Path, combined: str, project_root: Path | None) -> bool:
    if project_root is not None:
        try:
            rel = packet_dir_path.resolve().relative_to(project_root.resolve())
            if str(rel).replace("\\", "/").startswith("docs/changes/archive/"):
                return True
        except ValueError:
            pass
    return bool(re.search(r"^Status\s*:\s*archived\s*$", combined, re.IGNORECASE | re.MULTILINE))


def _has_archive_backlink(text: str) -> bool:
    return bool(_BACKLINK_TARGET_RE.search(text) and _BACKLINK_ACTION_RE.search(text))


__all__ = [
    "init_packet",
    "check_packet",
    "check_all_packets",
    "discover_packets",
    "resolve_packet_path",
    "load_packet_template",
    "packet_dir",
]