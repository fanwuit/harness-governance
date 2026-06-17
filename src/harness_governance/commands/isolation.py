"""``harness isolation`` commands — role workspace isolation (Gap 1).

Creates per-role directories under ``.harness/isolation/``, validates
that file accesses stay within declared boundaries, and reports
cross-role violations.
"""

from __future__ import annotations

from pathlib import Path

import click

from ..messages import bilingual
from ..state_machine.isolation import (
    _CANONICAL_ROLES,
    _DEFAULT_ROLE_PATHS,
    _DEFAULT_ROLE_ALLOWANCES,
    IsolationManager,
)


@click.group("isolation")
def isolation_group() -> None:
    """Role workspace isolation management."""


# ---------------------------------------------------------------------------
# isolation init
# ---------------------------------------------------------------------------


@isolation_group.command("init")
@click.option("--session-id", required=True, help="Governance session ID.")
@click.option("--change-id", default="", help="Change/packet identifier.")
@click.option("--role", "roles", multiple=True, help="Roles to initialize (repeatable).")
@click.pass_context
def isolation_init(
    ctx: click.Context,
    session_id: str,
    change_id: str,
    roles: tuple[str, ...],
) -> None:
    """Create isolation workspaces for a session.

    Initializes one workspace per canonical role (or those specified
    via --role).  Each workspace is a directory with a scope declaration.
    """
    root = _resolve_root(ctx)
    mgr = IsolationManager(root)

    target_roles = list(roles) if roles else list(_CANONICAL_ROLES)

    for role in target_roles:
        ws = mgr.create_workspace(role, session_id, change_id)
        click.echo(
            bilingual(
                "isolation.workspace_created",
                role=role,
                path=ws.workspace_path,
            ),
        )

    click.echo(
        bilingual("isolation.init_done", count=len(target_roles), session=session_id),
    )


# ---------------------------------------------------------------------------
# isolation check
# ---------------------------------------------------------------------------


@isolation_group.command("check")
@click.option("--session-id", required=True, help="Governance session ID.")
@click.pass_context
def isolation_check(ctx: click.Context, session_id: str) -> None:
    """Verify isolation for a session — reports all violations."""
    root = _resolve_root(ctx)
    mgr = IsolationManager(root)
    summary = mgr.verify_workspace(session_id)

    click.echo(
        bilingual(
            "isolation.roles_found",
            roles=", ".join(summary.roles_isolated) if summary.roles_isolated else "none",
        ),
    )
    click.echo(
        bilingual(
            "isolation.workspaces_valid",
            valid="✓" if summary.workspaces_valid else "✗",
        ),
    )

    if summary.cross_role_violations:
        click.echo(bilingual("isolation.violations_header"), err=True)
        for v in summary.cross_role_violations:
            click.echo(
                f"  [{v.role}] {v.event}: {', '.join(v.files_touched)}",
                err=True,
            )

    if summary.files_outside_scope:
        click.echo(bilingual("isolation.out_of_scope_header"), err=True)
        for f in summary.files_outside_scope:
            click.echo(f"  {f}", err=True)

    if not summary.workspaces_valid:
        raise SystemExit(1)


# ---------------------------------------------------------------------------
# isolation list
# ---------------------------------------------------------------------------


@isolation_group.command("list")
@click.option("--session-id", required=True, help="Governance session ID.")
@click.pass_context
def isolation_list(ctx: click.Context, session_id: str) -> None:
    """List isolation workspace details for each role in a session."""
    root = _resolve_root(ctx)
    mgr = IsolationManager(root)

    for role in _CANONICAL_ROLES:
        ws = mgr.load_workspace(session_id, role)
        if ws is None:
            click.echo(f"  {role}: {bilingual('isolation.not_created')}")
            continue

        paths_str = ", ".join(ws.allowed_paths[:3])
        if len(ws.allowed_paths) > 3:
            paths_str += f" ... (+{len(ws.allowed_paths) - 3})"
        roles_str = ", ".join(ws.allowed_roles) if ws.allowed_roles else "none"

        click.echo(f"  {role}:")
        click.echo(f"    {bilingual('isolation.paths_label')}: {paths_str}")
        click.echo(f"    {bilingual('isolation.roles_label')}: {roles_str}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_root(ctx: click.Context) -> Path:
    """Resolve the project root from CLI context, defaulting to cwd."""
    if ctx.obj is not None and isinstance(ctx.obj, dict):
        root = ctx.obj.get("project_root")
        if root is not None:
            return Path(root)
    return Path.cwd()
