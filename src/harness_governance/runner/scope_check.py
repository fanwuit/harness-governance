"""Per-round scope budget checker for the autonomous runner.

After each round the runner calls :func:`check_scope_budget` to compare
the git diff since the round started against the task's
:class:`~harness_governance.models.schemas.ScopeBudget`.  If any
threshold is exceeded, the function returns a
:class:`ScopeBudgetViolation` that the loop uses to force a checkpoint
and (optionally) auto-decompose the remaining work.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path

from ..models.schemas import ScopeBudget


@dataclass(slots=True)
class ScopeBudgetViolation:
    """One scope-budget threshold breach detected after a round."""

    rule: str  # "max_files" | "max_diff_lines" | "forbidden_path"
    threshold: int = 0
    actual: int = 0
    detail: str = ""  # human-readable, e.g. the forbidden path


@dataclass(slots=True)
class ScopeCheckResult:
    """Aggregate result of a post-round scope budget check."""

    violations: tuple[ScopeBudgetViolation, ...] = ()
    files_changed: tuple[str, ...] = ()
    diff_lines: int = 0

    @property
    def exceeded(self) -> bool:
        return bool(self.violations)


def _git_diff_since(
    project_root: Path,
    base_ref: str,
) -> tuple[list[str], int]:
    """Return ``(files_changed, total_diff_lines)`` since *base_ref*.

    Falls back gracefully if git is unavailable or the repo has no
    commits yet.
    """
    files: list[str] = []
    diff_lines = 0

    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", base_ref],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            files = [
                line.strip() for line in result.stdout.splitlines() if line.strip()
            ]
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["git", "diff", "--numstat", base_ref],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                parts = line.split("\t")
                if len(parts) >= 2:
                    try:
                        diff_lines += int(parts[0]) if parts[0] != "-" else 0
                    except ValueError:
                        pass
    except Exception:
        pass

    return files, diff_lines


def check_scope_budget(
    project_root: Path,
    budget: ScopeBudget,
    base_ref: str,
) -> ScopeCheckResult:
    """Compare the current git diff against *budget* thresholds.

    Parameters
    ----------
    project_root:
        Repository root.
    budget:
        The :class:`ScopeBudget` from the current queue item (or a
        default from the project config).
    base_ref:
        Git ref to diff against — typically the SHA recorded before the
        round started, or ``HEAD`` for a quick check.
    """
    files_changed, diff_lines = _git_diff_since(project_root, base_ref)

    violations: list[ScopeBudgetViolation] = []

    # max_files
    if budget.max_files > 0 and len(files_changed) > budget.max_files:
        violations.append(
            ScopeBudgetViolation(
                rule="max_files",
                threshold=budget.max_files,
                actual=len(files_changed),
                detail=(
                    f"Change touches {len(files_changed)} files "
                    f"(budget: {budget.max_files})"
                ),
            )
        )

    # max_diff_lines
    if budget.max_diff_lines > 0 and diff_lines > budget.max_diff_lines:
        violations.append(
            ScopeBudgetViolation(
                rule="max_diff_lines",
                threshold=budget.max_diff_lines,
                actual=diff_lines,
                detail=(
                    f"Change adds {diff_lines} diff lines "
                    f"(budget: {budget.max_diff_lines})"
                ),
            )
        )

    # forbidden_paths
    if budget.forbidden_paths:
        for f in files_changed:
            for pattern in budget.forbidden_paths:
                if fnmatch(f, pattern):
                    violations.append(
                        ScopeBudgetViolation(
                            rule="forbidden_path",
                            detail=f"File '{f}' matches forbidden pattern '{pattern}'",
                        )
                    )
                    break  # one violation per file is enough

    return ScopeCheckResult(
        violations=tuple(violations),
        files_changed=tuple(files_changed),
        diff_lines=diff_lines,
    )


def resolve_round_base_ref(project_root: Path) -> str:
    """Return the git ref to use as the diff base for the current round.

    Tries ``HEAD`` first; if the repo has no commits yet, returns the
    git empty-tree hash so that *all* untracked content is counted.
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    # No commits yet — use the empty-tree hash.
    return "4b825dc642cb6eb9a060e54bf899d4e3c6e2c3a8"
