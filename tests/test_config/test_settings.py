"""Tests for the harness config loader (``config.settings``)."""

from __future__ import annotations

from pathlib import Path

import pytest

from harness_governance.config.settings import (
    CURRENT_SCHEMA_VERSION,
    _coerce_path,
    _migrate,
    load_config,
    write_default_config,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_toml(cfg_dir: Path, content: str) -> Path:
    """Write *content* into ``<cfg_dir>/config.toml`` and return its path."""
    cfg_dir.mkdir(parents=True, exist_ok=True)
    toml_path = cfg_dir / "config.toml"
    toml_path.write_text(content, encoding="utf-8")
    return toml_path


# ===================================================================
# load_config — defaults (no config file)
# ===================================================================


class TestLoadConfigDefaults:
    """When no config.toml exists, load_config returns sane defaults."""

    def test_returns_defaults_when_no_file(self, tmp_path: Path) -> None:
        cfg = load_config(tmp_path)

        assert cfg.project_root == tmp_path.resolve()
        assert cfg.schema_version == CURRENT_SCHEMA_VERSION
        assert cfg.agent_platform == "claude-code"
        assert cfg.require_session is True

    def test_default_paths_are_absolute(self, tmp_path: Path) -> None:
        cfg = load_config(tmp_path)

        assert cfg.queue_file.is_absolute()
        assert cfg.changes_root.is_absolute()
        assert cfg.planning_root.is_absolute()
        assert cfg.harness_dir.is_absolute()

    def test_default_paths_resolved_against_root(self, tmp_path: Path) -> None:
        cfg = load_config(tmp_path)
        root = tmp_path.resolve()

        assert cfg.queue_file == root / "NEXT.md"
        assert cfg.changes_root == root / "docs" / "changes"
        assert cfg.planning_root == root / ".planning"
        assert cfg.harness_dir == root / ".harness"

    def test_project_root_is_set_to_provided_root(self, tmp_path: Path) -> None:
        cfg = load_config(tmp_path)
        assert cfg.project_root == tmp_path.resolve()


# ===================================================================
# load_config — valid config.toml
# ===================================================================


class TestLoadConfigFromFile:
    """load_config correctly parses a valid config.toml."""

    def test_parses_all_declared_fields(self, tmp_path: Path) -> None:
        cfg_dir = tmp_path / ".harness"
        _write_toml(
            cfg_dir,
            (
                "schema_version = 1\n"
                'agent_platform = "generic"\n'
                'queue_file = "TODO.md"\n'
                'changes_root = "changelog"\n'
                'planning_root = "plans"\n'
                'harness_dir = ".hg"\n'
                'check_frequency = "always"\n'
                "require_session = false\n"
            ),
        )

        cfg = load_config(tmp_path)

        assert cfg.schema_version == 1
        assert cfg.agent_platform == "generic"
        assert cfg.queue_file == tmp_path.resolve() / "TODO.md"
        assert cfg.changes_root == tmp_path.resolve() / "changelog"
        assert cfg.planning_root == tmp_path.resolve() / "plans"
        assert cfg.harness_dir == tmp_path.resolve() / ".hg"
        assert cfg.check_frequency == "always"
        assert cfg.require_session is False

    def test_path_fields_are_absolutized(self, tmp_path: Path) -> None:
        cfg_dir = tmp_path / ".harness"
        _write_toml(
            cfg_dir,
            (
                "schema_version = 1\n"
                'agent_platform = "generic"\n'
                'queue_file = "rel/path.md"\n'
            ),
        )

        cfg = load_config(tmp_path)
        assert cfg.queue_file.is_absolute()
        assert cfg.queue_file == tmp_path.resolve() / "rel" / "path.md"

    def test_absolute_path_in_config_kept_as_is(self, tmp_path: Path) -> None:
        abs_path = tmp_path / "absolute_queue.md"
        cfg_dir = tmp_path / ".harness"
        _write_toml(
            cfg_dir,
            (
                "schema_version = 1\n"
                'agent_platform = "generic"\n'
                f'queue_file = "{abs_path.as_posix()}"\n'
            ),
        )

        cfg = load_config(tmp_path)
        assert cfg.queue_file == abs_path

    def test_project_root_always_set_to_provided_root(self, tmp_path: Path) -> None:
        """Even when config.toml is present, project_root is forced to the arg."""
        cfg_dir = tmp_path / ".harness"
        _write_toml(
            cfg_dir,
            'schema_version = 1\nagent_platform = "generic"\n',
        )

        cfg = load_config(tmp_path)
        assert cfg.project_root == tmp_path.resolve()

    def test_partial_config_fills_defaults(self, tmp_path: Path) -> None:
        cfg_dir = tmp_path / ".harness"
        _write_toml(
            cfg_dir,
            'schema_version = 1\nagent_platform = "codex"\n',
        )

        cfg = load_config(tmp_path)
        assert cfg.agent_platform == "codex"
        # Defaults for path fields are still resolved against root.
        assert cfg.queue_file == tmp_path.resolve() / "NEXT.md"
        assert cfg.require_session is True

    def test_minimal_config_toml(self, tmp_path: Path) -> None:
        cfg_dir = tmp_path / ".harness"
        _write_toml(cfg_dir, 'schema_version = 1\nagent_platform = "generic"\n')

        cfg = load_config(tmp_path)
        assert cfg.schema_version == 1
        assert cfg.agent_platform == "generic"


# ===================================================================
# load_config — unknown fields (extra="forbid")
# ===================================================================


class TestLoadConfigUnknownFields:
    """HarnessConfig uses extra='forbid', so unknown TOML keys must raise."""

    def test_unknown_field_raises(self, tmp_path: Path) -> None:
        cfg_dir = tmp_path / ".harness"
        _write_toml(
            cfg_dir,
            (
                "schema_version = 1\n"
                'agent_platform = "generic"\n'
                'totally_bogus_field = "oops"\n'
            ),
        )

        with pytest.raises(Exception):
            load_config(tmp_path)

    def test_typo_in_field_name_raises(self, tmp_path: Path) -> None:
        cfg_dir = tmp_path / ".harness"
        _write_toml(
            cfg_dir,
            (
                "schema_version = 1\n"
                'agent_platfrom = "generic"\n'  # intentional typo
            ),
        )

        with pytest.raises(Exception):
            load_config(tmp_path)


# ===================================================================
# _coerce_path
# ===================================================================


class TestCoercePath:
    """Unit tests for the internal ``_coerce_path`` helper."""

    def test_relative_string_resolved_against_base(self, tmp_path: Path) -> None:
        result = _coerce_path("sub/dir", base=tmp_path)
        assert result == tmp_path / "sub" / "dir"
        assert result.is_absolute()

    def test_absolute_string_kept_as_is(self, tmp_path: Path) -> None:
        abs_path = tmp_path / "abs" / "path"
        result = _coerce_path(str(abs_path), base=tmp_path)
        assert result == abs_path

    def test_relative_path_object_resolved(self, tmp_path: Path) -> None:
        result = _coerce_path(Path("relative/file.md"), base=tmp_path)
        assert result == tmp_path / "relative" / "file.md"
        assert result.is_absolute()

    def test_absolute_path_object_kept(self, tmp_path: Path) -> None:
        abs_p = tmp_path / "absolute" / "path" / "file.md"
        assert abs_p.is_absolute()
        result = _coerce_path(abs_p, base=tmp_path)
        assert result == abs_p

    def test_empty_string_raises_type_error(self, tmp_path: Path) -> None:
        with pytest.raises(TypeError):
            _coerce_path("", base=tmp_path)

    def test_none_raises_type_error(self, tmp_path: Path) -> None:
        with pytest.raises(TypeError):
            _coerce_path(None, base=tmp_path)

    def test_integer_raises_type_error(self, tmp_path: Path) -> None:
        with pytest.raises(TypeError):
            _coerce_path(42, base=tmp_path)

    def test_bool_raises_type_error(self, tmp_path: Path) -> None:
        with pytest.raises(TypeError):
            _coerce_path(True, base=tmp_path)


# ===================================================================
# _migrate
# ===================================================================


class TestMigrate:
    """Schema migration helper."""

    def test_adds_schema_version(self) -> None:
        raw = {"agent_platform": "generic"}
        result = _migrate(raw, from_version=0)
        assert result["schema_version"] == CURRENT_SCHEMA_VERSION

    def test_idempotent(self) -> None:
        raw = {"agent_platform": "generic", "schema_version": CURRENT_SCHEMA_VERSION}
        result = _migrate(raw, from_version=CURRENT_SCHEMA_VERSION)
        assert result["schema_version"] == CURRENT_SCHEMA_VERSION

    def test_preserves_existing_fields(self) -> None:
        raw = {"agent_platform": "codex", "require_session": False}
        result = _migrate(raw, from_version=0)
        assert result["agent_platform"] == "codex"
        assert result["require_session"] is False

    def test_does_not_mutate_input(self) -> None:
        raw = {"agent_platform": "generic"}
        original = dict(raw)
        _migrate(raw, from_version=0)
        assert raw == original

    def test_schema_version_overrides_old_value(self) -> None:
        raw = {"schema_version": 0}
        result = _migrate(raw, from_version=0)
        assert result["schema_version"] == CURRENT_SCHEMA_VERSION


# ===================================================================
# write_default_config
# ===================================================================


class TestWriteDefaultConfig:
    """write_default_config writes correct TOML and respects the force flag."""

    def test_writes_config_toml(self, tmp_path: Path) -> None:
        result_path = write_default_config(tmp_path, agent_platform="generic")

        assert result_path.exists()
        assert result_path == (tmp_path / ".harness" / "config.toml").resolve()

    def test_written_content_is_valid_toml(self, tmp_path: Path) -> None:
        import sys

        if sys.version_info >= (3, 11):
            import tomllib
        else:
            tomllib = pytest.importorskip("tomli")

        write_default_config(tmp_path, agent_platform="claude-code")
        toml_path = tmp_path / ".harness" / "config.toml"

        with toml_path.open("rb") as fh:
            data = tomllib.load(fh)

        assert data["schema_version"] == CURRENT_SCHEMA_VERSION
        assert data["agent_platform"] == "claude-code"
        assert "queue_file" in data
        assert "changes_root" in data
        assert "planning_root" in data
        assert "harness_dir" in data
        assert "check_frequency" in data
        assert data["require_session"] is True

    def test_creates_parent_directory(self, tmp_path: Path) -> None:
        write_default_config(tmp_path, agent_platform="generic")
        assert (tmp_path / ".harness").is_dir()

    def test_does_not_overwrite_existing_without_force(self, tmp_path: Path) -> None:
        cfg_dir = tmp_path / ".harness"
        cfg_dir.mkdir()
        toml_path = cfg_dir / "config.toml"
        toml_path.write_text("# custom content\n", encoding="utf-8")

        write_default_config(tmp_path, agent_platform="generic", force=False)

        # Original content must be preserved.
        assert toml_path.read_text(encoding="utf-8") == "# custom content\n"

    def test_force_overwrites_existing(self, tmp_path: Path) -> None:
        cfg_dir = tmp_path / ".harness"
        cfg_dir.mkdir()
        toml_path = cfg_dir / "config.toml"
        toml_path.write_text("# stale\n", encoding="utf-8")

        write_default_config(tmp_path, agent_platform="codex", force=True)

        content = toml_path.read_text(encoding="utf-8")
        assert "codex" in content
        assert "# stale" not in content

    def test_returns_absolute_path(self, tmp_path: Path) -> None:
        result = write_default_config(tmp_path, agent_platform="generic")
        assert result.is_absolute()

    def test_round_trip_with_load_config(self, tmp_path: Path) -> None:
        """Config written by write_default_config should be loadable."""
        write_default_config(tmp_path, agent_platform="generic")
        cfg = load_config(tmp_path)

        assert cfg.agent_platform == "generic"
        assert cfg.schema_version == CURRENT_SCHEMA_VERSION
        assert cfg.project_root == tmp_path.resolve()


# ===================================================================
# load_config — edge cases
# ===================================================================


class TestLoadConfigEdgeCases:
    """Miscellaneous edge cases for load_config."""

    def test_custom_config_file_path(self, tmp_path: Path) -> None:
        custom_dir = tmp_path / "custom_cfg"
        custom_dir.mkdir()
        custom_toml = custom_dir / "my_config.toml"
        custom_toml.write_text(
            'schema_version = 1\nagent_platform = "cursor"\n',
            encoding="utf-8",
        )

        cfg = load_config(tmp_path, config_file=custom_toml)
        assert cfg.agent_platform == "cursor"
        assert cfg.project_root == tmp_path.resolve()

    def test_no_config_file_migrates_from_zero(self, tmp_path: Path) -> None:
        """Without a config file the raw dict is empty (version=0); migration runs."""
        cfg = load_config(tmp_path)
        assert cfg.schema_version == CURRENT_SCHEMA_VERSION
