"""Harness config loader.

The loader is deliberately minimal: it reads ``.harness/config.toml``
when present, falls back to :data:`defaults` otherwise, and exposes the
result as a :class:`harness_governance.models.HarnessConfig` instance.

We avoid pulling in a full TOML library: Python 3.11+ ships
:class:`tomllib` and the schema is small enough to make hand-rolled
parsing unnecessary on older runtimes. On 3.10 we require ``tomli``
only if the file uses advanced syntax (the current schema does not).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from ..logging_setup import get_logger
from ..models.schemas import HarnessConfig
from .defaults import DEFAULT_CONFIG_FILE

logger = get_logger("config")

#: The current schema version for ``.harness/config.toml``.
#: When a loaded config has a lower version, :func:`_migrate` is called
#: to bring it up to date.
CURRENT_SCHEMA_VERSION: int = 1


def _migrate(raw: dict[str, Any], *, from_version: int) -> dict[str, Any]:
    """Apply sequential migrations from *from_version* to current.

    Each migration step is a function ``dict -> dict`` that returns the
    updated payload.  Migrations are idempotent — running them on an
    already-migrated config is a no-op.
    """
    payload = dict(raw)
    version = from_version

    # Example future migration (v1 -> v2):
    # if version < 2:
    #     payload.setdefault("new_field", "default_value")
    #     version = 2

    if version < CURRENT_SCHEMA_VERSION:
        logger.debug("no migrations needed (already at v%d)", version)
    payload["schema_version"] = CURRENT_SCHEMA_VERSION
    return payload

if sys.version_info >= (3, 11):  # pragma: no cover - branch covered by version gate
    import tomllib as _toml
else:  # pragma: no cover
    try:
        import tomli as _toml  # type: ignore[no-redef]
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "harness-governance requires Python 3.11+ or the 'tomli' package "
            "on 3.10 to read .harness/config.toml."
        ) from exc


def _coerce_path(value: object, *, base: Path) -> Path:
    if isinstance(value, Path):
        return value if value.is_absolute() else base / value
    if isinstance(value, str) and value:
        p = Path(value)
        return p if p.is_absolute() else base / p
    raise TypeError(f"Expected path string, got {type(value).__name__}: {value!r}")


def load_config(
    project_root: Path | None = None,
    *,
    config_file: Path | None = None,
) -> HarnessConfig:
    """Load ``.harness/config.toml`` (or fall back to defaults).

    Parameters
    ----------
    project_root:
        Root of the user's project. Defaults to the current working
        directory. All relative paths inside ``config.toml`` are
        resolved against this root.
    config_file:
        Override the config file location. Defaults to
        ``<project_root>/.harness/config.toml``.
    """
    root = (project_root or Path.cwd()).resolve()
    cfg_path = (config_file or (root / DEFAULT_CONFIG_FILE)).resolve()

    raw: dict[str, object] = {}
    if cfg_path.is_file():
        logger.debug("reading config: %s", cfg_path)
        with cfg_path.open("rb") as handle:
            raw = _toml.load(handle)
        logger.info("loaded %d field(s) from %s", len(raw), cfg_path)
    else:
        logger.debug("no config file at %s; using defaults", cfg_path)

    # Schema migration: bring old configs up to date.
    file_version = int(raw.get("schema_version", 0))
    if file_version < CURRENT_SCHEMA_VERSION:
        logger.info("migrating config from schema v%d to v%d",
                     file_version, CURRENT_SCHEMA_VERSION)
        raw = _migrate(raw, from_version=file_version)

    payload: dict[str, object] = dict(raw)
    payload.setdefault("project_root", root)
    payload["project_root"] = root

    for key in (
        "queue_file",
        "changes_root",
        "planning_root",
        "harness_dir",
    ):
        if key in raw:
            payload[key] = _coerce_path(raw[key], base=root)

    config = HarnessConfig.model_validate(payload)

    # Ensure all path fields are absolute, resolving defaults against root.
    # When no config file exists the Pydantic defaults are relative; this
    # guarantees downstream consumers always receive absolute paths.
    _path_fields = ("queue_file", "changes_root", "planning_root", "harness_dir")
    path_overrides: dict[str, Path] = {}
    for key in _path_fields:
        value = getattr(config, key)
        if not value.is_absolute():
            path_overrides[key] = root / value
    if path_overrides:
        config = config.model_copy(update=path_overrides)

    return config


def write_default_config(
    project_root: Path,
    *,
    agent_platform: str,
    force: bool = False,
) -> Path:
    """Write ``.harness/config.toml`` with defaults.

    Returns the absolute path of the written file.
    """
    config_path = (project_root / DEFAULT_CONFIG_FILE).resolve()
    if config_path.exists() and not force:
        return config_path

    config_path.parent.mkdir(parents=True, exist_ok=True)
    body = (
        "# Harness governance configuration.\n"
        "# Generated by `harness init`. Edit values to override defaults.\n"
        f"schema_version = {CURRENT_SCHEMA_VERSION}\n"
        f'agent_platform = "{agent_platform}"\n'
        'queue_file = "NEXT.md"\n'
        'changes_root = "docs/changes"\n'
        'planning_root = ".planning"\n'
        'harness_dir = ".harness"\n'
        'check_frequency = "targeted"\n'
        'require_session = true\n'
    )
    # Pure string literal — encoding="utf-8" (never utf-8-sig) guarantees
    # no BOM is emitted. No read->write round-trip here, so no BOM can
    # propagate; the project-wide no-BOM invariant holds.
    config_path.write_text(body, encoding="utf-8")
    return config_path