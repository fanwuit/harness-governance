"""Thread-safe / process-safe NDJSON append with file locking.

Used by isolation, alignment, drift, and skill-chain modules to write
event records without interleaved corruption when multiple subagents
write concurrently.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

_LOCK_TIMEOUT = 5.0  # seconds
_IS_WINDOWS = sys.platform == "win32"

if _IS_WINDOWS:
    import msvcrt

    def _lock_file(fd: int) -> bool:
        """Acquire an exclusive lock on byte 0 of *fd*.  Returns True on success.

        ``msvcrt.locking`` locks bytes starting at the current file
        position, so we explicitly seek to byte 0 before locking.  This
        gives mutual exclusion regardless of where the previous
        ``os.write`` left the offset.
        """
        deadline = time.perf_counter() + _LOCK_TIMEOUT
        while True:
            try:
                os.lseek(fd, 0, os.SEEK_SET)
                msvcrt.locking(fd, msvcrt.LK_LOCK, 1)  # type: ignore[attr-defined]
                return True
            except OSError:
                if time.perf_counter() >= deadline:
                    return False
                time.sleep(0.05)

    def _unlock_file(fd: int) -> None:
        """Release the byte-0 lock on *fd*.

        Seeks back to byte 0 before unlocking so the unlock targets the
        same byte that :func:`_lock_file` acquired.
        """
        try:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)  # type: ignore[attr-defined]
        except OSError:
            pass

else:
    import fcntl  # type: ignore[import-untyped]

    def _lock_file(fd: int) -> bool:
        """Acquire an exclusive advisory lock on *fd*.  Returns True on success."""
        deadline = time.perf_counter() + _LOCK_TIMEOUT
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)  # type: ignore[attr-defined]
                return True
            except BlockingIOError:
                if time.perf_counter() >= deadline:
                    return False
                time.sleep(0.05)
            except OSError:
                return False

    def _unlock_file(fd: int) -> None:
        """Release the advisory lock on *fd*."""
        try:
            fcntl.flock(fd, fcntl.LOCK_UN)  # type: ignore[attr-defined]
        except OSError:
            pass


class NDJSONWriter:
    """Append JSON records to an NDJSON file with inter-process locking.

    Usage::

        writer = NDJSONWriter()
        writer.append(Path(".harness/isolation/session-1/.isolation.ndjson"),
                       {"role": "planner", "event": "workspace_created"})
    """

    def append(self, path: Path, record: dict[str, Any]) -> bool:
        """Append *record* as a JSON line to *path*.

        Creates parent directories if they do not exist.  Acquires an
        exclusive file lock so that concurrent writers do not interleave.

        Returns True on success, False if the lock could not be acquired
        after the timeout + one retry.
        """
        path.parent.mkdir(parents=True, exist_ok=True)

        line = json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"

        for attempt in (1, 2):
            try:
                # Open with low-level fd for locking primitives.
                fd = os.open(
                    str(path),
                    os.O_WRONLY | os.O_CREAT | os.O_APPEND,
                    0o666,
                )
                try:
                    if _lock_file(fd):
                        try:
                            os.write(fd, line.encode("utf-8"))
                            return True
                        finally:
                            _unlock_file(fd)
                finally:
                    os.close(fd)
            except OSError:
                if attempt == 2:
                    return False
                time.sleep(0.1)

        return False
