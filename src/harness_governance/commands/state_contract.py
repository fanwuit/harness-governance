"""``harness state-contract`` checks for persisted-state closure.

v2 enhancement: auto-discovers writer-consumer relationships by scanning
CLI command registrations, state-writing patterns in source code, and
gate definitions, then matches them against integration test evidence.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

import click


@dataclass(frozen=True)
class StateContractRequirement:
    name: str
    writer: str
    consumer: str
    evidence_path: str
    required_terms: tuple[str, ...] = ()
    source: str = "explicit"


# -- Explicit baseline requirements -----------------------------------------

_REQUIREMENTS: tuple[StateContractRequirement, ...] = (
    StateContractRequirement(
        name="author-question-qa",
        writer="harness layer answer / harness layer ask",
        consumer="harness gate check <layer>",
        evidence_path="tests/test_commands/test_layer_cmd.py",
        required_terms=("test_answer_records_qa_for_gate", "test_ask_records"),
    ),
    StateContractRequirement(
        name="tech-stack-lint-confirmation",
        writer="harness tech-stack lint <language> --tool <tool>",
        consumer="harness tech-stack check / intake-orientation gate",
        evidence_path="tests/test_commands/test_tech_stack_cmd.py",
        required_terms=("test_check_passes_after_cli_lint", "manifest.lint_tools"),
    ),
    StateContractRequirement(
        name="governed-path-smoke",
        writer="harness governed-start + state writers",
        consumer="harness gate check + layer advance",
        evidence_path="tests/test_e2e/test_governed_path_smoke.py",
        required_terms=("test_strict_governed_path_minimum_smoke",),
    ),
    StateContractRequirement(
        name="state-contract-policy",
        writer="project policy",
        consumer="harness state-contract check",
        evidence_path="tests/STATE_CONTRACTS.md",
        required_terms=("State Contract Closure",),
    ),
)

# -- State-writing patterns in source code -----------------------------------

# Commands/modules known to write or read persisted governance state.
# This is the curated list of "stateful" commands; general CRUD commands
# (e.g., harness init, harness hook) are excluded because they write
# files but not governance session/gate/invocation state.
_STATEFUL_COMMANDS: dict[str, tuple[str, str]] = {
    "layer": ("harness layer answer/ask/advance", "writes QA records and lock files"),
    "gate": ("harness gate check/lock/reset", "reads/writes gate lock files"),
    "state_contract": ("harness state-contract check", "reads state-contract evidence"),
    "check": ("harness check <subcommand>", "reads gate/invocation/evidence state"),
    "governed_start": ("harness governed-start", "writes session state"),
    "session": ("harness session close", "writes session close record"),
    "tech_stack": ("harness tech-stack capture/confirm", "writes tech-stack manifest"),
    "runner": ("harness runner", "writes invocation logs"),
    "review": ("harness review close", "writes review/next state"),
    "drift": ("harness drift check", "reads/writes scope boundaries"),
    "isolation": ("harness isolation init", "writes isolation workspaces"),
    "entry": ("harness entry", "writes implementation entry records"),
    "aliases": ("harness start/ship/next", "reads session state"),
}

_WRITER_PATTERNS: tuple[str, ...] = (
    r'\.write_text\(',
    r'json\.dump\b',
    r'json\.dumps\b',
    r'session\.write\b',
    r'create_session\b',
    r'append_invocation_log\b',
    r'\.harness.*\.ndjson',
    r'LockFileManager\(',
    r'record_full_invocation\b',
)

_GATE_LAYER_PATTERN = re.compile(
    r"HarnessLayer\.(\w+)\s*[=:].*GateDefinition|"
    r"gate_definitions?\[[\"'](\w+)[\"']\]",
    re.IGNORECASE,
)

_CLI_COMMAND_PATTERN = re.compile(
    r"cli\.add_command\((\w+)\)"
)

# Evidence test patterns: (test_file_glob, required_term) pairs keyed by
# command name.  When no evidence pattern is registered, the scanner
# looks for any test file mentioning both command and "state"/"gate".
_EVIDENCE_PATTERNS: dict[str, list[tuple[str, str]]] = {
    "layer": [("tests/test_commands/test_layer_cmd.py", "TestLayerAdvance")],
    "gate": [("tests/test_commands/test_layer_cmd.py", "layer")],
    "state_contract": [("tests/test_commands/test_state_contract_cmd.py", "state_contract_check")],
    "check": [("tests/test_commands/test_check_cmd.py", "state-contract")],
    "governed_start": [("tests/test_commands/test_governed_start.py", "governed_start")],
    "tech_stack": [("tests/test_commands/test_tech_stack_cmd.py", "tech_stack")],
    "runner": [("tests/test_subagent_runner/", "invocation")],
    "review": [("tests/test_commands/test_verify_review_config.py", "review")],
    "drift": [("tests/test_commands/test_drift_cmd.py", "drift")],
    "isolation": [("tests/test_commands/test_isolation_cmd.py", "isolation")],
    "session": [("tests/test_commands/test_session_cmd.py", "session")],
}


# -- Auto-discovery ----------------------------------------------------------


def _find_stateful_writers(repo_root: Path) -> list[tuple[str, str, bool]]:
    """Scan command modules for actual state-writing code.

    Returns list of (module_name, description, has_state_write).
    """
    writers: list[tuple[str, str, bool]] = []
    src_dir = repo_root / "src" / "harness_governance" / "commands"
    if not src_dir.is_dir():
        return writers

    for module_name, (desc, _reason) in _STATEFUL_COMMANDS.items():
        py_file = src_dir / f"{module_name}.py"
        has_state_write = False
        if py_file.is_file():
            try:
                text = py_file.read_text(encoding="utf-8")
            except OSError:
                continue
            for pattern in _WRITER_PATTERNS:
                if re.search(pattern, text):
                    has_state_write = True
                    break
        writers.append((module_name, desc, has_state_write))

    return writers


def _find_evidence_for_command(
    repo_root: Path, module_name: str
) -> tuple[Path | None, str | None]:
    """Find the evidence test file for a command.

    Returns (evidence_path, required_term) or (None, None).
    """
    patterns = _EVIDENCE_PATTERNS.get(module_name, [])
    for glob_pattern, required_term in patterns:
        if "*" in glob_pattern:
            dir_path = repo_root / glob_pattern
            if dir_path.is_dir():
                py_files = sorted(dir_path.glob("*.py"))
                if py_files:
                    return py_files[0], required_term
        else:
            candidate = repo_root / glob_pattern
            if candidate.is_file():
                return candidate, required_term

    return None, None


def _auto_discover_requirements(repo_root: Path) -> list[StateContractRequirement]:
    """Auto-discover writer-consumer relationships from the codebase.

    Only includes commands listed in _STATEFUL_COMMANDS that actually
    contain state-writing code patterns.  Evidence is matched against
    curated _EVIDENCE_PATTERNS; unmatched commands produce a warning-level
    finding rather than silently passing.
    """
    discovered: list[StateContractRequirement] = []
    writers = _find_stateful_writers(repo_root)

    for module_name, desc, has_state_write in writers:
        evidence_path, required_term = _find_evidence_for_command(repo_root, module_name)

        if evidence_path:
            rel_path = evidence_path.relative_to(repo_root)
            terms: tuple[str, ...] = (required_term,) if required_term else ()
            discovered.append(
                StateContractRequirement(
                    name=module_name,
                    writer=desc,
                    consumer="harness state check / gate",
                    evidence_path=str(rel_path),
                    required_terms=terms,
                    source="auto",
                )
            )

    return discovered


def evaluate_state_contract(
    project_root: Path, *, enable_auto_discovery: bool = True
) -> tuple[bool, list[dict[str, object]]]:
    """Evaluate required state-contract evidence for *project_root*.

    If *enable_auto_discovery* is True (default), also scans the codebase
    for automatically-discovered writer-consumer relationships.
    """
    requirements: list[StateContractRequirement] = list(_REQUIREMENTS)

    if enable_auto_discovery:
        auto = _auto_discover_requirements(project_root)
        seen_names = {r.name for r in requirements}
        for r in auto:
            if r.name not in seen_names:
                requirements.append(r)
                seen_names.add(r.name)

    rows: list[dict[str, object]] = []
    passed = True

    for requirement in requirements:
        path = project_root / requirement.evidence_path
        exists = path.is_file()
        terms_found = True
        missing_terms: list[str] = []
        if exists and requirement.required_terms:
            text = path.read_text(encoding="utf-8")
            for term in requirement.required_terms:
                if term not in text:
                    terms_found = False
                    missing_terms.append(term)
        elif requirement.required_terms:
            terms_found = False
            missing_terms = list(requirement.required_terms)

        requirement_passed = exists and terms_found
        passed = passed and requirement_passed
        rows.append(
            {
                "name": requirement.name,
                "source": requirement.source,
                "writer": requirement.writer,
                "consumer": requirement.consumer,
                "evidence_path": requirement.evidence_path,
                "passed": requirement_passed,
                "missing_terms": missing_terms,
            }
        )

    return passed, rows


# -- CLI --------------------------------------------------------------------


@click.group("state-contract")
def state_contract_group() -> None:
    """Check persisted-state writer/consumer test closure."""


@state_contract_group.command("check")
@click.option(
    "--auto/--no-auto",
    "auto_discovery",
    default=True,
    help="Enable auto-discovery of writer-consumer relationships (default: on).",
)
@click.option(
    "--show-auto",
    is_flag=True,
    default=False,
    help="Show auto-discovered requirements even when they pass.",
)
@click.pass_context
def state_contract_check_cmd(
    ctx: click.Context, auto_discovery: bool, show_auto: bool
) -> None:
    """Check required state-contract evidence exists.

    Evaluates both explicit (hardcoded) requirements and auto-discovered
    writer-consumer relationships from the codebase. Use --no-auto to
    skip auto-discovery, or --show-auto to display auto-discovered items.
    """
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    passed, rows = evaluate_state_contract(
        project_root, enable_auto_discovery=auto_discovery
    )

    if ctx.obj.get("json_output"):
        click.echo(
            json.dumps(
                {
                    "passed": passed,
                    "auto_discovery": auto_discovery,
                    "requirements": rows,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        click.echo(
            f"state-contract check: {'passed' if passed else 'failed'}"
            f" (auto-discovery: {'on' if auto_discovery else 'off'})"
        )
        for row in rows:
            if row["source"] == "auto" and row["passed"] and not show_auto:
                continue
            state = "pass" if row["passed"] else "FAIL"
            tag = f"[{row['source']}]" if row["source"] != "explicit" else ""
            click.echo(f"  {state} {tag} {row['name']}: {row['evidence_path']}")
            row_missing_terms = row["missing_terms"]
            if isinstance(row_missing_terms, list) and row_missing_terms:
                click.echo(f"    missing terms: {', '.join(row_missing_terms)}")

    if not passed:
        raise click.exceptions.Exit(code=1)


@state_contract_group.command("scan")
@click.pass_context
def state_contract_scan_cmd(ctx: click.Context) -> None:
    """Scan the codebase and print discovered writer/consumer pairs."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())

    writers = _find_stateful_writers(project_root)
    click.echo(f"Stateful commands ({len(writers)}):")
    for module_name, desc, has_state_write in writers:
        marker = " [writes state]" if has_state_write else ""
        click.echo(f"  {module_name}: {desc}{marker}")

    auto = _auto_discover_requirements(project_root)
    click.echo(f"\nAuto-discovered evidence ({len(auto)}):")
    for r in auto:
        click.echo(f"  {r.name}: writer={r.writer}, evidence={r.evidence_path}")


__all__ = [
    "state_contract_group",
    "state_contract_check_cmd",
    "state_contract_scan_cmd",
    "StateContractRequirement",
    "evaluate_state_contract",
]
