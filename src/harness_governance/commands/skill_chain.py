"""``harness skill-chain`` commands — skill invocation tracing (Gap 5).

Records parent-child skill call lineage, validates chain integrity,
and visualises the invocation tree (ASCII or Mermaid).
"""

from __future__ import annotations

import click

from ..messages import bilingual
from ..state_machine.skill_chain import SkillChainTracer
from ._util import resolve_root


@click.group("skill-chain")
def skill_chain_group() -> None:
    """Skill invocation chain tracing and audit."""


# ---------------------------------------------------------------------------
# skill-chain trace
# ---------------------------------------------------------------------------


@skill_chain_group.command("trace")
@click.option("--session-id", required=True, help="Governance session ID.")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["ascii", "mermaid"]),
    default="ascii",
    help="Output format (default: ascii).",
)
@click.pass_context
def skill_chain_trace(
    ctx: click.Context,
    session_id: str,
    fmt: str,
) -> None:
    """Display the skill invocation tree for a session."""
    root = resolve_root(ctx)
    tracer = SkillChainTracer(root)

    if fmt == "mermaid":
        click.echo(tracer.to_mermaid(session_id))
    else:
        click.echo(tracer.to_ascii_tree(session_id))

    # Also print a summary.
    report = tracer.compute_report(session_id)
    click.echo()
    click.echo(
        bilingual(
            "skill_chain.summary_line",
            total=report.total_invocations,
            depth=report.max_depth,
            skills=", ".join(report.unique_skills) if report.unique_skills else "none",
        ),
    )


# ---------------------------------------------------------------------------
# skill-chain visualize
# ---------------------------------------------------------------------------


@skill_chain_group.command("visualize")
@click.option("--session-id", required=True, help="Governance session ID.")
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["mermaid", "ascii"]),
    default="mermaid",
    help="Output format (default: mermaid).",
)
@click.pass_context
def skill_chain_visualize(
    ctx: click.Context,
    session_id: str,
    fmt: str,
) -> None:
    """Generate a call-tree diagram (Mermaid or ASCII)."""
    root = resolve_root(ctx)
    tracer = SkillChainTracer(root)

    if fmt == "mermaid":
        click.echo("```mermaid")
        click.echo(tracer.to_mermaid(session_id))
        click.echo("```")
    else:
        click.echo(tracer.to_ascii_tree(session_id))


# ---------------------------------------------------------------------------
# skill-chain inspect
# ---------------------------------------------------------------------------


@skill_chain_group.command("inspect")
@click.option("--session-id", required=True, help="Governance session ID.")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.pass_context
def skill_chain_inspect(
    ctx: click.Context,
    session_id: str,
    as_json: bool,
) -> None:
    """Validate chain integrity and print a detailed report."""
    root = resolve_root(ctx)
    tracer = SkillChainTracer(root)
    report = tracer.compute_report(session_id)
    issues = tracer.validate_chain_integrity(session_id)

    if as_json:
        click.echo(report.model_dump_json(indent=2))
        if issues:
            raise SystemExit(1)
        return

    click.echo(
        bilingual(
            "skill_chain.report_header",
            total=report.total_invocations,
            depth=report.max_depth,
        ),
    )

    if report.unique_skills:
        click.echo(
            bilingual("skill_chain.skills_list", skills=", ".join(report.unique_skills))
        )

    if report.orphan_invocations:
        click.echo(
            bilingual(
                "skill_chain.orphans",
                count=len(report.orphan_invocations),
            ),
            err=True,
        )
        for oid in report.orphan_invocations:
            click.echo(f"    {oid[:16]}...", err=True)

    if report.longest_chain:
        click.echo(
            bilingual(
                "skill_chain.longest_chain",
                length=len(report.longest_chain),
            ),
        )

    if issues:
        click.echo(bilingual("skill_chain.issues_header"), err=True)
        for issue in issues:
            click.echo(f"  ✗ {issue}", err=True)
        raise SystemExit(1)

    click.echo(bilingual("skill_chain.clean"))
