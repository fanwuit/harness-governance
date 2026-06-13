"""``harness check {routing,packets,entry,inventory,all}`` commands.

Each subcommand mirrors a legacy script and produces a structured
:class:`CheckResult`.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import click

from ..commands.entry import check_file as check_entry_file
from ..commands.entry import discover_entry_files
from ..file_ops import packet as packet_ops
from ..models.schemas import CheckFinding, CheckResult
from ..state_machine.engine import (
    StateMachineEngine,
    TransitionContext,
    TransitionVerdict,
)
from ..state_machine.layers import HarnessLayer

_HARNESS_PRECONDITION = "## Harness Precondition"
_CANONICAL_LAYER_TERMS = (
    "Intake / Orientation",
    "Fact Discovery",
    "Implementation Readiness",
)
_OLD_CHAIN = re.compile(
    r"Idea\s*(?:->|\n\s*->\s*\n)\s*Brainstorming\s*(?:->|\n\s*->\s*\n)\s*Brief\s*"
    r"(?:->|\n\s*->\s*\n)\s*Architecture\s*(?:->|\n\s*->\s*\n)\s*ADR\s*"
    r"(?:->|\n\s*->\s*\n)\s*Contract\s*(?:->|\n\s*->\s*\n)\s*Implementation\s*"
    r"(?:->|\n\s*->\s*\n)\s*Verification\s*(?:->|\n\s*->\s*\n)\s*Review / Next",
    re.MULTILINE,
)


def _find_enabled_skills(repo_root: Path) -> list[Path]:
    """Find every ``*/SKILL.md`` excluding system / router skills."""
    skip = {".system", "harness-engineering", "skill-use-transparency"}
    skills: list[Path] = []
    for path in sorted(repo_root.glob("*/SKILL.md")):
        if path.parts[-2] in skip:
            continue
        skills.append(path)
    return skills


def check_routing(repo_root: Path) -> CheckResult:
    """Run the routing-guardrails check (mirrors legacy ``check-routing-guardrails.py``)."""
    findings: list[CheckFinding] = []
    skills = _find_enabled_skills(repo_root)
    for path in skills:
        text = path.read_text(encoding="utf-8")
        if _HARNESS_PRECONDITION not in text:
            findings.append(
                CheckFinding(
                    check="routing",
                    target=str(path.relative_to(repo_root)),
                    level="error",
                    message=f"missing {_HARNESS_PRECONDITION}",
                )
            )
        for term in _CANONICAL_LAYER_TERMS:
            if term not in text:
                findings.append(
                    CheckFinding(
                        check="routing",
                        target=str(path.relative_to(repo_root)),
                        level="warning",
                        message=f"missing canonical layer term: {term}",
                    )
                )
        if _OLD_CHAIN.search(text) and "简化视图" not in text:
            findings.append(
                CheckFinding(
                    check="routing",
                    target=str(path.relative_to(repo_root)),
                    level="warning",
                    message="old layer chain without 简化视图 marker",
                )
            )

    # Layer-progression sanity check via the state machine.
    engine = StateMachineEngine()
    sample = TransitionContext(
        from_layer=HarnessLayer.IDEA,
        to_layer=HarnessLayer.IMPLEMENTATION,
    )
    verdict: TransitionVerdict = engine.evaluate(sample)
    if verdict.allowed:
        findings.append(
            CheckFinding(
                check="routing",
                target="state-machine",
                level="error",
                message="state machine allowed idea → implementation without readiness",
            )
        )

    return CheckResult(
        check="routing",
        passed=not any(f.level == "error" for f in findings),
        findings=tuple(findings),
        inspected=len(skills),
    )


def check_packets(repo_root: Path) -> CheckResult:
    """Run the change-packet structure check."""
    errors, _summaries = packet_ops.check_all_packets(repo_root)
    findings = tuple(
        CheckFinding(check="packets", target="docs/changes/", level="error", message=err)
        for err in errors
    )
    return CheckResult(
        check="packets",
        passed=not findings,
        findings=findings,
        inspected=len(_summaries),
    )


def check_entry(repo_root: Path) -> CheckResult:
    """Run the implementation entry record check."""
    files = discover_entry_files(repo_root)
    all_errors: list[str] = []
    for file in files:
        all_errors.extend(check_entry_file(file, repo_root=repo_root))
    findings = tuple(
        CheckFinding(check="entry", target=str(file), level="error", message=err)
        for file in files
        for err in [e for e in all_errors if str(file) in e]
    )
    return CheckResult(
        check="entry",
        passed=not all_errors,
        findings=findings,
        inspected=len(files),
    )


def check_inventory(repo_root: Path) -> CheckResult:
    """Verify README skill table matches on-disk skills (mirrors legacy)."""
    findings: list[CheckFinding] = []
    readme = repo_root / "README.md"
    if not readme.is_file():
        return CheckResult(
            check="inventory",
            passed=False,
            findings=(
                CheckFinding(
                    check="inventory",
                    target="README.md",
                    level="error",
                    message="README.md not found",
                ),
            ),
        )

    text = readme.read_text(encoding="utf-8")
    enabled = sorted(
        path.parent.name
        for path in _find_enabled_skills(repo_root)
    )

    # Look for the line ``启用的非 system skills：N 个``.
    count_match = re.search(r"启用的非 system skills[：:]\s*(\d+)\s*个", text)
    if count_match:
        declared = int(count_match.group(1))
        if declared != len(enabled):
            findings.append(
                CheckFinding(
                    check="inventory",
                    target="README.md",
                    level="error",
                    message=f"declared count {declared}, on-disk count {len(enabled)}",
                )
            )

    table_skills = _extract_table_skills(text)
    for skill in enabled:
        if skill not in table_skills:
            findings.append(
                CheckFinding(
                    check="inventory",
                    target="README.md",
                    level="warning",
                    message=f"missing enabled skill: {skill}",
                )
            )
    for skill in table_skills:
        if skill not in enabled:
            findings.append(
                CheckFinding(
                    check="inventory",
                    target="README.md",
                    level="warning",
                    message=f"lists missing/disabled skill: {skill}",
                )
            )

    return CheckResult(
        check="inventory",
        passed=not any(f.level == "error" for f in findings),
        findings=tuple(findings),
        inspected=len(enabled),
    )


def _extract_table_skills(readme_text: str) -> list[str]:
    """Extract skill names from the README markdown table."""
    names: list[str] = []
    for line in readme_text.splitlines():
        columns = [c.strip() for c in line.split("|")]
        if len(columns) < 6 or columns[4] != "是":
            continue
        cell = columns[2]
        match = re.match(r"^`([^`]+)`$", cell)
        if match:
            names.append(match.group(1))
    return sorted(names)


@click.group("check")
def check_group() -> None:
    """Run governance checks."""


def _emit(ctx: click.Context, result: CheckResult) -> None:
    if ctx.obj.get("json_output"):
        import json

        payload = result.model_dump()
        payload["findings"] = [f.model_dump() for f in result.findings]
        click.echo(json.dumps(payload, indent=2))
        if not result.passed:
            raise click.exceptions.Exit(code=1)
        return
    if result.passed:
        if result.inspected:
            click.echo(f"{result.check} check passed: {result.inspected} item(s).")
        else:
            click.echo(f"{result.check} check passed.")
        return
    click.echo(f"{result.check} check failed:")
    for finding in result.findings:
        click.echo(f"- [{finding.level}] {finding.target}: {finding.message}")
    raise click.exceptions.Exit(code=1)


@check_group.command("routing")
@click.pass_context
def check_routing_cmd(ctx: click.Context) -> None:
    """Routing guardrail check."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    _emit(ctx, check_routing(project_root))


