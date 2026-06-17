"""Scope drift detection — Gap 3 of the v0.8.0 governance release.

Detects when implementation changes exceed declared scope boundaries by
comparing ``git diff`` output against persisted scope declarations.
Triggers decomposition suggestions and feeds the T10 transition rule.

``resolve_diff_base()`` computes the merge-base for diffing; it is
extracted as a standalone function for testability.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

from ..models.schemas import (
    DecompositionTrigger,
    DriftDetection,
    ScopeBoundary,
    ScopeDeclaration,
)

logger = logging.getLogger("harness.drift")

# Git empty-tree hash — used as final fallback for diff base.
_EMPTY_TREE = "4b825dc642cb6eb9a060e54bf899d4e3c6e2c3a8"


def resolve_diff_base(
    project_root: Path,
    default_branch: str = "main",
    override_ref: str | None = None,
) -> str:
    """Resolve the git ref to diff against.

    Resolution order:
    1. *override_ref* (from CLI ``--base-ref``).
    2. ``git merge-base HEAD <default_branch>``.
    3. ``HEAD~1``.
    4. Empty-tree hash (diff everything).
    """
    if override_ref:
        return override_ref

    try:
        result = subprocess.run(
            ["git", "merge-base", "HEAD", default_branch],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD~1"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass

    return _EMPTY_TREE


def _run_git_diff(
    project_root: Path,
    base_ref: str,
) -> tuple[list[str], int, int]:
    """Run ``git diff --name-only --stat`` and return parsed results.

    Returns ``(files_changed, lines_added, lines_deleted)``.
    """
    files: list[str] = []
    lines_added = 0
    lines_deleted = 0

    # --name-only
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", base_ref, "HEAD"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            files = [
                line.strip() for line in result.stdout.splitlines() if line.strip()
            ]
    except Exception:
        logger.warning("git diff --name-only failed", exc_info=True)

    # --numstat for line counts
    try:
        result = subprocess.run(
            ["git", "diff", "--numstat", base_ref, "HEAD"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                parts = line.split("\t")
                if len(parts) >= 2:
                    try:
                        lines_added += int(parts[0]) if parts[0] != "-" else 0
                    except ValueError:
                        pass
                    try:
                        lines_deleted += int(parts[1]) if parts[1] != "-" else 0
                    except ValueError:
                        pass
    except Exception:
        logger.warning("git diff --numstat failed", exc_info=True)

    return files, lines_added, lines_deleted


class DriftDetectionEngine:
    """Detect scope drift by comparing git diffs against declared boundaries.

    Usage::

        engine = DriftDetectionEngine(project_root)
        engine.declare_scope(scope_declaration)
        drift = engine.check_boundary("chg-001")
        triggers = engine.detect_decomposition_trigger(drift, boundary)
    """

    SCOPES_DIR = Path(".harness/scopes")

    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root

    # -- Public API -------------------------------------------------------

    def declare_scope(self, declaration: ScopeDeclaration) -> Path:
        """Persist a scope declaration to disk.

        Returns the path to the written file.
        """
        scopes_dir = self._project_root / self.SCOPES_DIR
        scopes_dir.mkdir(parents=True, exist_ok=True)

        path = scopes_dir / f"{declaration.change_id}.json"
        path.write_text(
            declaration.model_dump_json(indent=2, exclude_none=True),
            encoding="utf-8",
        )
        return path

    def load_scope(self, change_id: str) -> ScopeDeclaration | None:
        """Load a previously declared scope, or None."""
        path = self._project_root / self.SCOPES_DIR / f"{change_id}.json"
        if not path.is_file():
            return None
        try:
            return ScopeDeclaration.model_validate_json(
                path.read_text(encoding="utf-8")
            )
        except Exception:
            logger.warning("Failed to parse scope declaration: %s", path, exc_info=True)
            return None

    def check_boundary(
        self,
        change_id: str,
        base_ref: str | None = None,
        default_branch: str = "main",
    ) -> DriftDetection:
        """Compare actual changes against the declared scope for *change_id*.

        If no scope declaration exists, all changes are considered in-scope
        (the drift protection is advisory, not blocking without a scope).
        """
        scope = self.load_scope(change_id)

        base = resolve_diff_base(
            self._project_root,
            default_branch=default_branch,
            override_ref=base_ref,
        )

        files_changed, lines_added, lines_deleted = _run_git_diff(
            self._project_root, base
        )

        planned = list(scope.declared_files) if scope else []
        boundary = scope.boundary if scope else ScopeBoundary()

        # Detect files outside scope.
        files_out_of_scope: list[str] = []
        files_in_forbidden: list[str] = []

        if planned:
            planned_set = set(planned)
            for f in files_changed:
                if f not in planned_set:
                    files_out_of_scope.append(f)

        # Detect forbidden path access.
        if boundary.forbidden_paths:
            from fnmatch import fnmatch

            for f in files_changed:
                for forbidden in boundary.forbidden_paths:
                    if fnmatch(f, forbidden):
                        files_in_forbidden.append(f)
                        break

        # Detect decomposition triggers.
        triggers = self.detect_decomposition_trigger(
            files_changed=files_changed,
            lines_added=lines_added,
            boundary=boundary,
        )

        drift_detected = bool(files_out_of_scope or files_in_forbidden or triggers)

        return DriftDetection(
            planned_files=tuple(planned),
            actual_files_changed=tuple(files_changed),
            files_out_of_scope=tuple(files_out_of_scope),
            files_in_forbidden_paths=tuple(files_in_forbidden),
            lines_added=lines_added,
            lines_deleted=lines_deleted,
            triggers_decomposition=tuple(triggers),
            drift_detected=drift_detected,
        )

    @staticmethod
    def detect_decomposition_trigger(
        *,
        files_changed: list[str],
        lines_added: int,
        boundary: ScopeBoundary,
    ) -> list[DecompositionTrigger]:
        """Check whether the change exceeds *boundary* thresholds.

        Returns a list of triggers (empty if all thresholds are satisfied).
        """
        triggers: list[DecompositionTrigger] = []

        n_files = len(files_changed)
        if boundary.max_files > 0 and n_files > boundary.max_files:
            triggers.append(
                DecompositionTrigger(
                    triggered_by="max_files",
                    threshold=boundary.max_files,
                    actual=n_files,
                    recommendation=(
                        f"Change touches {n_files} files (threshold: "
                        f"{boundary.max_files}). Consider splitting into "
                        f"multiple smaller changes, each affecting at most "
                        f"{boundary.max_files} files."
                    ),
                )
            )

        if boundary.max_total_lines > 0 and lines_added > boundary.max_total_lines:
            triggers.append(
                DecompositionTrigger(
                    triggered_by="max_total_lines",
                    threshold=boundary.max_total_lines,
                    actual=lines_added,
                    recommendation=(
                        f"Change adds {lines_added} lines (threshold: "
                        f"{boundary.max_total_lines}). Consider splitting "
                        f"into smaller increments."
                    ),
                )
            )

        return triggers


# ---------------------------------------------------------------------------
# Gate hook registration — called at import time
# ---------------------------------------------------------------------------


def _gate_hook_drift(
    session,  # SessionState
    project_root: Path,
) -> list[str]:
    """IMPLEMENTATION hook: check for scope drift before entering implementation.

    Returns a list of failure message strings (empty = all passed).
    """
    failures: list[str] = []
    engine = DriftDetectionEngine(project_root)

    # Use the session's active change_id if available.
    change_id = getattr(session, "change_id", "") or getattr(session, "session_id", "")

    if not change_id:
        # No change_id — check if any scope declarations exist at all.
        scopes_dir = project_root / engine.SCOPES_DIR
        if not scopes_dir.is_dir() or not list(scopes_dir.glob("*.json")):
            return failures  # no scopes declared, drift check is advisory
        return failures

    drift = engine.check_boundary(change_id)

    if drift.files_out_of_scope:
        failures.append(
            f"Scope drift: {len(drift.files_out_of_scope)} file(s) outside "
            f"declared scope: {', '.join(list(drift.files_out_of_scope)[:5])}"
        )

    if drift.files_in_forbidden_paths:
        failures.append(
            f"Forbidden paths touched: {', '.join(drift.files_in_forbidden_paths)}"
        )

    if drift.triggers_decomposition:
        for t in drift.triggers_decomposition:
            failures.append(f"Decomposition trigger: {t.recommendation}")

    return failures


# Module-level registration — fires when drift is imported.
try:
    from .gates import HarnessLayer, register_gate_hook

    register_gate_hook(HarnessLayer.IMPLEMENTATION, _gate_hook_drift)
except ImportError:
    pass
