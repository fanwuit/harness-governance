"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """Provide a clean project root for the test."""
    return tmp_path


def write_permissive_config(project_root: Path) -> Path:
    """Write a config with ``require_session = false`` for tests that
    don't need session enforcement. Returns the config path.
    """
    cfg_dir = project_root / ".harness"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    cfg = cfg_dir / "config.toml"
    cfg.write_text(
        'schema_version = 1\nrequire_session = false\n',
        encoding="utf-8",
    )
    return cfg


def seed_session(project_root: Path, *, session_id: str = "20260616-test") -> str:
    """Create a minimal active session so that governed commands pass
    the session gate. Returns the session ID.
    """
    from harness_governance.session import SessionState, create_session
    from harness_governance.state_machine.classification import RoutingPath
    from harness_governance.state_machine.layers import HarnessLayer

    state = SessionState(
        session_id=session_id,
        created_at="2026-06-16T10:00:00+00:00",
        description="Test seed",
        routing_path=RoutingPath.GOVERNED_PATH,
        current_layer=HarnessLayer.INTAKE_ORIENTATION,
    )
    create_session(project_root, state)
    return session_id


@pytest.fixture
def packet_templates_dir() -> Path:
    """Absolute path to the bundled change-packet templates."""
    from importlib import resources

    return Path(str(resources.files("harness_governance.data.templates.change-packet")))


@pytest.fixture
def planning_templates_dir() -> Path:
    """Absolute path to the bundled planning templates."""
    from importlib import resources

    return Path(str(resources.files("harness_governance.data.templates.planning")))