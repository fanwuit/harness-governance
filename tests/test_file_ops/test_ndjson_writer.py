"""Tests for the thread-safe / process-safe NDJSON writer."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from harness_governance.file_ops.ndjson_writer import NDJSONWriter


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_lines(path: Path) -> list[str]:
    """Return non-empty lines from *path*."""
    return [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln]


def _parse_ndjson(path: Path) -> list[dict]:
    """Parse every line of *path* as JSON and return the list of objects."""
    return [json.loads(ln) for ln in _read_lines(path)]


# ---------------------------------------------------------------------------
# Tests — basic append
# ---------------------------------------------------------------------------


class TestAppendBasic:
    """Core append() behaviour."""

    def test_append_returns_true(self, tmp_path: Path) -> None:
        writer = NDJSONWriter()
        target = tmp_path / "events.ndjson"
        assert writer.append(target, {"role": "planner"}) is True

    def test_append_creates_file(self, tmp_path: Path) -> None:
        writer = NDJSONWriter()
        target = tmp_path / "events.ndjson"
        writer.append(target, {"a": 1})
        assert target.exists()

    def test_append_writes_valid_json_line(self, tmp_path: Path) -> None:
        writer = NDJSONWriter()
        target = tmp_path / "events.ndjson"
        writer.append(target, {"key": "value"})

        lines = _read_lines(target)
        assert len(lines) == 1
        assert json.loads(lines[0]) == {"key": "value"}

    def test_append_ends_with_newline(self, tmp_path: Path) -> None:
        writer = NDJSONWriter()
        target = tmp_path / "events.ndjson"
        writer.append(target, {"x": 1})

        raw = target.read_text(encoding="utf-8")
        assert raw.endswith("\n")

    def test_append_creates_parent_dirs(self, tmp_path: Path) -> None:
        writer = NDJSONWriter()
        target = tmp_path / "deep" / "nested" / "dir" / "events.ndjson"
        result = writer.append(target, {"event": "created"})

        assert result is True
        assert target.exists()
        assert target.parent.is_dir()

    def test_append_deeply_nested_path(self, tmp_path: Path) -> None:
        writer = NDJSONWriter()
        target = tmp_path / "a" / "b" / "c" / "d" / "e" / "out.ndjson"
        assert writer.append(target, {"depth": 5}) is True
        assert _parse_ndjson(target) == [{"depth": 5}]


# ---------------------------------------------------------------------------
# Tests — multiple appends
# ---------------------------------------------------------------------------


class TestMultipleAppends:
    """Records accumulate; earlier records are never overwritten."""

    def test_multiple_appends_produce_valid_ndjson(self, tmp_path: Path) -> None:
        writer = NDJSONWriter()
        target = tmp_path / "events.ndjson"

        for i in range(5):
            writer.append(target, {"index": i})

        records = _parse_ndjson(target)
        assert len(records) == 5
        assert [r["index"] for r in records] == [0, 1, 2, 3, 4]

    def test_records_are_appended_not_overwritten(self, tmp_path: Path) -> None:
        writer = NDJSONWriter()
        target = tmp_path / "events.ndjson"

        writer.append(target, {"first": True})
        writer.append(target, {"second": True})

        records = _parse_ndjson(target)
        assert len(records) == 2
        assert records[0] == {"first": True}
        assert records[1] == {"second": True}

    def test_each_line_is_independent_json(self, tmp_path: Path) -> None:
        writer = NDJSONWriter()
        target = tmp_path / "events.ndjson"

        writer.append(target, {"a": 1})
        writer.append(target, {"b": 2})
        writer.append(target, {"c": 3})

        lines = _read_lines(target)
        assert len(lines) == 3
        # Each line must be independently parseable.
        for line in lines:
            parsed = json.loads(line)
            assert isinstance(parsed, dict)


# ---------------------------------------------------------------------------
# Tests — JSON serialization options
# ---------------------------------------------------------------------------


class TestSerializationOptions:
    """The writer uses ``ensure_ascii=False`` and ``sort_keys=True``."""

    def test_ensure_ascii_false_preserves_unicode(self, tmp_path: Path) -> None:
        writer = NDJSONWriter()
        target = tmp_path / "unicode.ndjson"

        writer.append(target, {"greeting": "\u3053\u3093\u306b\u3061\u306f", "emoji": "\u2728"})

        raw = target.read_text(encoding="utf-8")
        # Unicode characters must appear literally, not as \\uXXXX escapes.
        assert "\u3053\u3093\u306b\u3061\u306f" in raw
        assert "\u2728" in raw
        assert "\\u" not in raw

    def test_sort_keys_true(self, tmp_path: Path) -> None:
        writer = NDJSONWriter()
        target = tmp_path / "sorted.ndjson"

        writer.append(target, {"zebra": 1, "alpha": 2, "middle": 3})

        line = _read_lines(target)[0]
        parsed_keys = list(json.loads(line).keys())
        assert parsed_keys == sorted(parsed_keys)
        assert parsed_keys == ["alpha", "middle", "zebra"]

    def test_unicode_round_trip(self, tmp_path: Path) -> None:
        writer = NDJSONWriter()
        target = tmp_path / "roundtrip.ndjson"

        record = {"name": "\u00e9l\u00e8ve", "city": "\u00fc\u00f8\u00e5", "note": "\u4e2d\u6587"}
        writer.append(target, record)

        parsed = _parse_ndjson(target)
        assert parsed[0] == record


# ---------------------------------------------------------------------------
# Tests — concurrent / locking behaviour (single-writer)
# ---------------------------------------------------------------------------


class TestLocking:
    """File locking should be transparent for single-writer scenarios."""

    def test_rapid_successive_appends(self, tmp_path: Path) -> None:
        """Rapid appends from a single writer should all succeed."""
        writer = NDJSONWriter()
        target = tmp_path / "rapid.ndjson"

        results = [writer.append(target, {"i": i}) for i in range(20)]
        assert all(results)
        assert len(_parse_ndjson(target)) == 20

    def test_two_writers_same_file(self, tmp_path: Path) -> None:
        """Two NDJSONWriter instances writing to the same file should both succeed."""
        target = tmp_path / "shared.ndjson"

        writer_a = NDJSONWriter()
        writer_b = NDJSONWriter()

        assert writer_a.append(target, {"from": "A"}) is True
        assert writer_b.append(target, {"from": "B"}) is True

        records = _parse_ndjson(target)
        assert len(records) == 2
        sources = {r["from"] for r in records}
        assert sources == {"A", "B"}


# ---------------------------------------------------------------------------
# Tests — error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Invalid paths should cause append to return False."""

    def test_invalid_path_raises(self) -> None:
        writer = NDJSONWriter()
        # NUL byte in path is rejected by Python before reaching os.open,
        # raising ValueError (not caught by the writer's OSError handler).
        bad_path = Path("bad\x00path.ndjson")
        with pytest.raises(ValueError):
            writer.append(bad_path, {"x": 1})

    def test_append_complex_nested_record(self, tmp_path: Path) -> None:
        """Records with nested structures should serialize correctly."""
        writer = NDJSONWriter()
        target = tmp_path / "nested.ndjson"

        record = {
            "event": "workspace_created",
            "metadata": {"layer": "contract", "depth": 3},
            "tags": ["a", "b"],
        }
        writer.append(target, record)

        parsed = _parse_ndjson(target)
        assert parsed[0] == record

    def test_append_empty_record(self, tmp_path: Path) -> None:
        writer = NDJSONWriter()
        target = tmp_path / "empty.ndjson"
        assert writer.append(target, {}) is True
        assert _parse_ndjson(target) == [{}]

    def test_append_record_with_none_values(self, tmp_path: Path) -> None:
        writer = NDJSONWriter()
        target = tmp_path / "nulls.ndjson"
        record = {"key": None, "other": "value"}
        writer.append(target, record)

        parsed = _parse_ndjson(target)
        assert parsed[0] == record
