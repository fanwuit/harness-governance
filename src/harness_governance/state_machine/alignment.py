"""Field alignment between contract and implementation — Gap 2 of the v0.8.0 release.

Extracts field specifications from contract documents (markdown tables,
JSON schema blocks), scans Python implementation source via the ``ast``
module, and produces an :class:`AlignmentReport` with mismatches.

v0.8.0 supports **Python only** for implementation scanning.  Non-Python
projects produce an ``AlignmentReport`` with ``unsupported_languages``
populated — the gate hook downgrades these to warnings.
"""

from __future__ import annotations

import ast
import logging
import re
from datetime import datetime, timezone
from pathlib import Path

from ..models.schemas import (
    AlignmentFinding,
    AlignmentReport,
    FieldAlignmentSpec,
    TraceabilityEntry,
    TraceabilityMatrix,
)

logger = logging.getLogger("harness.alignment")

# File extension → language name mapping.
_EXT_TO_LANGUAGE: dict[str, str] = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".mjs": "JavaScript",
    ".java": "Java",
    ".kt": "Kotlin",
    ".cs": "C#",
    ".go": "Go",
    ".rs": "Rust",
    ".rb": "Ruby",
    ".swift": "Swift",
    ".c": "C",
    ".cpp": "C++",
    ".cc": "C++",
}

# Python type name → canonical form for comparison.
_PY_TYPE_NORMALIZE: dict[str, str] = {
    "str": "str",
    "int": "int",
    "float": "float",
    "bool": "bool",
    "bytes": "bytes",
    "dict": "dict",
    "list": "list",
    "set": "set",
    "tuple": "tuple",
    "NoneType": "None",
    "UUID": "UUID",
    "datetime": "datetime",
    "date": "date",
    "Path": "Path",
    "Decimal": "Decimal",
}


