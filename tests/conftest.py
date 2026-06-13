"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """Provide a clean project root for the test."""
    return tmp_path


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