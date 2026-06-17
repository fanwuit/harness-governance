"""Shared helpers for CLI command modules."""

from __future__ import annotations

from pathlib import Path

import click


def resolve_root(ctx: click.Context) -> Path:
    """Resolve the project root from CLI context, defaulting to cwd."""
    if ctx.obj is not None and isinstance(ctx.obj, dict):
        root = ctx.obj.get("project_root")
        if root is not None:
            return Path(root)
    return Path.cwd()


__all__ = ["resolve_root"]
