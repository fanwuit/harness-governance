"""Comprehensive tests for the FieldAlignmentEngine (state_machine.alignment).

Covers spec extraction (markdown tables, JSON schema blocks), AST-based
implementation scanning, the full alignment pipeline, traceability matrix
construction, type normalization/compatibility, language detection, and
gate hook integration.
"""

from __future__ import annotations

import ast
import textwrap
from pathlib import Path

import pytest

from harness_governance.state_machine.alignment import (
    FieldAlignmentEngine,
    _FieldVisitor,
    _gate_hook_alignment_contract,
    _gate_hook_alignment_impl,
)
from harness_governance.models.schemas import (
    FieldAlignmentSpec,
    TraceabilityMatrix,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def engine(tmp_path: Path) -> FieldAlignmentEngine:
    """Return a FieldAlignmentEngine rooted at *tmp_path*."""
    return FieldAlignmentEngine(tmp_path)


def _write_contract(tmp_path: Path, name: str, content: str) -> Path:
    """Write a contract markdown file under docs/contracts/ and return its path."""
    d = tmp_path / "docs" / "contracts"
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    p.write_text(content, encoding="utf-8")
    return p


def _write_source(tmp_path: Path, rel_path: str, content: str) -> Path:
    """Write a Python source file under the project root and return its path."""
    p = tmp_path / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


def _write_test_file(tmp_path: Path, rel_path: str, content: str) -> Path:
    """Write a test file under the project root and return its path."""
    p = tmp_path / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Markdown contract content snippets
# ---------------------------------------------------------------------------
#
# NOTE: The separator-line detector in _parse_markdown_table only
# recognises the patterns ``---``, ``----`` (with optional ``:``
# alignment markers).  Longer runs like ``-------`` are NOT treated
# as separators and will be parsed as data rows.  All test fixtures
# therefore use exactly three dashes per cell.
# ---------------------------------------------------------------------------

SIMPLE_TABLE_MD = textwrap.dedent("""\
    # User API Contract

    | Field | Type | Required |
    |---|---|---|
    | user_id | str | yes |
    | name | str | yes |
    | email | str | yes |
    | age | int | no |
""")

CHINESE_TABLE_MD = textwrap.dedent("""\
    # 用户接口契约

    | 字段 | 类型 | 必填 |
    |---|---|---|
    | user_id | str | 是 |
    | name | str | 是 |
    | email | str | 必填 |
""")

JSON_SCHEMA_MD = textwrap.dedent("""\
    # Order API

    ```json
    {
      "type": "object",
      "properties": {
        "order_id": {"type": "string"},
        "quantity": {"type": "integer"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "price": {"type": "number"}
      },
      "required": ["order_id", "quantity"]
    }
    ```
""")

DUPLICATE_FIELD_TABLE_MD = textwrap.dedent("""\
    | Field | Type | Required |
    |---|---|---|
    | user_id | str | yes |
    | user_id | str | no |
""")

EMPTY_TABLE_MD = textwrap.dedent("""\
    # No fields here

    Just some text without any tables.
""")

TABLE_WITH_SEP_VARIANTS_MD = textwrap.dedent("""\
    | Field | Type | Required |
    |---:|:---|:---:|
    | alpha | str | yes |
    | beta | int | no |
""")

TABLE_NAME_HEADER_MD = textwrap.dedent("""\
    | Name | Type | Required? |
    |---|---|---|
    | widget_id | str | true |
    | label | str | false |
""")

UUID_TABLE_MD = textwrap.dedent("""\
    | Field | Type | Required |
    |---|---|---|
    | id | UUID | yes |
    | label | str | yes |
""")


# ---------------------------------------------------------------------------
# Sample Python source snippets
# ---------------------------------------------------------------------------

MATCHING_IMPL = """\
class User:
    user_id: str
    name: str
    email: str
    age: int
"""

MISSING_FIELD_IMPL = """\
class User:
    user_id: str
    name: str
    # email is missing
    age: int
"""

TYPE_MISMATCH_IMPL = """\
class User:
    user_id: str
    name: int
    email: str
    age: str
"""

EXTRA_FIELD_IMPL = """\
class User:
    user_id: str
    name: str
    email: str
    age: int
    phone: str
"""

INIT_STYLE_IMPL = """\
class User:
    def __init__(self):
        self.user_id = None
        self.name = ""
        self.email = ""
        self.age = 0
"""

FUNC_ANNOTATED_IMPL = """\
def create_user(user_id: str, name: str, email: str, age: int) -> None:
    pass
"""


# ===================================================================
# extract_specs() tests
# ===================================================================


class TestExtractSpecs:
    """Tests for FieldAlignmentEngine.extract_specs()."""

    def test_parse_simple_markdown_table(self, tmp_path: Path) -> None:
        contract = _write_contract(tmp_path, "user-api.md", SIMPLE_TABLE_MD)
        engine = FieldAlignmentEngine(tmp_path)
        specs = engine.extract_specs(contract)

        assert len(specs) == 4
        names = [s.field_name for s in specs]
        assert "user_id" in names
        assert "name" in names
        assert "email" in names
        assert "age" in names

    def test_field_types_extracted(self, tmp_path: Path) -> None:
        contract = _write_contract(tmp_path, "user-api.md", SIMPLE_TABLE_MD)
        engine = FieldAlignmentEngine(tmp_path)
        specs = engine.extract_specs(contract)
        spec_map = {s.field_name: s for s in specs}

        assert spec_map["user_id"].field_type == "str"
        assert spec_map["name"].field_type == "str"
        assert spec_map["age"].field_type == "int"

    def test_required_flag_extracted(self, tmp_path: Path) -> None:
        contract = _write_contract(tmp_path, "user-api.md", SIMPLE_TABLE_MD)
        engine = FieldAlignmentEngine(tmp_path)
        specs = engine.extract_specs(contract)
        spec_map = {s.field_name: s for s in specs}

        assert spec_map["user_id"].is_required is True
        assert spec_map["name"].is_required is True
        assert spec_map["age"].is_required is False

    def test_source_line_populated(self, tmp_path: Path) -> None:
        contract = _write_contract(tmp_path, "user-api.md", SIMPLE_TABLE_MD)
        engine = FieldAlignmentEngine(tmp_path)
        specs = engine.extract_specs(contract)

        for spec in specs:
            assert spec.source_line > 0
            assert spec.source_contract == str(contract)

    def test_parse_json_schema_block(self, tmp_path: Path) -> None:
        contract = _write_contract(tmp_path, "order-api.md", JSON_SCHEMA_MD)
        engine = FieldAlignmentEngine(tmp_path)
        specs = engine.extract_specs(contract)

        assert len(specs) == 4
        spec_map = {s.field_name: s for s in specs}
        assert "order_id" in spec_map
        assert "quantity" in spec_map
        assert "tags" in spec_map
        assert "price" in spec_map

    def test_json_schema_required_fields(self, tmp_path: Path) -> None:
        contract = _write_contract(tmp_path, "order-api.md", JSON_SCHEMA_MD)
        engine = FieldAlignmentEngine(tmp_path)
        specs = engine.extract_specs(contract)
        spec_map = {s.field_name: s for s in specs}

        assert spec_map["order_id"].is_required is True
        assert spec_map["quantity"].is_required is True
        assert spec_map["tags"].is_required is False
        assert spec_map["price"].is_required is False

    def test_json_schema_array_type(self, tmp_path: Path) -> None:
        contract = _write_contract(tmp_path, "order-api.md", JSON_SCHEMA_MD)
        engine = FieldAlignmentEngine(tmp_path)
        specs = engine.extract_specs(contract)
        spec_map = {s.field_name: s for s in specs}

        assert "list" in spec_map["tags"].field_type.lower()

    def test_nonexistent_file_returns_empty(self, tmp_path: Path) -> None:
        engine = FieldAlignmentEngine(tmp_path)
        specs = engine.extract_specs(tmp_path / "does-not-exist.md")
        assert specs == []

    def test_empty_contract_returns_empty(self, tmp_path: Path) -> None:
        contract = _write_contract(tmp_path, "empty.md", "")
        engine = FieldAlignmentEngine(tmp_path)
        specs = engine.extract_specs(contract)
        assert specs == []

    def test_contract_without_tables_or_json(self, tmp_path: Path) -> None:
        contract = _write_contract(tmp_path, "no-fields.md", EMPTY_TABLE_MD)
        engine = FieldAlignmentEngine(tmp_path)
        specs = engine.extract_specs(contract)
        assert specs == []

    def test_both_table_and_json_extracted(self, tmp_path: Path) -> None:
        combined = SIMPLE_TABLE_MD + "\n\n" + JSON_SCHEMA_MD
        contract = _write_contract(tmp_path, "combined.md", combined)
        engine = FieldAlignmentEngine(tmp_path)
        specs = engine.extract_specs(contract)
        # 4 from table + 4 from JSON = 8
        assert len(specs) == 8

    def test_uuid_field_type_extracted(self, tmp_path: Path) -> None:
        contract = _write_contract(tmp_path, "uuid.md", UUID_TABLE_MD)
        engine = FieldAlignmentEngine(tmp_path)
        specs = engine.extract_specs(contract)
        spec_map = {s.field_name: s for s in specs}
        assert spec_map["id"].field_type == "UUID"


# ===================================================================
# _parse_markdown_table() tests
# ===================================================================


class TestParseMarkdownTable:
    """Edge cases for the static _parse_markdown_table method."""

    def test_chinese_headers(self) -> None:
        specs = FieldAlignmentEngine._parse_markdown_table(CHINESE_TABLE_MD, "test.md")
        assert len(specs) == 3
        names = {s.field_name for s in specs}
        assert names == {"user_id", "name", "email"}

    def test_chinese_required_values(self) -> None:
        specs = FieldAlignmentEngine._parse_markdown_table(CHINESE_TABLE_MD, "test.md")
        spec_map = {s.field_name: s for s in specs}
        # "是" and "必填" should both be treated as required
        assert spec_map["user_id"].is_required is True
        assert spec_map["name"].is_required is True
        assert spec_map["email"].is_required is True

    def test_separator_variants(self) -> None:
        specs = FieldAlignmentEngine._parse_markdown_table(
            TABLE_WITH_SEP_VARIANTS_MD, "test.md"
        )
        assert len(specs) == 2
        names = {s.field_name for s in specs}
        assert names == {"alpha", "beta"}

    def test_name_header_alias(self) -> None:
        specs = FieldAlignmentEngine._parse_markdown_table(
            TABLE_NAME_HEADER_MD, "test.md"
        )
        assert len(specs) == 2
        spec_map = {s.field_name: s for s in specs}
        assert "widget_id" in spec_map
        assert "label" in spec_map

    def test_empty_content(self) -> None:
        specs = FieldAlignmentEngine._parse_markdown_table("", "test.md")
        assert specs == []

    def test_no_table_in_content(self) -> None:
        specs = FieldAlignmentEngine._parse_markdown_table(
            "Just a paragraph.\nWith two lines.\n", "test.md"
        )
        assert specs == []

    def test_table_ends_on_blank_line(self) -> None:
        content = textwrap.dedent("""\
            | Field | Type | Required |
            |---|---|---|
            | a | str | yes |

            | Field | Type | Required |
            |---|---|---|
            | b | int | no |
        """)
        specs = FieldAlignmentEngine._parse_markdown_table(content, "test.md")
        names = {s.field_name for s in specs}
        assert "a" in names
        assert "b" in names

    def test_source_contract_attached(self) -> None:
        specs = FieldAlignmentEngine._parse_markdown_table(
            SIMPLE_TABLE_MD, "my_contract.md"
        )
        for spec in specs:
            assert spec.source_contract == "my_contract.md"

    def test_long_separator_recognised(self) -> None:
        """Separator lines with more than 4 dashes are correctly recognised.

        The separator check uses a regex to accept any number of dashes
        (e.g. ``|-------|------|----------|``).
        """
        content = textwrap.dedent("""\
            | Field | Type | Required |
            |-------|------|----------|
            | a | str | yes |
        """)
        specs = FieldAlignmentEngine._parse_markdown_table(content, "test.md")
        # The separator line is correctly skipped → only 1 spec
        assert len(specs) == 1
        assert specs[0].field_name == "a"


# ===================================================================
# _parse_json_schema_blocks() tests
# ===================================================================


class TestParseJsonSchemaBlocks:
    def test_basic_schema(self) -> None:
        specs = FieldAlignmentEngine._parse_json_schema_blocks(
            JSON_SCHEMA_MD, "test.md"
        )
        assert len(specs) == 4

    def test_nested_json_schema(self) -> None:
        nested = textwrap.dedent("""\
            ```json
            {
              "type": "object",
              "properties": {
                "address": {
                  "type": "object",
                  "properties": {
                    "street": {"type": "string"}
                  }
                },
                "city": {"type": "string"}
              },
              "required": ["city"]
            }
            ```
        """)
        specs = FieldAlignmentEngine._parse_json_schema_blocks(nested, "test.md")
        names = {s.field_name for s in specs}
        # Only top-level properties are extracted
        assert "address" in names
        assert "city" in names

    def test_array_items_type(self) -> None:
        schema = textwrap.dedent("""\
            ```json
            {
              "properties": {
                "tags": {"type": "array", "items": {"type": "string"}},
                "scores": {"type": "array", "items": {"type": "integer"}}
              },
              "required": []
            }
            ```
        """)
        specs = FieldAlignmentEngine._parse_json_schema_blocks(schema, "test.md")
        spec_map = {s.field_name: s for s in specs}
        assert "list" in spec_map["tags"].field_type.lower()
        assert "string" in spec_map["tags"].field_type.lower()

    def test_invalid_json_block_skipped(self) -> None:
        bad = textwrap.dedent("""\
            ```json
            {this is not valid json
            ```
        """)
        specs = FieldAlignmentEngine._parse_json_schema_blocks(bad, "test.md")
        assert specs == []

    def test_multiple_json_blocks(self) -> None:
        multi = textwrap.dedent("""\
            ```json
            {
              "properties": {"a": {"type": "string"}},
              "required": []
            }
            ```

            Some text in between.

            ```json
            {
              "properties": {"b": {"type": "integer"}},
              "required": ["b"]
            }
            ```
        """)
        specs = FieldAlignmentEngine._parse_json_schema_blocks(multi, "test.md")
        assert len(specs) == 2
        names = {s.field_name for s in specs}
        assert names == {"a", "b"}

    def test_no_properties_key(self) -> None:
        schema = textwrap.dedent("""\
            ```json
            {
              "type": "string"
            }
            ```
        """)
        specs = FieldAlignmentEngine._parse_json_schema_blocks(schema, "test.md")
        assert specs == []

    def test_property_without_type_defaults_to_string(self) -> None:
        schema = textwrap.dedent("""\
            ```json
            {
              "properties": {
                "mystery": {}
              },
              "required": []
            }
            ```
        """)
        specs = FieldAlignmentEngine._parse_json_schema_blocks(schema, "test.md")
        assert len(specs) == 1
        assert specs[0].field_type == "string"

    def test_required_fields_marked(self) -> None:
        schema = textwrap.dedent("""\
            ```json
            {
              "properties": {
                "a": {"type": "string"},
                "b": {"type": "integer"}
              },
              "required": ["a"]
            }
            ```
        """)
        specs = FieldAlignmentEngine._parse_json_schema_blocks(schema, "test.md")
        spec_map = {s.field_name: s for s in specs}
        assert spec_map["a"].is_required is True
        assert spec_map["b"].is_required is False


# ===================================================================
# scan_implementation() tests
# ===================================================================


class TestScanImplementation:
    def test_all_fields_matched(self, tmp_path: Path) -> None:
        contract = _write_contract(tmp_path, "user.md", SIMPLE_TABLE_MD)
        src = _write_source(tmp_path, "src/models/user.py", MATCHING_IMPL)
        engine = FieldAlignmentEngine(tmp_path)
        specs = engine.extract_specs(contract)
        findings, unsupported = engine.scan_implementation([src], specs)

        # Should have no missing errors
        missing = [f for f in findings if f.issue == "missing"]
        assert len(missing) == 0
        assert unsupported == []

    def test_missing_field_detected(self, tmp_path: Path) -> None:
        contract = _write_contract(tmp_path, "user.md", SIMPLE_TABLE_MD)
        src = _write_source(tmp_path, "src/models/user.py", MISSING_FIELD_IMPL)
        engine = FieldAlignmentEngine(tmp_path)
        specs = engine.extract_specs(contract)
        findings, unsupported = engine.scan_implementation([src], specs)

        missing = [f for f in findings if f.issue == "missing"]
        missing_names = {f.contract_field for f in missing}
        assert "email" in missing_names

    def test_type_mismatch_detected(self, tmp_path: Path) -> None:
        contract = _write_contract(tmp_path, "user.md", SIMPLE_TABLE_MD)
        src = _write_source(tmp_path, "src/models/user.py", TYPE_MISMATCH_IMPL)
        engine = FieldAlignmentEngine(tmp_path)
        specs = engine.extract_specs(contract)
        findings, unsupported = engine.scan_implementation([src], specs)

        mismatches = [f for f in findings if f.issue == "type_mismatch"]
        mismatch_fields = {f.contract_field for f in mismatches}
        # name is str in contract but int in impl; age is int in contract but str in impl
        assert "name" in mismatch_fields
        assert "age" in mismatch_fields

    def test_extra_field_detected(self, tmp_path: Path) -> None:
        contract = _write_contract(tmp_path, "user.md", SIMPLE_TABLE_MD)
        src = _write_source(tmp_path, "src/models/user.py", EXTRA_FIELD_IMPL)
        engine = FieldAlignmentEngine(tmp_path)
        specs = engine.extract_specs(contract)
        findings, unsupported = engine.scan_implementation([src], specs)

        extras = [f for f in findings if f.issue == "extra_field"]
        extra_names = {f.implementation_field for f in extras}
        assert "phone" in extra_names

    def test_extra_field_is_warning_severity(self, tmp_path: Path) -> None:
        contract = _write_contract(tmp_path, "user.md", SIMPLE_TABLE_MD)
        src = _write_source(tmp_path, "src/models/user.py", EXTRA_FIELD_IMPL)
        engine = FieldAlignmentEngine(tmp_path)
        specs = engine.extract_specs(contract)
        findings, _ = engine.scan_implementation([src], specs)

        extras = [f for f in findings if f.issue == "extra_field"]
        for f in extras:
            assert f.severity == "warning"

    def test_missing_field_is_error_severity(self, tmp_path: Path) -> None:
        contract = _write_contract(tmp_path, "user.md", SIMPLE_TABLE_MD)
        src = _write_source(tmp_path, "src/models/user.py", MISSING_FIELD_IMPL)
        engine = FieldAlignmentEngine(tmp_path)
        specs = engine.extract_specs(contract)
        findings, _ = engine.scan_implementation([src], specs)

        missing = [f for f in findings if f.issue == "missing"]
        for f in missing:
            assert f.severity == "error"

    def test_init_style_fields_detected(self, tmp_path: Path) -> None:
        contract = _write_contract(tmp_path, "user.md", SIMPLE_TABLE_MD)
        src = _write_source(tmp_path, "src/models/user.py", INIT_STYLE_IMPL)
        engine = FieldAlignmentEngine(tmp_path)
        specs = engine.extract_specs(contract)
        findings, unsupported = engine.scan_implementation([src], specs)

        missing = [f for f in findings if f.issue == "missing"]
        assert len(missing) == 0

    def test_function_annotation_fields_detected(self, tmp_path: Path) -> None:
        contract = _write_contract(tmp_path, "user.md", SIMPLE_TABLE_MD)
        src = _write_source(tmp_path, "src/models/user.py", FUNC_ANNOTATED_IMPL)
        engine = FieldAlignmentEngine(tmp_path)
        specs = engine.extract_specs(contract)
        findings, unsupported = engine.scan_implementation([src], specs)

        missing = [f for f in findings if f.issue == "missing"]
        assert len(missing) == 0

    def test_unsupported_language_recorded(self, tmp_path: Path) -> None:
        contract = _write_contract(tmp_path, "user.md", SIMPLE_TABLE_MD)
        ts_file = tmp_path / "src" / "app.ts"
        ts_file.parent.mkdir(parents=True, exist_ok=True)
        ts_file.write_text("const userId: string = 'abc';", encoding="utf-8")

        engine = FieldAlignmentEngine(tmp_path)
        specs = engine.extract_specs(contract)
        findings, unsupported = engine.scan_implementation([ts_file], specs)

        assert "TypeScript" in unsupported

    def test_empty_specs_returns_empty(self, tmp_path: Path) -> None:
        src = _write_source(tmp_path, "src/models/user.py", MATCHING_IMPL)
        engine = FieldAlignmentEngine(tmp_path)
        findings, unsupported = engine.scan_implementation([src], [])
        assert findings == []
        assert unsupported == []

    def test_nonexistent_source_file_skipped(self, tmp_path: Path) -> None:
        contract = _write_contract(tmp_path, "user.md", SIMPLE_TABLE_MD)
        engine = FieldAlignmentEngine(tmp_path)
        specs = engine.extract_specs(contract)
        findings, unsupported = engine.scan_implementation(
            [tmp_path / "no_such_file.py"], specs
        )
        # All 4 fields should be reported as missing
        missing = [f for f in findings if f.issue == "missing"]
        assert len(missing) == 4

    def test_syntax_error_source_skipped(self, tmp_path: Path) -> None:
        contract = _write_contract(tmp_path, "user.md", SIMPLE_TABLE_MD)
        src = _write_source(tmp_path, "src/bad.py", "def broken(:\n  pass\n")
        engine = FieldAlignmentEngine(tmp_path)
        specs = engine.extract_specs(contract)
        findings, unsupported = engine.scan_implementation([src], specs)
        # All 4 fields missing since the source can't be parsed.
        missing = [f for f in findings if f.issue == "missing"]
        assert len(missing) == 4

    def test_multiple_source_files(self, tmp_path: Path) -> None:
        contract = _write_contract(tmp_path, "user.md", SIMPLE_TABLE_MD)
        src1 = _write_source(
            tmp_path,
            "src/models/user.py",
            "class User:\n    user_id: str\n    name: str\n",
        )
        src2 = _write_source(
            tmp_path,
            "src/models/user_extra.py",
            "class UserExtra:\n    email: str\n    age: int\n",
        )
        engine = FieldAlignmentEngine(tmp_path)
        specs = engine.extract_specs(contract)
        findings, unsupported = engine.scan_implementation([src1, src2], specs)

        missing = [f for f in findings if f.issue == "missing"]
        assert len(missing) == 0

    def test_mixed_python_and_non_python(self, tmp_path: Path) -> None:
        """Non-Python files are recorded as unsupported; Python files are scanned."""
        contract = _write_contract(tmp_path, "user.md", SIMPLE_TABLE_MD)
        py_src = _write_source(tmp_path, "src/models/user.py", MATCHING_IMPL)
        ts_file = tmp_path / "src" / "app.ts"
        ts_file.parent.mkdir(parents=True, exist_ok=True)
        ts_file.write_text("export const x = 1;", encoding="utf-8")

        engine = FieldAlignmentEngine(tmp_path)
        specs = engine.extract_specs(contract)
        findings, unsupported = engine.scan_implementation([py_src, ts_file], specs)
        assert "TypeScript" in unsupported
        missing = [f for f in findings if f.issue == "missing"]
        assert len(missing) == 0  # Python source covers all fields


# ===================================================================
# compute_alignment() tests
# ===================================================================


class TestComputeAlignment:
    def test_no_contracts_dir_passes(self, tmp_path: Path) -> None:
        engine = FieldAlignmentEngine(tmp_path)
        report = engine.compute_alignment()
        assert report.passed is True
        assert report.fields_expected == 0
        assert report.fields_matched == 0

    def test_empty_contracts_dir_passes(self, tmp_path: Path) -> None:
        (tmp_path / "docs" / "contracts").mkdir(parents=True)
        engine = FieldAlignmentEngine(tmp_path)
        report = engine.compute_alignment()
        assert report.passed is True

    def test_passing_alignment(self, tmp_path: Path) -> None:
        _write_contract(tmp_path, "user.md", SIMPLE_TABLE_MD)
        _write_source(tmp_path, "src/models/user.py", MATCHING_IMPL)
        engine = FieldAlignmentEngine(tmp_path)
        report = engine.compute_alignment()

        assert report.passed is True
        assert report.fields_expected == 4
        assert report.fields_matched >= 3  # at least most should match

    def test_failing_alignment(self, tmp_path: Path) -> None:
        _write_contract(tmp_path, "user.md", SIMPLE_TABLE_MD)
        _write_source(tmp_path, "src/models/user.py", MISSING_FIELD_IMPL)
        engine = FieldAlignmentEngine(tmp_path)
        report = engine.compute_alignment()

        assert report.passed is False
        errors = [f for f in report.findings if f.severity == "error"]
        assert len(errors) > 0

    def test_compute_alignment_detects_unsupported_languages(
        self, tmp_path: Path
    ) -> None:
        """compute_alignment() now scans all known source file types;
        non-Python files are reported in unsupported_languages.
        """
        _write_contract(tmp_path, "user.md", SIMPLE_TABLE_MD)
        ts_file = tmp_path / "src" / "app.ts"
        ts_file.parent.mkdir(parents=True, exist_ok=True)
        ts_file.write_text("export const x = 1;", encoding="utf-8")

        engine = FieldAlignmentEngine(tmp_path)
        report = engine.compute_alignment()
        # .ts files are discovered and reported as unsupported
        assert "TypeScript" in report.unsupported_languages

    def test_report_has_generated_at(self, tmp_path: Path) -> None:
        engine = FieldAlignmentEngine(tmp_path)
        report = engine.compute_alignment()
        assert report.generated_at != ""

    def test_report_findings_is_tuple(self, tmp_path: Path) -> None:
        _write_contract(tmp_path, "user.md", SIMPLE_TABLE_MD)
        _write_source(tmp_path, "src/models/user.py", MATCHING_IMPL)
        engine = FieldAlignmentEngine(tmp_path)
        report = engine.compute_alignment()
        assert isinstance(report.findings, tuple)

    def test_multiple_contract_files(self, tmp_path: Path) -> None:
        _write_contract(tmp_path, "user.md", SIMPLE_TABLE_MD)
        _write_contract(tmp_path, "order.md", JSON_SCHEMA_MD)
        _write_source(tmp_path, "src/models/user.py", MATCHING_IMPL)
        _write_source(
            tmp_path,
            "src/models/order.py",
            "class Order:\n    order_id: str\n    quantity: int\n    tags: list\n    price: float\n",
        )
        engine = FieldAlignmentEngine(tmp_path)
        report = engine.compute_alignment()
        assert report.fields_expected == 8  # 4 + 4

    def test_type_mismatch_causes_failure(self, tmp_path: Path) -> None:
        _write_contract(tmp_path, "user.md", SIMPLE_TABLE_MD)
        _write_source(tmp_path, "src/models/user.py", TYPE_MISMATCH_IMPL)
        engine = FieldAlignmentEngine(tmp_path)
        report = engine.compute_alignment()
        assert report.passed is False
        mismatches = [f for f in report.findings if f.issue == "type_mismatch"]
        assert len(mismatches) > 0


# ===================================================================
# build_traceability_matrix() tests
# ===================================================================


class TestBuildTraceabilityMatrix:
    def test_empty_project(self, tmp_path: Path) -> None:
        engine = FieldAlignmentEngine(tmp_path)
        matrix = engine.build_traceability_matrix()
        assert isinstance(matrix, TraceabilityMatrix)
        assert matrix.fields_total == 0
        assert matrix.fields_traced == 0

    def test_session_id_propagated(self, tmp_path: Path) -> None:
        engine = FieldAlignmentEngine(tmp_path)
        matrix = engine.build_traceability_matrix(session_id="sess-123")
        assert matrix.session_id == "sess-123"

    def test_contract_fields_discovered(self, tmp_path: Path) -> None:
        _write_contract(tmp_path, "user.md", SIMPLE_TABLE_MD)
        engine = FieldAlignmentEngine(tmp_path)
        matrix = engine.build_traceability_matrix()
        assert matrix.fields_total == 4
        names = {e.field_name for e in matrix.entries}
        assert "user_id" in names
        assert "name" in names

    def test_contract_ref_populated(self, tmp_path: Path) -> None:
        _write_contract(tmp_path, "user.md", SIMPLE_TABLE_MD)
        engine = FieldAlignmentEngine(tmp_path)
        matrix = engine.build_traceability_matrix()
        for entry in matrix.entries:
            assert entry.contract_ref != ""
            assert "user.md" in entry.contract_ref

    def test_implementation_ref_populated(self, tmp_path: Path) -> None:
        _write_contract(tmp_path, "user.md", SIMPLE_TABLE_MD)
        _write_source(tmp_path, "src/models/user.py", MATCHING_IMPL)
        engine = FieldAlignmentEngine(tmp_path)
        matrix = engine.build_traceability_matrix()

        traced = [e for e in matrix.entries if e.implementation_ref != ""]
        assert len(traced) > 0

    def test_verification_ref_populated(self, tmp_path: Path) -> None:
        _write_contract(tmp_path, "user.md", SIMPLE_TABLE_MD)
        _write_source(tmp_path, "src/models/user.py", MATCHING_IMPL)
        _write_test_file(
            tmp_path, "tests/test_user.py", "# test that user_id and name are correct\n"
        )
        engine = FieldAlignmentEngine(tmp_path)
        matrix = engine.build_traceability_matrix()

        verified = [e for e in matrix.entries if e.verification_ref != ""]
        assert len(verified) > 0

    def test_fields_traced_count(self, tmp_path: Path) -> None:
        _write_contract(tmp_path, "user.md", SIMPLE_TABLE_MD)
        _write_source(tmp_path, "src/models/user.py", MATCHING_IMPL)
        engine = FieldAlignmentEngine(tmp_path)
        matrix = engine.build_traceability_matrix()

        # fields_traced counts entries with both contract_ref and implementation_ref
        expected_traced = sum(
            1 for e in matrix.entries if e.contract_ref and e.implementation_ref
        )
        assert matrix.fields_traced == expected_traced

    def test_generated_at_populated(self, tmp_path: Path) -> None:
        engine = FieldAlignmentEngine(tmp_path)
        matrix = engine.build_traceability_matrix()
        assert matrix.generated_at != ""

    def test_duplicate_fields_deduplicated(self, tmp_path: Path) -> None:
        """If two contract files declare the same field, it appears once."""
        _write_contract(tmp_path, "a.md", SIMPLE_TABLE_MD)
        _write_contract(tmp_path, "b.md", SIMPLE_TABLE_MD)
        engine = FieldAlignmentEngine(tmp_path)
        matrix = engine.build_traceability_matrix()
        names = [e.field_name for e in matrix.entries]
        assert len(names) == len(set(names))


# ===================================================================
# _normalize_type() tests
# ===================================================================


class TestNormalizeType:
    """Test _FieldVisitor._normalize_type() static method.

    The normalisation uses _PY_TYPE_NORMALIZE dict lookups which
    preserve the exact mapped value (e.g. ``UUID`` stays ``UUID``,
    ``NoneType`` becomes ``None``).  Types NOT in the dict are
    lowercased.
    """

    def test_optional_str(self) -> None:
        assert _FieldVisitor._normalize_type("Optional[str]") == "str"

    def test_str_pipe_none(self) -> None:
        assert _FieldVisitor._normalize_type("str | None") == "str"

    def test_optional_int(self) -> None:
        assert _FieldVisitor._normalize_type("Optional[int]") == "int"

    def test_plain_str(self) -> None:
        assert _FieldVisitor._normalize_type("str") == "str"

    def test_plain_int(self) -> None:
        assert _FieldVisitor._normalize_type("int") == "int"

    def test_uuid_stays_uppercase(self) -> None:
        # _PY_TYPE_NORMALIZE maps "UUID" → "UUID"
        assert _FieldVisitor._normalize_type("UUID") == "UUID"

    def test_datetime(self) -> None:
        assert _FieldVisitor._normalize_type("datetime") == "datetime"

    def test_bool(self) -> None:
        assert _FieldVisitor._normalize_type("bool") == "bool"

    def test_float(self) -> None:
        assert _FieldVisitor._normalize_type("float") == "float"

    def test_none_type_maps_to_none(self) -> None:
        # _PY_TYPE_NORMALIZE maps "NoneType" → "None"
        assert _FieldVisitor._normalize_type("NoneType") == "None"

    def test_whitespace_stripped(self) -> None:
        assert _FieldVisitor._normalize_type("  str  ") == "str"

    def test_unknown_type_lowered(self) -> None:
        assert _FieldVisitor._normalize_type("MyCustomType") == "mycustomtype"

    def test_optional_uuid(self) -> None:
        assert _FieldVisitor._normalize_type("Optional[UUID]") == "UUID"

    def test_int_pipe_none(self) -> None:
        assert _FieldVisitor._normalize_type("int | None") == "int"

    def test_decimal(self) -> None:
        assert _FieldVisitor._normalize_type("Decimal") == "Decimal"

    def test_path(self) -> None:
        assert _FieldVisitor._normalize_type("Path") == "Path"


# ===================================================================
# _types_compatible() tests
# ===================================================================


class TestTypesCompatible:
    def test_same_types(self) -> None:
        assert _FieldVisitor._types_compatible("str", "str") is True

    def test_lowercase_uuid_and_str(self) -> None:
        # The compatibility check uses lowercase "uuid" in the set.
        assert _FieldVisitor._types_compatible("uuid", "str") is True
        assert _FieldVisitor._types_compatible("str", "uuid") is True

    def test_uppercase_uuid_and_str_compatible(self) -> None:
        # _types_compatible now lowercases both sides before the set
        # check, so "UUID" (uppercase) is correctly treated as
        # compatible with "str".
        assert _FieldVisitor._types_compatible("UUID", "str") is True
        assert _FieldVisitor._types_compatible("str", "UUID") is True

    def test_int_and_float(self) -> None:
        assert _FieldVisitor._types_compatible("int", "float") is True
        assert _FieldVisitor._types_compatible("float", "int") is True

    def test_inferred_always_compatible(self) -> None:
        assert _FieldVisitor._types_compatible("str", "inferred") is True
        assert _FieldVisitor._types_compatible("int", "inferred") is True

    def test_any_always_compatible(self) -> None:
        assert _FieldVisitor._types_compatible("any", "str") is True
        assert _FieldVisitor._types_compatible("str", "any") is True

    def test_incompatible_types(self) -> None:
        assert _FieldVisitor._types_compatible("str", "int") is False

    def test_bool_vs_str_incompatible(self) -> None:
        assert _FieldVisitor._types_compatible("bool", "str") is False

    def test_dict_vs_list_incompatible(self) -> None:
        assert _FieldVisitor._types_compatible("dict", "list") is False


# ===================================================================
# _detect_language() tests
# ===================================================================


class TestDetectLanguage:
    def test_python(self) -> None:
        assert FieldAlignmentEngine._detect_language(Path("foo.py")) == "Python"

    def test_typescript(self) -> None:
        assert FieldAlignmentEngine._detect_language(Path("foo.ts")) == "TypeScript"

    def test_tsx(self) -> None:
        assert FieldAlignmentEngine._detect_language(Path("foo.tsx")) == "TypeScript"

    def test_javascript(self) -> None:
        assert FieldAlignmentEngine._detect_language(Path("foo.js")) == "JavaScript"

    def test_mjs(self) -> None:
        assert FieldAlignmentEngine._detect_language(Path("foo.mjs")) == "JavaScript"

    def test_java(self) -> None:
        assert FieldAlignmentEngine._detect_language(Path("Foo.java")) == "Java"

    def test_kotlin(self) -> None:
        assert FieldAlignmentEngine._detect_language(Path("Foo.kt")) == "Kotlin"

    def test_csharp(self) -> None:
        assert FieldAlignmentEngine._detect_language(Path("Foo.cs")) == "C#"

    def test_go(self) -> None:
        assert FieldAlignmentEngine._detect_language(Path("main.go")) == "Go"

    def test_rust(self) -> None:
        assert FieldAlignmentEngine._detect_language(Path("main.rs")) == "Rust"

    def test_ruby(self) -> None:
        assert FieldAlignmentEngine._detect_language(Path("app.rb")) == "Ruby"

    def test_swift(self) -> None:
        assert FieldAlignmentEngine._detect_language(Path("App.swift")) == "Swift"

    def test_c(self) -> None:
        assert FieldAlignmentEngine._detect_language(Path("main.c")) == "C"

    def test_cpp(self) -> None:
        assert FieldAlignmentEngine._detect_language(Path("main.cpp")) == "C++"

    def test_cc(self) -> None:
        assert FieldAlignmentEngine._detect_language(Path("main.cc")) == "C++"

    def test_unknown_extension(self) -> None:
        assert FieldAlignmentEngine._detect_language(Path("data.csv")) == "unknown"

    def test_no_extension(self) -> None:
        assert FieldAlignmentEngine._detect_language(Path("Makefile")) == "unknown"


# ===================================================================
# _field_in_source() tests
# ===================================================================


class TestFieldInSource:
    def test_field_present(self) -> None:
        assert (
            FieldAlignmentEngine._field_in_source("user_id", "self.user_id = 1") is True
        )

    def test_field_absent(self) -> None:
        assert (
            FieldAlignmentEngine._field_in_source("user_id", "self.name = ''") is False
        )

    def test_word_boundary(self) -> None:
        # "name" should NOT match inside "username"
        assert (
            FieldAlignmentEngine._field_in_source("name", "username = 'foo'") is False
        )

    def test_field_in_comment(self) -> None:
        assert (
            FieldAlignmentEngine._field_in_source("email", "# check email field")
            is True
        )


# ===================================================================
# Gate hook tests
# ===================================================================


class TestGateHookAlignmentContract:
    def test_no_contracts_dir_passes(self, tmp_path: Path) -> None:
        failures = _gate_hook_alignment_contract(None, tmp_path)
        assert failures == []

    def test_valid_contract_passes(self, tmp_path: Path) -> None:
        _write_contract(tmp_path, "user.md", SIMPLE_TABLE_MD)
        failures = _gate_hook_alignment_contract(None, tmp_path)
        assert failures == []

    def test_contract_without_specs_fails(self, tmp_path: Path) -> None:
        _write_contract(tmp_path, "empty.md", EMPTY_TABLE_MD)
        failures = _gate_hook_alignment_contract(None, tmp_path)
        assert len(failures) == 1
        assert "no parseable field specifications" in failures[0].lower()

    def test_duplicate_field_names_fails(self, tmp_path: Path) -> None:
        _write_contract(tmp_path, "dupes.md", DUPLICATE_FIELD_TABLE_MD)
        failures = _gate_hook_alignment_contract(None, tmp_path)
        assert len(failures) == 1
        assert "duplicate" in failures[0].lower()

    def test_multiple_contracts_mixed(self, tmp_path: Path) -> None:
        _write_contract(tmp_path, "good.md", SIMPLE_TABLE_MD)
        _write_contract(tmp_path, "bad.md", EMPTY_TABLE_MD)
        failures = _gate_hook_alignment_contract(None, tmp_path)
        # Only the bad contract should fail
        assert len(failures) == 1
        assert "bad.md" in failures[0]

    def test_json_schema_contract_passes(self, tmp_path: Path) -> None:
        _write_contract(tmp_path, "order.md", JSON_SCHEMA_MD)
        failures = _gate_hook_alignment_contract(None, tmp_path)
        assert failures == []


class TestGateHookAlignmentImpl:
    def test_passing_alignment(self, tmp_path: Path) -> None:
        _write_contract(tmp_path, "user.md", SIMPLE_TABLE_MD)
        _write_source(tmp_path, "src/models/user.py", MATCHING_IMPL)
        failures = _gate_hook_alignment_impl(None, tmp_path)
        assert failures == []

    def test_failing_alignment_missing_field(self, tmp_path: Path) -> None:
        _write_contract(tmp_path, "user.md", SIMPLE_TABLE_MD)
        _write_source(tmp_path, "src/models/user.py", MISSING_FIELD_IMPL)
        failures = _gate_hook_alignment_impl(None, tmp_path)
        assert len(failures) > 0
        assert any("alignment error" in f.lower() for f in failures)

    def test_failing_alignment_type_mismatch(self, tmp_path: Path) -> None:
        _write_contract(tmp_path, "user.md", SIMPLE_TABLE_MD)
        _write_source(tmp_path, "src/models/user.py", TYPE_MISMATCH_IMPL)
        failures = _gate_hook_alignment_impl(None, tmp_path)
        assert len(failures) > 0
        assert any("type_mismatch" in f for f in failures)

    def test_unsupported_languages_downgraded(self, tmp_path: Path) -> None:
        """When compute_alignment only finds non-Python source (which it
        won't, since it globs *.py), unsupported_languages is empty and
        the gate passes.  This verifies the gate hook does not crash
        when there are no Python source files at all.
        """
        _write_contract(tmp_path, "user.md", SIMPLE_TABLE_MD)
        # No Python source files → all fields missing → errors.
        # But compute_alignment only globs *.py, so unsupported_languages
        # is always empty from the full pipeline.
        failures = _gate_hook_alignment_impl(None, tmp_path)
        # Missing fields cause failures
        assert len(failures) > 0

    def test_no_contracts_passes(self, tmp_path: Path) -> None:
        failures = _gate_hook_alignment_impl(None, tmp_path)
        assert failures == []

    def test_empty_contracts_dir_passes(self, tmp_path: Path) -> None:
        (tmp_path / "docs" / "contracts").mkdir(parents=True)
        failures = _gate_hook_alignment_impl(None, tmp_path)
        assert failures == []


# ===================================================================
# _FieldVisitor AST tests
# ===================================================================


class TestFieldVisitorAST:
    """Direct tests for the AST visitor used by scan_implementation."""

    def _make_specs(self, fields: dict[str, str]) -> dict[str, FieldAlignmentSpec]:
        return {
            name: FieldAlignmentSpec(field_name=name, field_type=ftype)
            for name, ftype in fields.items()
        }

    def test_class_annotation_match(self) -> None:
        source = "class Foo:\n    bar: str\n"
        spec_map = self._make_specs({"bar": "str"})
        visitor = _FieldVisitor("test.py", spec_map)
        visitor.visit(ast.parse(source))
        assert "bar" in visitor.found_fields

    def test_class_annotation_type_mismatch_via_init(self) -> None:
        """Use __init__-style plain assignment to test type_mismatch detection.

        ``_scan_init_assignments`` walks ``ast.Assign`` nodes only, so we
        use ``self.bar = 0`` (not ``self.bar: int = 0``).  The inferred
        type "inferred" is treated as compatible with any contract type
        by ``_types_compatible``, so we verify the field is *found* rather
        than producing a type_mismatch.
        """
        source = textwrap.dedent("""\
            class Foo:
                def __init__(self):
                    self.bar = 0
        """)
        spec_map = self._make_specs({"bar": "str"})
        visitor = _FieldVisitor("test.py", spec_map)
        visitor.visit(ast.parse(source))

        # The field should be found (present in found_fields).
        assert "bar" in visitor.found_fields
        # "inferred" is compatible with any contract type → no mismatch.
        mismatches = [f for f in visitor.findings if f.issue == "type_mismatch"]
        assert len(mismatches) == 0

    def test_class_level_annotation_double_visited(self) -> None:
        """Class-level AnnAssign nodes are visited by both visit_ClassDef
        and visit_AnnAssign (via generic_visit), producing duplicate findings.
        This documents the current behaviour.
        """
        source = "class Foo:\n    bar: int\n"
        spec_map = self._make_specs({"bar": "str"})
        visitor = _FieldVisitor("test.py", spec_map)
        visitor.visit(ast.parse(source))

        mismatches = [f for f in visitor.findings if f.issue == "type_mismatch"]
        # Two findings for the same field due to double visitation
        assert len(mismatches) == 2
        assert all(f.contract_field == "bar" for f in mismatches)

    def test_init_assignment_match(self) -> None:
        source = textwrap.dedent("""\
            class Foo:
                def __init__(self):
                    self.bar = "hello"
                    self.baz = 42
        """)
        spec_map = self._make_specs({"bar": "str", "baz": "int"})
        visitor = _FieldVisitor("test.py", spec_map)
        visitor.visit(ast.parse(source))
        assert "bar" in visitor.found_fields
        assert "baz" in visitor.found_fields

    def test_private_fields_ignored(self) -> None:
        source = textwrap.dedent("""\
            class Foo:
                def __init__(self):
                    self._internal = "private"
        """)
        spec_map = self._make_specs({})
        visitor = _FieldVisitor("test.py", spec_map)
        visitor.visit(ast.parse(source))
        # Private fields should not produce extra_field findings
        extras = [f for f in visitor.findings if f.issue == "extra_field"]
        assert len(extras) == 0

    def test_private_class_annotations_ignored(self) -> None:
        source = "class Foo:\n    _private: str\n"
        spec_map = self._make_specs({})
        visitor = _FieldVisitor("test.py", spec_map)
        visitor.visit(ast.parse(source))
        # _private starts with underscore → should not be checked
        # (visit_ClassDef skips AnnAssign if target.id starts with _)
        # But visit_AnnAssign also skips if target.id starts with _
        extras = [f for f in visitor.findings if f.issue == "extra_field"]
        assert len(extras) == 0

    def test_top_level_annotated_assignment(self) -> None:
        source = "API_VERSION: str = '1.0'\n"
        spec_map = self._make_specs({"API_VERSION": "str"})
        visitor = _FieldVisitor("test.py", spec_map)
        visitor.visit(ast.parse(source))
        assert "API_VERSION" in visitor.found_fields

    def test_union_type_pep604(self) -> None:
        """str | None annotations should be normalized and compatible."""
        source = "class Foo:\n    bar: str | None\n"
        spec_map = self._make_specs({"bar": "Optional[str]"})
        visitor = _FieldVisitor("test.py", spec_map)
        visitor.visit(ast.parse(source))
        # Should match without type_mismatch
        assert "bar" in visitor.found_fields
        mismatches = [f for f in visitor.findings if f.issue == "type_mismatch"]
        assert len(mismatches) == 0

    def test_subscript_type(self) -> None:
        source = "class Foo:\n    items: list[int]\n"
        spec_map = self._make_specs({"items": "list"})
        visitor = _FieldVisitor("test.py", spec_map)
        visitor.visit(ast.parse(source))
        # list[int] vs list — the normalized forms differ, but we
        # verify no crash occurs and the field is found.
        assert "items" in visitor.found_fields

    def test_function_param_annotation(self) -> None:
        source = "def greet(name: str, age: int) -> None:\n    pass\n"
        spec_map = self._make_specs({"name": "str", "age": "int"})
        visitor = _FieldVisitor("test.py", spec_map)
        visitor.visit(ast.parse(source))
        assert "name" in visitor.found_fields
        assert "age" in visitor.found_fields

    def test_self_arg_skipped(self) -> None:
        """The 'self' parameter in methods should not be checked."""
        source = textwrap.dedent("""\
            class Foo:
                def __init__(self):
                    pass
        """)
        spec_map = self._make_specs({})
        visitor = _FieldVisitor("test.py", spec_map)
        visitor.visit(ast.parse(source))
        extras = [f for f in visitor.findings if f.implementation_field == "self"]
        assert len(extras) == 0

    def test_extra_field_finding_has_source_info(self) -> None:
        source = textwrap.dedent("""\
            class Foo:
                def __init__(self):
                    self.extra = "data"
        """)
        spec_map = self._make_specs({})
        visitor = _FieldVisitor("test.py", spec_map)
        visitor.visit(ast.parse(source))
        extras = [f for f in visitor.findings if f.issue == "extra_field"]
        assert len(extras) >= 1
        assert extras[0].source_file == "test.py"
        assert extras[0].source_line > 0
