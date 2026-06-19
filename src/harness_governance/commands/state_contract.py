"""``harness state-contract`` checks for persisted-state closure."""

from __future__ import annotations

import json
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


def evaluate_state_contract(project_root: Path) -> tuple[bool, list[dict[str, object]]]:
    """Evaluate required state-contract evidence for *project_root*."""
    rows: list[dict[str, object]] = []
    passed = True

    for requirement in _REQUIREMENTS:
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
                "writer": requirement.writer,
                "consumer": requirement.consumer,
                "evidence_path": requirement.evidence_path,
                "passed": requirement_passed,
                "missing_terms": missing_terms,
            }
        )

    return passed, rows


@click.group("state-contract")
def state_contract_group() -> None:
    """Check persisted-state writer/consumer test closure."""


@state_contract_group.command("check")
@click.pass_context
def state_contract_check_cmd(ctx: click.Context) -> None:
    """Check required state-contract evidence exists."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    passed, rows = evaluate_state_contract(project_root)

    if ctx.obj.get("json_output"):
        click.echo(
            json.dumps(
                {
                    "passed": passed,
                    "requirements": rows,
                },
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        click.echo(f"state-contract check: {'passed' if passed else 'failed'}")
        for row in rows:
            state = "pass" if row["passed"] else "FAIL"
            click.echo(f"  {state} {row['name']}: {row['evidence_path']}")
            row_missing_terms = row["missing_terms"]
            if isinstance(row_missing_terms, list) and row_missing_terms:
                click.echo(f"    missing terms: {', '.join(row_missing_terms)}")

    if not passed:
        raise click.exceptions.Exit(code=1)


__all__ = [
    "state_contract_group",
    "state_contract_check_cmd",
    "StateContractRequirement",
    "evaluate_state_contract",
]
