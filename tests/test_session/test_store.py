"""Tests for session store operations."""

from __future__ import annotations

import json
from pathlib import Path

from harness_governance.session.state import SessionState
from harness_governance.session.store import (
    create_session,
    find_active_session,
    generate_session_id,
    list_sessions,
    load_session,
    save_session,
)
from harness_governance.state_machine.classification import RoutingPath
from harness_governance.state_machine.layers import HarnessLayer


class TestGenerateSessionId:
    def test_basic_slug(self) -> None:
        sid = generate_session_id("Fix login bug")
        assert sid.endswith("-fix-login-bug")
        assert len(sid.split("-", 1)[0]) == 8  # YYYYMMDD

    def test_special_chars_stripped(self) -> None:
        sid = generate_session_id("Add @#$ feature!")
        assert "@" not in sid
        assert "#" not in sid
        assert "$" not in sid
        assert "!" not in sid

    def test_long_description_truncated(self) -> None:
        sid = generate_session_id("A" * 200)
        slug = sid.split("-", 1)[1]
        assert len(slug) <= 40

    def test_empty_description_fallback(self) -> None:
        sid = generate_session_id("")
        assert sid.endswith("-session")


def _make_session(
    session_id: str = "20260616-test",
    *,
    status: str = "active",
    current_layer: HarnessLayer | None = HarnessLayer.INTAKE_ORIENTATION,
) -> SessionState:
    return SessionState(
        session_id=session_id,
        created_at="2026-06-16T10:00:00+00:00",
        description="Test session",
        routing_path=RoutingPath.GOVERNED_PATH,
        current_layer=current_layer,
        status=status,
    )


class TestCreateAndLoad:
    def test_create_writes_json(self, tmp_path: Path) -> None:
        state = _make_session()
        path = create_session(tmp_path, state)
        assert path.is_file()
        assert path.suffix == ".json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        assert raw["session_id"] == "20260616-test"

    def test_load_roundtrip(self, tmp_path: Path) -> None:
        state = _make_session()
        create_session(tmp_path, state)
        loaded = load_session(tmp_path, "20260616-test")
        assert loaded.session_id == state.session_id
        assert loaded.current_layer == state.current_layer
        assert loaded.routing_path == state.routing_path

    def test_load_missing_raises(self, tmp_path: Path) -> None:
        import pytest

        with pytest.raises(FileNotFoundError):
            load_session(tmp_path, "nonexistent")


class TestSaveAndFind:
    def test_save_overwrites(self, tmp_path: Path) -> None:
        state = _make_session()
        create_session(tmp_path, state)
        updated = state.model_copy(update={"current_layer": HarnessLayer.IDEA})
        save_session(tmp_path, updated)
        loaded = load_session(tmp_path, "20260616-test")
        assert loaded.current_layer == HarnessLayer.IDEA

    def test_find_active_returns_active(self, tmp_path: Path) -> None:
        state = _make_session()
        create_session(tmp_path, state)
        found = find_active_session(tmp_path)
        assert found is not None
        assert found.session_id == "20260616-test"

    def test_find_active_ignores_closed(self, tmp_path: Path) -> None:
        state = _make_session(status="closed")
        create_session(tmp_path, state)
        found = find_active_session(tmp_path)
        assert found is None

    def test_find_active_empty_dir(self, tmp_path: Path) -> None:
        assert find_active_session(tmp_path) is None


class TestListSessions:
    def test_list_all(self, tmp_path: Path) -> None:
        create_session(tmp_path, _make_session("20260616-a"))
        create_session(tmp_path, _make_session("20260616-b", status="closed"))
        sessions = list_sessions(tmp_path)
        assert len(sessions) == 2
        ids = {s.session_id for s in sessions}
        assert ids == {"20260616-a", "20260616-b"}

    def test_list_empty(self, tmp_path: Path) -> None:
        assert list_sessions(tmp_path) == []
