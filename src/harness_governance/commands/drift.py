"""``harness drift`` commands — scope drift detection (Gap 3).

Compares actual git changes against declared scope boundaries and
triggers decomposition suggestions when thresholds are exceeded.
"""

from __future__ import annotations

import click

from ..messages import bilingual
from ..models.schemas import (
    ScopeBoundary,
    ScopeDeclaration,
)
from ..state_machine.drift import DriftDetectionEngine, resolve_diff_base
from ._util import resolve_root


@click.group("drift")
def drift_group() -> None:
    """Scope drift detection and boundary enforcement."""


# ---------------------------------------------------------------------------
# drift check
# ---------------------------------------------------------------------------


@drift_group.command("check")
@click.option("--change-id", required=True, help="Change/packet identifier.")
@click.option(
    "--base-ref",
    default=None,
    help="Git ref to diff against (auto-detected if omitted).",
)
@click.option(
    "--default-branch", default="main", help="Default branch name for merge-base."
)
@click.pass_context
def drift_check(
    ctx: click.Context,
    change_id: str,
    base_ref: str | None,
    default_branch: str,
) -> None:
    """Compare actual changes against the declared scope."""
    root = resolve_root(ctx)
    engine = DriftDetectionEngine(root)
    drift = engine.check_boundary(
        change_id, base_ref=base_ref, default_branch=default_branch
    )

    base = resolve_diff_base(root, default_branch=default_branch, override_ref=base_ref)

    click.echo(bilingual("drift.base_ref", ref=base[:8]))
    click.echo(
        bilingual(
            "drift.files_changed",
            count=len(drift.actual_files_changed),
        ),
    )
    click.echo(
        bilingual(
            "drift.line_stats",
            added=drift.lines_added,
            deleted=drift.lines_deleted,
        ),
    )

    if drift.files_out_of_scope:
        click.echo(bilingual("drift.out_of_scope"), err=True)
        for f in drift.files_out_of_scope:
            click.echo(f"  {f}", err=True)

    if drift.files_in_forbidden_paths:
        click.echo(bilingual("drift.forbidden_paths"), err=True)
        for f in drift.files_in_forbidden_paths:
            click.echo(f"  {f}", err=True)

    if drift.triggers_decomposition:
        click.echo(bilingual("drift.decomposition_triggered"), err=True)
        for t in drift.triggers_decomposition:
            click.echo(f"  [{t.triggered_by}] {t.recommendation}", err=True)

    if drift.drift_detected:
        click.echo(bilingual("drift.detected"), err=True)
        raise SystemExit(1)

    click.echo(bilingual("drift.clean"))


# ---------------------------------------------------------------------------
# drift scope
# ---------------------------------------------------------------------------


@drift_group.command("scope")
@click.option("--change-id", required=True, help="Change/packet identifier.")
@click.option("--session-id", default="", help="Governance session ID.")
@click.option("--file", "files", multiple=True, help="File path in scope (repeatable).")
@click.option(
    "--forbidden",
    "forbidden_paths",
    multiple=True,
    help="Forbidden glob pattern (repeatable).",
)
@click.option(
    "--max-files", type=int, default=0, help="Max files before decomposition trigger."
)
@click.option(
    "--max-lines",
    type=int,
    default=0,
    help="Max total added lines before decomposition trigger.",
)
@click.option(
    "--tier",
    default="standard",
    type=click.Choice(["strict", "standard", "light"]),
    help="Use preset thresholds for this rigor tier.",
)
@click.pass_context
def drift_scope(
    ctx: click.Context,
    change_id: str,
    session_id: str,
    files: tuple[str, ...],
    forbidden_paths: tuple[str, ...],
    max_files: int,
    max_lines: int,
    tier: str,
) -> None:
    """Declare or update the scope boundary for a change."""
    root = resolve_root(ctx)
    engine = DriftDetectionEngine(root)

    # Load existing scope if present, or create from tier defaults.
    existing = engine.load_scope(change_id)
    if existing is not None:
        boundary = existing.boundary
        declared_files = list(existing.declared_files)
    else:
        boundary = ScopeBoundary.for_tier(tier)
        declared_files = []

    # Override thresholds if explicitly provided.
    if max_files > 0:
        boundary.max_files = max_files
    if max_lines > 0:
        boundary.max_total_lines = max_lines
    if forbidden_paths:
        boundary.forbidden_paths = (*boundary.forbidden_paths, *forbidden_paths)
    if files:
        declared_files.extend(files)

    declaration = ScopeDeclaration(
        change_id=change_id,
        session_id=session_id,
        boundary=boundary,
        declared_files=tuple(sorted(set(declared_files))),
    )

    path = engine.declare_scope(declaration)
    click.echo(
        bilingual(
            "drift.scope_saved",
            change_id=change_id,
            path=str(path.relative_to(root)),
            files=len(declaration.declared_files),
            max_files=boundary.max_files,
            max_lines=boundary.max_total_lines,
        ),
    )


# ---------------------------------------------------------------------------
# drift boundary
# ---------------------------------------------------------------------------


@drift_group.command("boundary")
@click.option("--change-id", required=True, help="Change/packet identifier.")
@click.pass_context
def drift_boundary(ctx: click.Context, change_id: str) -> None:
    """Show the current scope boundary for a change."""
    root = resolve_root(ctx)
    engine = DriftDetectionEngine(root)
    scope = engine.load_scope(change_id)

    if scope is None:
        click.echo(bilingual("drift.no_scope"), err=True)
        raise SystemExit(1)

    click.echo(bilingual("drift.boundary_header", change_id=change_id))
    click.echo(f"  Max files: {scope.boundary.max_files or '∞'}")
    click.echo(f"  Max lines per file: {scope.boundary.max_lines_per_file or '∞'}")
    click.echo(f"  Max total added lines: {scope.boundary.max_total_lines or '∞'}")

    if scope.declared_files:
        click.echo(f"  Declared files ({len(scope.declared_files)}):")
        for f in scope.declared_files:
            click.echo(f"    {f}")

    if scope.boundary.allowed_paths:
        click.echo("  Allowed paths:")
        for p in scope.boundary.allowed_paths:
            click.echo(f"    {p}")

    if scope.boundary.forbidden_paths:
        click.echo("  Forbidden paths:")
        for p in scope.boundary.forbidden_paths:
            click.echo(f"    {p}")
