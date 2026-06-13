"""Tests for the file_ops cache helpers."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from harness_governance.file_ops import _cache
from harness_governance.file_ops._cache import (
    PACKET_CACHE,
    PacketCache,
    file_cache,
    reset_caches,
)


def test_file_cache_caches_until_mtime_changes(tmp_path: Path) -> None:
    target = tmp_path / "data.txt"
    target.write_text("v1", encoding="utf-8")

    call_count = {"n": 0}

    @file_cache
    def read(path: Path) -> str:
        call_count["n"] += 1
        return path.read_text(encoding="utf-8")

    assert read(target) == "v1"
    assert read(target) == "v1"
    assert call_count["n"] == 1

    target.write_text("v2", encoding="utf-8")
    # Force mtime to move forward (some filesystems have 1s resolution).
    new_time = time.time() + 2
    os.utime(target, (new_time, new_time))
    assert read(target) == "v2"
    assert call_count["n"] == 2


def test_file_cache_clear() -> None:
    target = Path("E:/nonexistent-test.txt")

    @file_cache
    def read(path: Path) -> str:
        return "x"

    read(target)
    read.cache_clear()  # type: ignore[attr-defined]
    assert read.cache_info().size == 0  # type: ignore[attr-defined]


def test_packet_cache_invalidates_on_mtime_change(tmp_path: Path) -> None:
    cache = PacketCache()
    target = tmp_path / "p"
    target.mkdir()
    cache.put(target, "value-1")
    assert cache.get(target) == "value-1"
    # Touch directory to advance mtime.
    new_time = time.time() + 2
    os.utime(target, (new_time, new_time))
    assert cache.get(target) is None


def test_packet_cache_lru_eviction(tmp_path: Path) -> None:
    cache = PacketCache(max_entries=2)
    a = tmp_path / "a"
    b = tmp_path / "b"
    c = tmp_path / "c"
    a.mkdir()
    b.mkdir()
    c.mkdir()
    cache.put(a, "A")
    cache.put(b, "B")
    cache.put(c, "C")  # evicts a
    assert cache.get(a) is None
    assert cache.get(b) == "B"
    assert cache.get(c) == "C"


def test_reset_caches_clears_module_state(tmp_path: Path) -> None:
    target = tmp_path / "p"
    target.mkdir()
    PACKET_CACHE.put(target, "v")
    reset_caches()
    assert PACKET_CACHE.get(target) is None
    # file_cache decorator stores its own state; reset via decorator.
    assert _cache.PACKET_CACHE is not None