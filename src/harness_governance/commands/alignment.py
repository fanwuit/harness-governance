"""``harness alignment`` commands — field alignment between contract and code (Gap 2).

Extracts field specifications from contract documents and compares them
against implementation source code.  v0.8.0 supports Python only for
implementation scanning.
"""

from __future__ import annotations

import click

from ..messages import bilingual
from ..state_machine.alignment import FieldAlignmentEngine
from ._util import resolve_root


@click.group("alignment")
def alignment_group() -> None:
    """Field alignment between contract and implementation."""


# ---------------------------------------------------------------------------
# alignment check
# ---------------------------------------------------------------------------


@alignment_group.command("check")
@click.option(
    "--contract",
    "contract_file",
    default=None,
    type=click.Path(exists=True),
    help="Specific contract file to check (all contracts if omitted).",
)
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.pass_context
def alignment_check(
    ctx: click.Context,
    contract_file: str | None,
    as_json: bool,
) -> None:
    """Compare contract field specs against implementation.

    Scans all contracts in ``docs/contracts/`` and all Python source
    files in ``src/``.  Reports missing, renamed, and type-mismatched
    fields.
    """
    root = resolve_root(ctx)
    engine = FieldAlignmentEngine(root)
    report = engine.compute_alignment()

    if as_json:
        click.echo(report.model_dump_json(indent=2))
        if not report.passed:
            raise SystemExit(1)
        return

    click.echo(
        bilingual(
            "alignment.summary",
            expected=report.fields_expected,
            matched=report.fields_matched,
        ),
    )

    if report.unsupported_languages:
        click.echo(
            bilingual(
                "alignment.unsupported",
                langs=", ".join(report.unsupported_languages),
            ),
        )

    if not report.findings:
        click.echo(bilingual("alignment.no_findings"))
        return

    for f in report.findings:
        prefix = "✗" if f.severity == "error" else "⚠"
        click.echo(
            f"  {prefix} [{f.issue}] {f.contract_field or f.implementation_field}"
            f"  ({f.contract_type or '?'} vs {f.implementation_type or '?'})",
        )
        if f.source_file:
            click.echo(f"      {f.source_file}:{f.source_line}")

    if not report.passed:
        click.echo(bilingual("alignment.failed"), err=True)
        raise SystemExit(1)

    click.echo(bilingual("alignment.passed"))


# ---------------------------------------------------------------------------
# alignment trace
# ---------------------------------------------------------------------------


@alignment_group.command("trace")
@click.option("--session-id", default="", help="Governance session ID.")
@click.pass_context
def alignment_trace(ctx: click.Context, session_id: str) -> None:
    """Build a cross-layer field traceability matrix.

    Traces each contract field through architecture, ADR,
    implementation, and verification layers.
    """
    root = resolve_root(ctx)
    engine = FieldAlignmentEngine(root)
    matrix = engine.build_traceability_matrix(session_id)

    click.echo(
        bilingual(
            "alignment.trace_summary",
            total=matrix.fields_total,
            traced=matrix.fields_traced,
        ),
    )

    for entry in matrix.entries:
        click.echo(f"  {entry.field_name}:")
        if entry.contract_ref:
            click.echo(f"    contract: {entry.contract_ref}")
        if entry.architecture_ref:
            click.echo(f"    architecture: {entry.architecture_ref}")
        if entry.adr_ref:
            click.echo(f"    adr: {entry.adr_ref}")
        if entry.implementation_ref:
            click.echo(f"    implementation: {entry.implementation_ref}")
        if entry.verification_ref:
            click.echo(f"    verification: {entry.verification_ref}")
