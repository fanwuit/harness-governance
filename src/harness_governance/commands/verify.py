"""``harness verify <preset>`` command.

Runs a named verification preset against the project. Built-in presets
delegate to existing commands so we don't duplicate logic.
"""

from __future__ import annotations

from pathlib import Path

import click

from ..messages import bilingual
from .check import check_entry, check_inventory, check_packets, check_routing


# Preset → (label, runner callable returning CheckResult)
_PRESETS: dict[str, str] = {
    "routing-guardrails": "routing",
    "packets": "packets",
    "entry": "entry",
    "inventory": "inventory",
    "all-local-checks": "all",
}


@click.command("verify")
@click.argument("preset")
@click.pass_context
def verify_cmd(ctx: click.Context, preset: str) -> None:
    """Run a verification preset.

    Built-in presets: ``routing-guardrails``, ``packets``, ``entry``,
    ``inventory``, ``all-local-checks``.
    """
    project_root: Path = ctx.obj.get("project_root", Path.cwd())

    if preset in _PRESETS:
        runner_name = _PRESETS[preset]
        runners = {
            "routing": check_routing,
            "packets": check_packets,
            "entry": check_entry,
            "inventory": check_inventory,
        }
        if runner_name == "all":
            results = [
                runners[k](project_root)
                for k in ("routing", "packets", "entry", "inventory")
            ]
            passed = all(r.passed for r in results)
            click.echo(
                bilingual("verify.passed" if passed else "verify.failed", preset=preset)
            )
            for r in results:
                click.echo(f"  {r.check}: {'pass' if r.passed else 'FAIL'}")
            if not passed:
                raise click.exceptions.Exit(code=1)
            return
        result = runners[runner_name](project_root)
        click.echo(
            bilingual(
                "verify.passed" if result.passed else "verify.failed", preset=preset
            )
        )
        if not result.passed:
            for finding in result.findings:
                click.echo(f"  - {finding.target}: {finding.message}")
            raise click.exceptions.Exit(code=1)
        return

    raise click.ClickException(
        bilingual(
            "verify.unknown_preset",
            preset=preset,
            available=", ".join(sorted(_PRESETS)),
        )
    )


__all__ = ["verify_cmd"]
