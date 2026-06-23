"""``harness verify <preset>`` command.

Runs a named verification preset against the project. Built-in presets
delegate to existing commands so we don't duplicate logic.
"""

from __future__ import annotations

import glob
import subprocess
import sys
import zipfile
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
    "local": "all",
}

_RELEASE_COMMANDS: tuple[tuple[str, ...], ...] = (
    (sys.executable, "-m", "ruff", "format", "--check", "src/", "tests/"),
    (sys.executable, "-m", "ruff", "check", "src/", "tests/"),
    (sys.executable, "-m", "mypy", "src/"),
    (sys.executable, "-m", "pytest"),
    (sys.executable, "-m", "build", "--wheel"),
)


def is_harness_governance_repo(project_root: Path) -> bool:
    """Return True only for the harness-governance source repository."""
    pyproject = project_root / "pyproject.toml"
    package_root = project_root / "src" / "harness_governance"
    if not pyproject.is_file() or not package_root.is_dir():
        return False
    text = pyproject.read_text(encoding="utf-8")
    return (
        'name = "harness-governance"' in text or "name = 'harness-governance'" in text
    )


@click.command("verify")
@click.argument("preset")
@click.option(
    "--release",
    "release",
    is_flag=True,
    default=False,
    help="Run harness-governance repository release/tag readiness checks.",
)
@click.pass_context
def verify_cmd(ctx: click.Context, preset: str, release: bool) -> None:
    """Run a verification preset.

    Built-in presets: ``routing-guardrails``, ``packets``, ``entry``,
    ``inventory``, ``all-local-checks``, ``local --release``.

    ``local --release`` is currently scoped to this harness-governance
    repository's Python package release flow, not a generic derived-project
    release policy.
    """
    project_root: Path = ctx.obj.get("project_root", Path.cwd())

    if preset == "local" and release:
        _run_release_verification(project_root)
        return

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


def _run_release_verification(project_root: Path) -> None:
    if not is_harness_governance_repo(project_root):
        raise click.ClickException(bilingual("verify.release.self_repo_only"))

    failures: list[str] = []
    for command in _RELEASE_COMMANDS:
        label = " ".join(command)
        click.echo(f"release: {label}")
        completed = subprocess.run(command, cwd=project_root, text=True)
        if completed.returncode != 0:
            failures.append(label)
            break

    if not failures and not _verify_wheel_contents(project_root):
        failures.append("wheel contents")

    if failures:
        click.echo(bilingual("verify.failed", preset="local --release"))
        raise click.exceptions.Exit(code=1)

    click.echo(bilingual("verify.passed", preset="local --release"))


def _verify_wheel_contents(project_root: Path) -> bool:
    wheels = glob.glob(str(project_root / "dist" / "*.whl"))
    if not wheels:
        click.echo("MISSING wheel: dist/*.whl")
        return False

    required = (
        "data/templates/",
        "data/references/",
        "data/skills/",
        "data/role-prompts/",
    )
    with zipfile.ZipFile(wheels[0]) as zf:
        names = zf.namelist()
        missing = [item for item in required if not any(item in name for name in names)]
    if missing:
        click.echo(f"MISSING in wheel: {missing}")
        return False

    click.echo(f"Wheel OK: {Path(wheels[0]).name}")
    return True


__all__ = [
    "verify_cmd",
    "is_harness_governance_repo",
    "_run_release_verification",
    "_verify_wheel_contents",
]
