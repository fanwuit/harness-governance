"""Filesystem cache helpers for large repos.

Two patterns:

1. :func:`file_cache` — function decorator that caches a return value
   keyed by ``(args, kwargs)`` and invalidates when the underlying
   file's mtime changes. Used for read-only file walks like
   ``discover_packets`` and ``check_packet``.
2. :class:`PacketCache` — a small LRU keyed by packet directory,
   holding parsed packet summaries so :func:`check_all_packets` does
   not re-read the same files when called twice in one command.
"""

from __future__ import annotations

import functools
from collections import OrderedDict
from pathlib import Path
from typing import Any, Callable, ParamSpec, TypeVar

P = ParamSpec("P")
T = TypeVar("T")


def _mtime(path: Path) -> float:
    """Return the file's mtime, or ``-inf`` if it does not exist."""
    try:
        return path.stat().st_mtime
    except OSError:
        return float("-inf")


def file_cache(func: Callable[P, T]) -> Callable[P, T]:
    """Cache ``func``'s result, invalidating when the watched path changes.

    The decorated function must accept at least one :class:`Path` argument
    (the file or directory whose mtime gates the cache). All other
    arguments are part of the cache key.
    """
    store: "OrderedDict[tuple, tuple[T, float]]" = OrderedDict()
    cache_hits = 0
    cache_misses = 0
    max_entries = 256

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        nonlocal cache_hits, cache_misses
        # Pick the first Path-looking argument as the mtime watcher.
        watch_path: Path | None = None
        for arg in args:
            if isinstance(arg, Path):
                watch_path = arg
                break
        if watch_path is None:
            for v in kwargs.values():
                if isinstance(v, Path):
                    watch_path = v
                    break

        key = (args, tuple(sorted(kwargs.items())))
        mtime = _mtime(watch_path) if watch_path else float("-inf")
        cached = store.get(key)
        if cached is not None and cached[1] == mtime:
            cache_hits += 1
            store.move_to_end(key)
            return cached[0]
        cache_misses += 1
        result = func(*args, **kwargs)
        store[key] = (result, mtime)
        store.move_to_end(key)
        while len(store) > max_entries:
            store.popitem(last=False)
        return result

    wrapper.cache_info = lambda: type(  # type: ignore[attr-defined]
        "Info",
        (),
        {
            "hits": cache_hits,
            "misses": cache_misses,
            "size": len(store),
        },
    )()
    wrapper.cache_clear = store.clear  # type: ignore[attr-defined]
    return wrapper


class PacketCache:
    """Tiny LRU for parsed change packets."""

    def __init__(self, max_entries: int = 128) -> None:
        self._store: "OrderedDict[Path, tuple[Any, float]]" = OrderedDict()
        self._max = max_entries

    def get(self, packet_dir: Path) -> Any | None:
        entry = self._store.get(packet_dir)
        if entry is None:
            return None
        value, mtime = entry
        current = _mtime(packet_dir)
        if current != mtime:
            self._store.pop(packet_dir, None)
            return None
        self._store.move_to_end(packet_dir)
        return value

    def put(self, packet_dir: Path, value: Any) -> None:
        self._store[packet_dir] = (value, _mtime(packet_dir))
        self._store.move_to_end(packet_dir)
        while len(self._store) > self._max:
            self._store.popitem(last=False)

    def clear(self) -> None:
        self._store.clear()


# Process-wide caches. Tests call :func:`reset_caches` between cases.
PACKET_CACHE = PacketCache()


def reset_caches() -> None:
    """Reset all module-level caches (mainly for tests)."""
    PACKET_CACHE.clear()


__all__ = ["file_cache", "PacketCache", "PACKET_CACHE", "reset_caches"]