@check_group.command("packets")
@click.pass_context
def check_packets_cmd(ctx: click.Context) -> None:
    """Change-packet structure check."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    _emit(ctx, check_packets(project_root))


@check_group.command("entry")
@click.pass_context
def check_entry_cmd(ctx: click.Context) -> None:
    """Implementation Entry Record check."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    _emit(ctx, check_entry(project_root))


@check_group.command("inventory")
@click.pass_context
def check_inventory_cmd(ctx: click.Context) -> None:
    """Skill inventory check."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    _emit(ctx, check_inventory(project_root))


@check_group.command("all")
@click.pass_context
def check_all_cmd(ctx: click.Context) -> None:
    """Run every check; aggregate pass/fail."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    results: list[CheckResult] = [
        check_routing(project_root),
        check_packets(project_root),
        check_entry(project_root),
        check_inventory(project_root),
    ]
    aggregate = CheckResult(
        check="all",
        passed=all(r.passed for r in results),
        findings=tuple(f for r in results for f in r.findings),
        inspected=sum(r.inspected for r in results),
    )
    _emit(ctx, aggregate)


__all__ = [
    "check_group",
    "check_routing_cmd",
    "check_packets_cmd",
    "check_entry_cmd",
    "check_inventory_cmd",
    "check_all_cmd",
    "check_routing",
    "check_packets",
    "check_entry",
    "check_inventory",
]