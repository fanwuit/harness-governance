"""``harness config`` command group.

Subcommands:

* ``harness config init``     — write ``.harness/config.toml`` from defaults.
* ``harness config show``       — display the effective configuration.
* ``harness config set``        — update one or more fields in ``config.toml``.
* ``harness config validate``   — check that ``config.toml`` is well-formed.
"""

from __future__ import annotations

import json
from pathlib import Path

import click

from ..config.defaults import DEFAULT_CONFIG_FILE, PLATFORM_SKILL_PATHS
from ..config.settings import load_config, write_default_config
from ..logging_setup import get_logger
from ..messages import bilingual
from .init import detect_platform

logger = get_logger("config")

# -- helpers ----------------------------------------------------------------


def _toml_value_repr(value: object) -> str:
    """Serialize a Python value to a TOML value literal."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value)
    if isinstance(value, Path):
        return json.dumps(str(value))
    if isinstance(value, (list, tuple)):
        items = ", ".join(json.dumps(str(v) if isinstance(v, Path) else v) for v in value)
        return f"[{items}]"
    return json.dumps(str(value))


def _read_and_update_toml(
    config_path: Path, updates: dict[str, object]
) -> str:
    """Read a flat TOML file, replace/add keys, return new content.

    Works for the simple flat schema used by ``.harness/config.toml``.
    Comments and blank lines that are *not* adjacent to a replaced key
    are preserved.
    """
    lines = config_path.read_text(encoding="utf-8").splitlines() if config_path.exists() else []
    updated_keys: set[str] = set()
    result: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            eq_pos = stripped.find("=")
            if eq_pos > 0:
                key = stripped[:eq_pos].strip()
                if key in updates:
                    result.append(f"{key} = {_toml_value_repr(updates[key])}")
                    updated_keys.add(key)
                    continue
        result.append(line)

    # Append keys that were not in the original file.
    for key, value in updates.items():
        if key not in updated_keys:
            result.append(f"{key} = {_toml_value_repr(value)}")

    return "\n".join(result) + "\n"


# -- click group -------------------------------------------------------------


@click.group("config")
def config_group() -> None:
    """Manage ``.harness/config.toml``."""


# -- config init -------------------------------------------------------------


@config_group.command("init")
@click.option(
    "--platform",
    "platform",
    default=None,
    type=click.Choice(sorted(PLATFORM_SKILL_PATHS)),
    help="Override automatic platform detection.",
)
@click.option("--force/--no-force", default=False, help="Overwrite existing config.")
@click.pass_context
def config_init_cmd(ctx: click.Context, platform: str | None, force: bool) -> None:
    """Initialize ``.harness/config.toml``."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    detected = platform or detect_platform(project_root)
    path = write_default_config(project_root, agent_platform=detected, force=force)
    logger.info("wrote config: %s", path)
    click.echo(bilingual("config.created", path=str(path)))
    click.echo(bilingual("config.platform", platform=detected))


# -- config show -------------------------------------------------------------


@config_group.command("show")
@click.pass_context
def config_show_cmd(ctx: click.Context) -> None:
    """Display the effective configuration."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    json_output: bool = ctx.obj.get("json_output", False)

    config = load_config(project_root)
    config_path = (project_root / DEFAULT_CONFIG_FILE).resolve()
    logger.debug("loaded config from %s", config_path)

    data = config.model_dump(mode="python")
    # Convert Path objects to strings for readability.
    for key, value in data.items():
        if isinstance(value, Path):
            data[key] = str(value)
        elif isinstance(value, tuple):
            data[key] = list(value)

    if json_output:
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        click.echo(bilingual("config.show_header", path=str(config_path)))
        click.echo("")
        for key, value in data.items():
            if key == "project_root":
                continue
            display = value if not isinstance(value, list) else ", ".join(str(v) for v in value)
            click.echo(f"  {key} = {display}")


# -- config set --------------------------------------------------------------


_FIELD_TYPES: dict[str, type] = {
    "agent_platform": str,
    "queue_file": str,
    "changes_root": str,
    "planning_root": str,
    "harness_dir": str,
    "entry_block_marker": str,
    "check_frequency": str,
}


@config_group.command("set")
@click.argument("pairs", nargs=-1, required=True)
@click.pass_context
def config_set_cmd(ctx: click.Context, pairs: tuple[str, ...]) -> None:
    """Update one or more config fields.  Example: ``harness config set check_frequency=always``."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    json_output: bool = ctx.obj.get("json_output", False)

    config_path = (project_root / DEFAULT_CONFIG_FILE).resolve()
    if not config_path.exists():
        raise click.ClickException(
            bilingual("config.not_found", path=str(config_path))
        )

    # Parse key=value pairs.
    updates: dict[str, object] = {}
    for pair in pairs:
        if "=" not in pair:
            raise click.BadParameter(
                bilingual("config.set_bad_format", value=pair),
                param_hint="PAIRS",
            )
        key, _, raw_value = pair.partition("=")
        key = key.strip()
        raw_value = raw_value.strip()
        if key not in _FIELD_TYPES:
            raise click.BadParameter(
                bilingual("config.unknown_field", field=key),
                param_hint="PAIRS",
            )
        updates[key] = raw_value

    logger.debug("updating %d field(s) in %s", len(updates), config_path)

    # Read-modify-write the TOML file.
    new_content = _read_and_update_toml(config_path, updates)
    config_path.write_text(new_content, encoding="utf-8")

    # Validate the result by reloading.
    try:
        config = load_config(project_root, config_file=config_path)
    except Exception as exc:
        raise click.ClickException(
            bilingual("config.validate_failed", error=str(exc))
        ) from exc

    if json_output:
        click.echo(json.dumps({"updated": list(updates.keys()), "valid": True}))
    else:
        for key in updates:
            click.echo(bilingual("config.set_ok", key=key, value=str(updates[key])))
        click.echo(bilingual("config.validate_passed"))


# -- config validate ---------------------------------------------------------


@config_group.command("validate")
@click.pass_context
def config_validate_cmd(ctx: click.Context) -> None:
    """Validate ``.harness/config.toml`` against the schema."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    json_output: bool = ctx.obj.get("json_output", False)

    config_path = (project_root / DEFAULT_CONFIG_FILE).resolve()
    if not config_path.exists():
        raise click.ClickException(
            bilingual("config.not_found", path=str(config_path))
        )

    try:
        config = load_config(project_root, config_file=config_path)
    except Exception as exc:
        if json_output:
            click.echo(json.dumps({"valid": False, "error": str(exc)}))
        else:
            click.echo(bilingual("config.validate_failed", error=str(exc)))
        raise SystemExit(1) from exc

    logger.info("config validation passed: %s", config_path)
    if json_output:
        click.echo(json.dumps({"valid": True, "fields": len(type(config).model_fields)}))
    else:
        click.echo(bilingual("config.validate_passed"))


__all__ = [
    "config_group",
    "config_init_cmd",
    "config_show_cmd",
    "config_set_cmd",
    "config_validate_cmd",
]
