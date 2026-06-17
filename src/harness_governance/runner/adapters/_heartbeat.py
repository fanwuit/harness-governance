"""Heartbeat monitoring for headless agent executors.

Provides a daemon thread that periodically writes NDJSON heartbeat
entries while a subprocess is alive, so callers can distinguish
"still running" from "hung / crashed" without waiting for the full
timeout.
"""

from __future__ import annotations

import json
import subprocess
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(slots=True)
class HeartbeatCounters:
    """Thread-safe counters shared between the main read loop and the
    heartbeat writer thread.  Only integer increments are needed, so
    the GIL provides sufficient synchronisation.
    """

    stdout_lines: int = 0
    stderr_lines: int = 0


def start_heartbeat_thread(
    proc: subprocess.Popen,
    heartbeat_path: Path,
    counters: HeartbeatCounters,
    interval_seconds: int,
    started_at: float,
) -> threading.Thread:
    """Start a daemon thread that writes NDJSON heartbeat entries.

    Each entry is a single JSON line::

        {"ts": "2026-06-17T12:00:30+00:00", "elapsed_s": 30.0,
         "stdout_lines": 45, "stderr_lines": 2, "pid": 12345}

    The thread exits automatically when *proc* terminates
    (``proc.poll() is not None``).

    Parameters
    ----------
    proc:
        The subprocess to monitor.
    heartbeat_path:
        Path to the ``.ndjson`` heartbeat file (created on first write).
    counters:
        Shared :class:`HeartbeatCounters` updated by the main loop.
    interval_seconds:
        Seconds between heartbeat entries.  Must be > 0.
    started_at:
        ``time.monotonic()`` value recorded just before / after
        ``Popen`` was created.

    Returns
    -------
    threading.Thread
        The daemon heartbeat thread (already started).
    """
    heartbeat_path.parent.mkdir(parents=True, exist_ok=True)

    def _loop() -> None:
        while proc.poll() is None:
            time.sleep(interval_seconds)
            if proc.poll() is not None:
                break
            entry = {
                "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "elapsed_s": round(time.monotonic() - started_at, 1),
                "stdout_lines": counters.stdout_lines,
                "stderr_lines": counters.stderr_lines,
                "pid": proc.pid,
            }
            try:
                with heartbeat_path.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
            except OSError:
                # Best-effort; heartbeat is advisory, not critical.
                pass

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    return t


def format_progress_line(elapsed_s: float, stdout_lines: int, stderr_lines: int) -> str:
    """Return a human-readable progress line for stderr output."""
    return (
        f"[harness runner] elapsed: {elapsed_s:.0f}s, "
        f"stdout: {stdout_lines} lines, stderr: {stderr_lines} lines\n"
    )