class FieldAlignmentEngine:
    """Extract contract specs, scan implementation, and compare fields.

    Usage::

        engine = FieldAlignmentEngine(project_root)
        specs = engine.extract_specs(Path("docs/contracts/user-api.md"))
        findings = engine.scan_implementation(
            [Path("src/models/user.py")], specs
        )
        report = engine.compute_alignment("contract", "implementation")
    """

    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root

    # -- Public API -------------------------------------------------------

    def extract_specs(self, contract_file: Path) -> list[FieldAlignmentSpec]:
        """Parse *contract_file* and extract field specifications.

        Supports:
        - Markdown tables with ``Field | Type | Required`` columns.
        - Fenced JSON Schema blocks (`````json ... ``` ``).
        """
        if not contract_file.is_file():
            return []

        try:
            content = contract_file.read_text(encoding="utf-8")
        except Exception:
            logger.warning("Cannot read contract file: %s", contract_file)
            return []

        specs: list[FieldAlignmentSpec] = []

        # Strategy 1: Markdown tables.
        specs.extend(self._parse_markdown_table(content, str(contract_file)))

        # Strategy 2: JSON Schema blocks.
        specs.extend(self._parse_json_schema_blocks(content, str(contract_file)))

        return specs

    def scan_implementation(
        self,
        source_files: list[Path],
        specs: list[FieldAlignmentSpec],
    ) -> tuple[list[AlignmentFinding], list[str]]:
        """Scan *source_files* for fields matching *specs*.

        Returns ``(findings, unsupported_languages)``.  For Python files
        the AST is used; other languages are recorded in the
        ``unsupported_languages`` list.

        If *specs* is empty, returns empty findings (no contract to
        validate against).
        """
        if not specs:
            return [], []

        findings: list[AlignmentFinding] = []
        unsupported: set[str] = set()
        spec_map: dict[str, FieldAlignmentSpec] = {s.field_name: s for s in specs}
        found_fields: set[str] = set()

        for sf in source_files:
            if not sf.is_file():
                continue

            lang = self._detect_language(sf)
            if lang != "Python":
                unsupported.add(lang)
                continue

            try:
                source = sf.read_text(encoding="utf-8")
            except Exception:
                continue

            file_findings, file_found = self._scan_python_ast(source, str(sf), spec_map)
            findings.extend(file_findings)
            found_fields.update(file_found)

        # Check for contract fields never found in any source file.
        for name, spec in spec_map.items():
            if name not in found_fields:
                findings.append(
                    AlignmentFinding(
                        issue="missing",
                        contract_field=name,
                        contract_type=spec.field_type,
                        severity="error",
                    )
                )

        return findings, sorted(unsupported)

    def compute_alignment(
        self,
        contract_layer: str = "contract",
        implementation_layer: str = "implementation",
    ) -> AlignmentReport:
        """Run the full alignment pipeline: extract → scan → report.

        *contract_layer* and *implementation_layer* are reserved for
        future layer-specific scoping; v0.8.0 scans all contracts and
        all Python source files in the project.
        """
        unsupported: set[str] = set()
        all_findings: list[AlignmentFinding] = []
        total_expected = 0
        total_matched = 0

        # Find contract documents.
        contracts_dir = self._project_root / "docs" / "contracts"
        contract_files = (
            list(contracts_dir.glob("*.md")) if contracts_dir.is_dir() else []
        )

        if not contract_files:
            return AlignmentReport(
                fields_expected=0,
                fields_matched=0,
                passed=True,
                generated_at=datetime.now(timezone.utc).isoformat(),
            )

        # Find source files (all known languages, not just Python).
        source_files: list[Path] = []
        src_dir = self._project_root / "src"
        if src_dir.is_dir():
            for ext in _EXT_TO_LANGUAGE:
                source_files.extend(src_dir.glob(f"**/*{ext}"))

        for cf in contract_files:
            specs = self.extract_specs(cf)
            if not specs:
                continue

            total_expected += len(specs)
            findings, unsup = self.scan_implementation(source_files, specs)
            all_findings.extend(findings)
            unsupported.update(unsup)

            # Count matched fields (those in specs that were found).
            found_names = {
                f.implementation_field for f in findings if f.issue not in ("missing",)
            }
            _matched = sum(
                1
                for s in specs
                if s.field_name in found_names
                or not any(
                    f.contract_field == s.field_name and f.issue == "missing"
                    for f in findings
                )
            )
            # More accurate: matched = expected - missing findings
            missing_count = sum(1 for f in findings if f.issue == "missing")
            total_matched += len(specs) - missing_count

        errors = [f for f in all_findings if f.severity == "error"]
        passed = len(errors) == 0

        return AlignmentReport(
            fields_expected=total_expected,
            fields_matched=max(0, total_matched),
            findings=tuple(all_findings),
            passed=passed,
            unsupported_languages=tuple(sorted(unsupported)),
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    def build_traceability_matrix(self, session_id: str = "") -> TraceabilityMatrix:
        """Build a cross-layer field traceability matrix.

        Scans artifacts across contract, adr, implementation, and
        verification layers to build per-field trace entries.
        v0.8.0 provides a skeleton — full cross-layer trace requires
        deeper artifact parsing planned for v0.9.0.
        """
        entries: list[TraceabilityEntry] = []
        fields_seen: set[str] = set()

        # Contract layer: extract field names.
        contracts_dir = self._project_root / "docs" / "contracts"
        if contracts_dir.is_dir():
            for cf in contracts_dir.glob("*.md"):
                specs = self.extract_specs(cf)
                for spec in specs:
                    if spec.field_name in fields_seen:
                        continue
                    fields_seen.add(spec.field_name)
                    entries.append(
                        TraceabilityEntry(
                            field_name=spec.field_name,
                            contract_ref=f"{cf.name}:{spec.source_line}",
                        )
                    )

        # Implementation layer: find field definitions in source.
        source_files = list(self._project_root.glob("src/**/*.py"))
        for entry in entries:
            for sf in source_files:
                try:
                    content = sf.read_text(encoding="utf-8")
                except Exception:
                    continue
                if self._field_in_source(entry.field_name, content):
                    entry.implementation_ref = str(sf.relative_to(self._project_root))
                    break

        # Verification layer: find field references in tests.
        test_files = list(self._project_root.glob("tests/**/*.py"))
        for entry in entries:
            for tf in test_files:
                try:
                    content = tf.read_text(encoding="utf-8")
                except Exception:
                    continue
                if entry.field_name in content:
                    entry.verification_ref = str(tf.relative_to(self._project_root))
                    break

        return TraceabilityMatrix(
            session_id=session_id,
            entries=tuple(entries),
            fields_total=len(entries),
            fields_traced=sum(
                1 for e in entries if e.contract_ref and e.implementation_ref
            ),
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    # -- Internal: Markdown table parsing ---------------------------------

    @staticmethod
    def _parse_markdown_table(
        content: str, source_path: str
    ) -> list[FieldAlignmentSpec]:
        """Extract field specs from markdown tables.

        Looks for tables with ``Field | Type | Required`` columns.
        """
        specs: list[FieldAlignmentSpec] = []

        # Find markdown table lines.
        lines = content.splitlines()
        in_table = False
        _headers: list[str] = []
        field_col = -1
        type_col = -1
        required_col = -1

        for line_no, line in enumerate(lines, start=1):
            stripped = line.strip()

            # Detect table start: a line starting/ending with | that
            # contains header-like content.
            if "|" in stripped and not in_table:
                parts = [c.strip().lower() for c in stripped.split("|")]
                parts = [p for p in parts if p]  # remove empty from leading/trailing |

                # Check for field/type/required column headers.
                field_idx = -1
                type_idx = -1
                req_idx = -1
                for i, h in enumerate(parts):
                    h_clean = h.strip().lower()
                    if h_clean in ("field", "name", "字段", "属性"):
                        field_idx = i
                    elif h_clean in ("type", "类型"):
                        type_idx = i
                    elif h_clean in ("required", "必填", "required?"):
                        req_idx = i

                if field_idx >= 0:
                    _headers = parts
                    field_col = field_idx
                    type_col = type_idx
                    required_col = req_idx
                    in_table = True
                    continue

            # Separator line (e.g. |---|---| or |-------|------|----------|).
            if in_table and all(
                re.fullmatch(r":?-+:?", c.strip())
                for c in stripped.split("|")
                if c.strip()
            ):
                continue

            # Data row.
            if in_table and "|" in stripped:
                parts = [c.strip() for c in stripped.split("|")]
                parts = [p for p in parts if p or parts.index(p) in (0, len(parts) - 1)]
                # Normalize: remove leading/trailing empties.
                while parts and not parts[0]:
                    parts.pop(0)
                while parts and not parts[-1]:
                    parts.pop()

                if field_col < len(parts) and parts[field_col]:
                    field_name = parts[field_col].strip("`*_ '\"")
                    field_type = (
                        parts[type_col].strip("`*_ '\"")
                        if type_col >= 0 and type_col < len(parts)
                        else "str"
                    )
                    is_required = True
                    if required_col >= 0 and required_col < len(parts):
                        req_val = parts[required_col].lower()
                        is_required = req_val in (
                            "yes",
                            "true",
                            "y",
                            "required",
                            "是",
                            "✓",
                            "必填",
                        )

                    specs.append(
                        FieldAlignmentSpec(
                            field_name=field_name,
                            field_type=field_type,
                            is_required=is_required,
                            source_contract=source_path,
                            source_line=line_no,
                        )
                    )
            elif in_table and not stripped:
                # Empty line ends the table.
                in_table = False
                field_col = -1
                type_col = -1
                required_col = -1

        return specs

    # -- Internal: JSON Schema parsing ------------------------------------

    @staticmethod
    def _parse_json_schema_blocks(
        content: str, source_path: str
    ) -> list[FieldAlignmentSpec]:
        """Extract field specs from fenced JSON Schema blocks."""
        specs: list[FieldAlignmentSpec] = []

        # Find ```json ... ``` blocks.
        block_pattern = re.compile(r"```json\s*\n(.*?)\n```", re.DOTALL)
        for match in block_pattern.finditer(content):
            try:
                import json

                schema = json.loads(match.group(1))
            except json.JSONDecodeError:
                continue

            props = schema.get("properties", {})
            required_list = schema.get("required", [])

            line_offset = content[: match.start()].count("\n") + 1

            for field_name, field_info in props.items():
                if isinstance(field_info, dict):
                    field_type = field_info.get("type", "string")
                    if field_type == "array" and "items" in field_info:
                        items = field_info["items"]
                        if isinstance(items, dict):
                            field_type = f"list[{items.get('type', 'any')}]"
                        else:
                            field_type = "list"
                else:
                    field_type = "string"

                specs.append(
                    FieldAlignmentSpec(
                        field_name=field_name,
                        field_type=str(field_type),
                        is_required=field_name in required_list,
                        source_contract=source_path,
                        source_line=line_offset,
                    )
                )

        return specs

    # -- Internal: Python AST scanning ------------------------------------

    def _scan_python_ast(
        self,
        source: str,
        source_path: str,
        spec_map: dict[str, FieldAlignmentSpec],
    ) -> tuple[list[AlignmentFinding], set[str]]:
        """Scan Python source with AST and compare against *spec_map*.

        Returns ``(findings, found_field_names)``.
        """
        findings: list[AlignmentFinding] = []
        found: set[str] = set()

        try:
            tree = ast.parse(source)
        except SyntaxError:
            logger.debug("Syntax error parsing %s — skipping", source_path)
            return findings, found

        visitor = _FieldVisitor(source_path, spec_map)
        visitor.visit(tree)

        findings.extend(visitor.findings)
        found.update(visitor.found_fields)
        return findings, found

    @staticmethod
    def _detect_language(file_path: Path) -> str:
        """Detect programming language from file extension."""
        suffix = file_path.suffix.lower()
        return _EXT_TO_LANGUAGE.get(suffix, "unknown")

    @staticmethod
    def _field_in_source(field_name: str, source: str) -> bool:
        """Quick check: does *field_name* appear as an identifier in *source*?"""
        # Look for the field name as a Python identifier (word boundary).
        return bool(re.search(rf"\b{re.escape(field_name)}\b", source))


# ---------------------------------------------------------------------------
# AST visitor — walks Python class/function definitions
# ---------------------------------------------------------------------------


class _FieldVisitor(ast.NodeVisitor):
    """Walk a Python AST and collect field definitions + compare against specs."""

    def __init__(
        self, source_path: str, spec_map: dict[str, FieldAlignmentSpec]
    ) -> None:
        self.source_path = source_path
        self.spec_map = spec_map
        self.findings: list[AlignmentFinding] = []
        self.found_fields: set[str] = set()

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Check class body for field assignments and annotations."""
        for item in node.body:
            # Instance attributes in __init__: self.xxx = value
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                self._scan_init_assignments(item)
            # Class-level annotations (dataclass-style).
            elif isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                if not item.target.id.startswith("_"):
                    self._check_annotation(item.target.id, item.annotation, item.lineno)
            # Plain class-level assignment with type comment.
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and not target.id.startswith("_"):
                        self._check_assignment(target.id, item.lineno)

        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check function parameters against spec (pydantic/dataclass __init__)."""
        for arg in node.args.args:
            if arg.arg == "self":
                continue
            if arg.annotation:
                self._check_annotation(arg.arg, arg.annotation, arg.lineno)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Top-level annotated assignments (module-level constants etc.)."""
        if isinstance(node.target, ast.Name) and not node.target.id.startswith("_"):
            self._check_annotation(node.target.id, node.annotation, node.lineno)
        self.generic_visit(node)

    # -- Internal ---------------------------------------------------------

    def _scan_init_assignments(self, func: ast.FunctionDef) -> None:
        """Scan ``self.xxx = ...`` assignments inside ``__init__``."""
        for node in ast.walk(func):
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if not isinstance(target, ast.Attribute):
                    continue
                if not isinstance(target.value, ast.Name):
                    continue
                if target.value.id != "self":
                    continue
                field_name = target.attr
                if field_name.startswith("_"):
                    continue
                self._check_assignment(field_name, node.lineno)

    def _check_annotation(
        self,
        field_name: str,
        annotation: ast.expr | None,
        lineno: int,
    ) -> None:
        """Compare an annotated field against the spec."""
        impl_type = self._expr_to_type_string(annotation) if annotation else "Any"
        self._compare(field_name, impl_type, lineno)

    def _check_assignment(self, field_name: str, lineno: int) -> None:
        """Compare an assigned field (type inferred) against the spec."""
        self._compare(field_name, "inferred", lineno)

    def _compare(self, field_name: str, impl_type: str, lineno: int) -> None:
        """Compare a found field against the spec map."""
        spec = self.spec_map.get(field_name)
        if spec is None:
            # Field exists in code but not in contract → extra_field (warning).
            self.findings.append(
                AlignmentFinding(
                    issue="extra_field",
                    implementation_field=field_name,
                    implementation_type=impl_type,
                    severity="warning",
                    source_file=self.source_path,
                    source_line=lineno,
                )
            )
            return

        self.found_fields.add(field_name)

        # Compare types (normalize both sides).
        contract_type = self._normalize_type(spec.field_type)
        norm_impl = self._normalize_type(impl_type)

        if contract_type and norm_impl and contract_type != norm_impl:
            # "Optional[X]" vs "X | None" — treat as compatible.
            if not self._types_compatible(contract_type, norm_impl):
                self.findings.append(
                    AlignmentFinding(
                        issue="type_mismatch",
                        contract_field=field_name,
                        contract_type=spec.field_type,
                        implementation_field=field_name,
                        implementation_type=impl_type,
                        severity="error",
                        source_file=self.source_path,
                        source_line=lineno,
                    )
                )

    @staticmethod
    def _expr_to_type_string(node: ast.expr) -> str:
        """Convert an AST annotation node to a string type representation."""
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Constant) and node.value is None:
            return "None"
        if isinstance(node, ast.Subscript):
            # e.g. Optional[str], list[int], dict[str, int]
            base = _FieldVisitor._expr_to_type_string(node.value)
            slice_str = _FieldVisitor._slice_to_string(node.slice)
            return f"{base}[{slice_str}]"
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            # X | Y (PEP 604 union)
            left = _FieldVisitor._expr_to_type_string(node.left)
            right = _FieldVisitor._expr_to_type_string(node.right)
            return f"{left} | {right}"
        if isinstance(node, ast.Attribute):
            return (
                f"{node.value.id}.{node.attr}"
                if isinstance(node.value, ast.Name)
                else node.attr
            )
        return "Any"

    @staticmethod
    def _slice_to_string(slice_node: ast.expr) -> str:
        """Convert an AST slice node to string."""
        if isinstance(slice_node, ast.Name):
            return slice_node.id
        if isinstance(slice_node, ast.Subscript):
            base = _FieldVisitor._expr_to_type_string(slice_node.value)
            inner = _FieldVisitor._slice_to_string(slice_node.slice)
            return f"{base}[{inner}]"
        if isinstance(slice_node, ast.Tuple):
            return ", ".join(
                _FieldVisitor._expr_to_type_string(e) for e in slice_node.elts
            )
        if isinstance(slice_node, ast.Constant):
            return str(slice_node.value)
        return "Any"

    @staticmethod
    def _normalize_type(type_str: str) -> str:
        """Normalize a type string for comparison."""
        t = type_str.strip()
        # Remove Optional[...] wrapper → keep inner type.
        opt_match = re.match(r"^Optional\[(.*)\]$", t)
        if opt_match:
            t = opt_match.group(1)
        # Remove trailing | None.
        t = re.sub(r"\s*\|\s*None$", "", t)
        # Map common names.
        return _PY_TYPE_NORMALIZE.get(t, t.lower())

    @staticmethod
    def _types_compatible(contract_type: str, impl_type: str) -> bool:
        """Return True if the two types are considered compatible."""
        if contract_type == impl_type:
            return True
        # "str" is compatible with "Any" / "inferred".
        if impl_type == "inferred" or impl_type == "any":
            return True
        if contract_type == "any":
            return True
        # UUID vs str (many codebases use str for UUID fields).
        if {contract_type.lower(), impl_type.lower()} <= {"uuid", "str"}:
            return True
        # int vs float.
        if {contract_type.lower(), impl_type.lower()} <= {"int", "float"}:
            return True
        return False


# ---------------------------------------------------------------------------
# Gate hook registration — called at import time
# ---------------------------------------------------------------------------


def _gate_hook_alignment_contract(
    session,  # SessionState
    project_root: Path,
) -> list[str]:
    """CONTRACT hook: validate contract field spec format completeness.

    Reads contract documents and ensures field tables are parseable.
    This is a read-only format check — the full alignment against
    implementation happens at the IMPLEMENTATION gate.
    """
    failures: list[str] = []
    engine = FieldAlignmentEngine(project_root)

    contracts_dir = project_root / "docs" / "contracts"
    if not contracts_dir.is_dir():
        return failures  # no contracts yet — not an error

    for cf in contracts_dir.glob("*.md"):
        specs = engine.extract_specs(cf)
        if not specs:
            failures.append(
                f"Contract file '{cf.name}' has no parseable field specifications. "
                f"Add a field table (| Field | Type | Required |) or JSON schema block."
            )
        else:
            # Check for duplicate field names.
            names = [s.field_name for s in specs]
            if len(names) != len(set(names)):
                dupes = {n for n in names if names.count(n) > 1}
                failures.append(
                    f"Contract '{cf.name}' has duplicate field names: {', '.join(sorted(dupes))}"
                )

    return failures


def _gate_hook_alignment_impl(
    session,  # SessionState
    project_root: Path,
) -> list[str]:
    """IMPLEMENTATION hook: run full field alignment check.

    Calls ``compute_alignment()`` and reports mismatches.
    Non-Python projects get a warning (not a blocking error).
    """
    failures: list[str] = []
    engine = FieldAlignmentEngine(project_root)

    report = engine.compute_alignment()

    if report.unsupported_languages:
        # Non-Python → downgrade to warning, not blocking.
        logger.warning(
            "Field alignment skipped for unsupported languages: %s",
            ", ".join(report.unsupported_languages),
        )
        return failures  # empty → gate passes (non-blocking)

    if not report.passed:
        for finding in report.findings:
            if finding.severity == "error":
                failures.append(
                    f"Alignment error: [{finding.issue}] "
                    f"contract '{finding.contract_field}' ({finding.contract_type}) "
                    f"vs impl '{finding.implementation_field}' ({finding.implementation_type})"
                    f"{' in ' + finding.source_file if finding.source_file else ''}"
                )

    return failures


# Module-level registration — fires when alignment is imported.
try:
    from .gates import HarnessLayer, register_gate_hook

    register_gate_hook(HarnessLayer.CONTRACT, _gate_hook_alignment_contract)
    register_gate_hook(HarnessLayer.IMPLEMENTATION, _gate_hook_alignment_impl)
except ImportError:
    pass
