"""``harness hook`` commands for optional local Git hook installation."""

from __future__ import annotations

from pathlib import Path

import click

from ..messages import bilingual
from .verify import is_harness_governance_repo

_TAG_RELEASE_MARKER = "harness-governance: tag-release pre-push"
_TAG_RELEASE_PRE_PUSH = f"""#!/bin/sh
# {_TAG_RELEASE_MARKER}

status=0

while read local_ref local_sha remote_ref remote_sha
do
  case "$local_ref" in
    refs/tags/*)
      echo "harness: tag push detected: $local_ref"
      harness verify local --release
      status=$?
      ;;
  esac
done

exit $status
"""


@click.group("hook")
def hook_group() -> None:
    """Install optional local Git hooks for this repository."""


@hook_group.command("install")
@click.option(
    "--tag-release",
    "tag_release",
    is_flag=True,
    default=False,
    help="Install a pre-push hook that verifies only tag pushes.",
)
@click.option(
    "--force",
    is_flag=True,
    default=False,
    help="Overwrite an existing pre-push hook.",
)
@click.pass_context
def hook_install_cmd(ctx: click.Context, tag_release: bool, force: bool) -> None:
    """Install a local Git hook.

    The tag-release hook currently targets harness-governance repository
    releases and calls ``harness verify local --release``.
    """
    if not tag_release:
        raise click.UsageError(bilingual("hook.install.requires_target"))

    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    if tag_release and not is_harness_governance_repo(project_root):
        raise click.ClickException(bilingual("hook.install.tag_release.self_repo_only"))

    git_dir = project_root / ".git"
    if not git_dir.is_dir():
        raise click.ClickException(bilingual("hook.install.no_git"))

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_path = hooks_dir / "pre-push"
    if hook_path.exists() and not force:
        text = hook_path.read_text(encoding="utf-8", errors="ignore")
        if _TAG_RELEASE_MARKER not in text:
            raise click.ClickException(bilingual("hook.install.exists"))

    hook_path.write_text(_TAG_RELEASE_PRE_PUSH, encoding="utf-8", newline="\n")
    try:
        hook_path.chmod(hook_path.stat().st_mode | 0o111)
    except OSError:
        pass

    if ctx.obj.get("json_output"):
        import json

        click.echo(
            json.dumps(
                {
                    "installed": True,
                    "hook": str(hook_path),
                    "tag_release": True,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    click.echo(bilingual("hook.install.tag_release", path=str(hook_path)))


__all__ = [
    "hook_group",
    "hook_install_cmd",
    "_TAG_RELEASE_MARKER",
    "_TAG_RELEASE_PRE_PUSH",
]
