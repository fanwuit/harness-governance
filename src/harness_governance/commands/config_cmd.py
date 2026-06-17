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
from ..config.settings import CURRENT_SCHEMA_VERSION, load_config, write_default_config
from ..file_ops._util import write_text_no_bom
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


def _validate_toml_text(
    project_root: Path, content: str, config_path: Path
) -> None:
    """Validate *content* by writing it to a temp file and loading it.

    The temp file is removed afterwards.  Raises whatever
    :func:`load_config` raises on invalid content.  Never touches the
    real *config_path*.
    """
    import tempfile

    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".toml",
        delete=False,
        encoding="utf-8",
    ) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)
    try:
        load_config(project_root, config_file=tmp_path)
    finally:
        try:
            tmp_path.unlink()
        except OSError:
            pass


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
    "require_session": bool,
    "schema_version": int,
    "blocked_statuses": list,
}

# Literal choices for fields that use Literal types in HarnessConfig.
_FIELD_CHOICES: dict[str, tuple[str, ...]] = {
    "agent_platform": (
        "claude-code", "codex", "cline", "cursor",
        "opencode", "windsurf", "qoderwork", "generic", "multi",
    ),
    "check_frequency": ("targeted", "phase-closeout", "always"),
}


def _coerce_value(key: str, raw_value: str) -> object:
    """Coerce a CLI string into the proper Python type for *key*.

    Raises :class:`click.BadParameter` on type/choice mismatches.
    """
    field_type = _FIELD_TYPES.get(key, str)

    if field_type is bool:
        lowered = raw_value.lower()
        if lowered in ("true", "1", "yes", "on"):
            return True
        if lowered in ("false", "0", "no", "off"):
            return False
        raise click.BadParameter(
            f"Field {key!r} expects a boolean (true/false), got {raw_value!r}.",
            param_hint="PAIRS",
        )

    if field_type is int:
        try:
            return int(raw_value)
        except ValueError as exc:
            raise click.BadParameter(
                f"Field {key!r} expects an integer, got {raw_value!r}.",
                param_hint="PAIRS",
            ) from exc

    if field_type is list:
        # Comma-separated → tuple of stripped strings (matches blocked_statuses shape).
        items = tuple(s.strip() for s in raw_value.split(",") if s.strip())
        return items

    # str (and any other type falls back to str).
    choices = _FIELD_CHOICES.get(key)
    if choices and raw_value not in choices:
        raise click.BadParameter(
            f"Field {key!r} must be one of {', '.join(choices)}, got {raw_value!r}.",
            param_hint="PAIRS",
        )
    return raw_value


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

    # Parse key=value pairs and coerce to the proper type.
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
        updates[key] = _coerce_value(key, raw_value)

    logger.debug("updating %d field(s) in %s", len(updates), config_path)

    # Read-modify-write the TOML file. Validate the new content in-memory
    # *before* touching the on-disk file so a bad value cannot corrupt it.
    new_content = _read_and_update_toml(config_path, updates)
    try:
        _validate_toml_text(project_root, new_content, config_path)
    except Exception as exc:
        raise click.ClickException(
            bilingual("config.validate_failed", error=str(exc))
        ) from exc

    write_text_no_bom(config_path, new_content)

    # Reload to confirm (defensive — should match the in-memory check above).
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


# -- config migrate --------------------------------------------------------


@config_group.command("migrate")
@click.pass_context
def config_migrate_cmd(ctx: click.Context) -> None:
    """Migrate ``.harness/config.toml`` to the current schema version."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    json_output: bool = ctx.obj.get("json_output", False)

    config_path = (project_root / DEFAULT_CONFIG_FILE).resolve()
    if not config_path.exists():
        raise click.ClickException(
            bilingual("config.not_found", path=str(config_path))
        )

    # Read the raw TOML to detect the file's schema version.
    import sys
    if sys.version_info >= (3, 11):
        import tomllib as _toml
    else:
        import tomli as _toml  # type: ignore[no-redef]

    with config_path.open("rb") as fh:
        raw = _toml.load(fh)

    file_version = int(raw.get("schema_version", 0))

    if file_version >= CURRENT_SCHEMA_VERSION:
        logger.info("config already at schema v%d", file_version)
        if json_output:
            click.echo(json.dumps({
                "migrated": False,
                "version": file_version,
            }))
        else:
            click.echo(bilingual("config.migrate_already_current", version=str(file_version)))
        return

    # Apply migration: rewrite the file with schema_version and any new fields.
    from ..config.settings import _migrate
    migrated = _migrate(raw, from_version=file_version)

    # Serialize back to TOML (simple flat schema).
    lines = [
        "# Harness governance configuration.",
        f"schema_version = {CURRENT_SCHEMA_VERSION}",
    ]
    for key, value in migrated.items():
        if key == "schema_version":
            continue
        lines.append(f"{key} = {_toml_value_repr(value)}")
    write_text_no_bom(config_path, "\n".join(lines) + "\n")

    logger.info("migrated config from v%d to v%d", file_version, CURRENT_SCHEMA_VERSION)
    if json_output:
        click.echo(json.dumps({
            "migrated": True,
            "from": file_version,
            "to": CURRENT_SCHEMA_VERSION,
        }))
    else:
        click.echo(bilingual(
            "config.migrate_done",
            old=str(file_version),
            new=str(CURRENT_SCHEMA_VERSION),
        ))


__all__ = [
    "config_group",
    "config_init_cmd",
    "config_show_cmd",
    "config_set_cmd",
    "config_validate_cmd",
    "config_migrate_cmd",
]
