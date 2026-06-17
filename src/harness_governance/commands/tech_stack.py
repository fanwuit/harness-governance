"""``harness tech-stack`` commands — technology stack version management (Gap 4).

Auto-detects languages, lint tools, documentation comment styles, and
persists the manifest to ``.harness/tech-stack.json``.  Integrates with
the INTAKE_ORIENTATION gate to require confirmation of lint and doc-style
choices before implementation begins.
"""

from __future__ import annotations

import click

from ..messages import bilingual
from ..models.schemas import (
    DocStyleGap,
    LintGap,
    TechStackCheckResult,
)
from ..state_machine.tech_stack import (
    DOC_STYLE_CATALOG,
    LINT_TOOL_CATALOG,
    TechStackManager,
)
from ._util import resolve_root


@click.group("tech-stack")
def tech_stack_group() -> None:
    """Technology stack version capture and validation."""


# ---------------------------------------------------------------------------
# tech-stack capture
# ---------------------------------------------------------------------------


@tech_stack_group.command("capture")
@click.pass_context
def tech_stack_capture(ctx: click.Context) -> None:
    """Auto-detect project languages, tools, and save the manifest.

    Scans file extensions, config files, and package manager signatures.
    Writes ``.harness/tech-stack.json``.
    """
    root = resolve_root(ctx)
    mgr = TechStackManager(root)
    manifest = mgr.capture()

    click.echo(bilingual("tech_stack.captured", languages=", ".join(manifest.languages)))
    if manifest.lint_tools:
        click.echo(bilingual("tech_stack.lint_tools_found", count=len(manifest.lint_tools)))
    if manifest.package_managers:
        click.echo(bilingual("tech_stack.pkg_managers", pkgs=", ".join(manifest.package_managers)))
    click.echo(bilingual("tech_stack.saved", path=str(mgr.MANIFEST_PATH)))


# ---------------------------------------------------------------------------
# tech-stack check
# ---------------------------------------------------------------------------


@tech_stack_group.command("check")
@click.pass_context
def tech_stack_check(ctx: click.Context) -> None:
    """Validate current tools against the persisted manifest.

    Detects unregistered tools, lint gaps, and doc-style gaps.
    Returns a non-zero exit code when issues are found.
    """
    root = resolve_root(ctx)
    mgr = TechStackManager(root)
    result: TechStackCheckResult = mgr.check()

    if result.passed:
        click.echo(bilingual("tech_stack.check_passed"))
        return

    for v in result.violations:
        click.echo(f"  ✗ {v}", err=True)

    if result.lint_gaps:
        click.echo(bilingual("tech_stack.lint_gaps_header"), err=True)
        for gap in result.lint_gaps:
            click.echo(
                f"    {gap.language}: {', '.join(gap.suggested_tools)}"
                f"{' (detected: ' + gap.detected_config + ')' if gap.detected_config else ''}",
                err=True,
            )

    if result.doc_style_gaps:
        click.echo(bilingual("tech_stack.doc_gaps_header"), err=True)
        for gap in result.doc_style_gaps:
            click.echo(
                f"    {gap.language}: {', '.join(gap.suggested_styles)}"
                f"{' (detected: ' + gap.detected_style + ')' if gap.detected_style else ''}",
                err=True,
            )

    if result.new_tools_pending_confirmation:
        click.echo(bilingual("tech_stack.pending_tools_header"), err=True)
        for t in result.new_tools_pending_confirmation:
            click.echo(f"    {t.tool_name}@{t.version} (introduced by {t.introduced_by})", err=True)

    raise SystemExit(1)


# ---------------------------------------------------------------------------
# tech-stack add
# ---------------------------------------------------------------------------


@tech_stack_group.command("add")
@click.argument("tool")
@click.option("--version", default="", help="Tool version (e.g. 8.56.0).")
@click.option(
    "--category",
    default="dev_tool",
    type=click.Choice([
        "language", "package_manager", "framework", "dev_tool",
        "lint", "formatter", "doc", "security",
    ]),
    help="Tool category.",
)
@click.option("--reason", default="", help="Why this tool is needed.")
@click.option("--session-id", default="", help="Session introducing this tool.")
@click.pass_context
def tech_stack_add(
    ctx: click.Context,
    tool: str,
    version: str,
    category: str,
    reason: str,
    session_id: str,
) -> None:
    """Register a new tool (unconfirmed) in the manifest.

    The tool must be confirmed later via ``harness tech-stack show``
    before the INTAKE_ORIENTATION gate will pass.
    """
    root = resolve_root(ctx)
    mgr = TechStackManager(root)
    intro = mgr.introduce_tool(
        tool_name=tool,
        version=version,
        rationale=reason,
        session_id=session_id,
        tool_category=category,
    )
    click.echo(
        bilingual(
            "tech_stack.tool_added",
            tool=tool,
            version=version or "unspecified",
        ),
    )
    click.echo(bilingual("tech_stack.tool_pending_confirmation"))


# ---------------------------------------------------------------------------
# tech-stack show
# ---------------------------------------------------------------------------


@tech_stack_group.command("show")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON.")
@click.pass_context
def tech_stack_show(ctx: click.Context, as_json: bool) -> None:
    """Display the current technology stack manifest."""
    root = resolve_root(ctx)
    mgr = TechStackManager(root)
    manifest = mgr.load()

    if manifest is None:
        click.echo(bilingual("tech_stack.no_manifest"), err=True)
        raise SystemExit(1)

    if as_json:
        click.echo(manifest.model_dump_json(indent=2))
        return

    click.echo(bilingual("tech_stack.languages", langs=", ".join(manifest.languages)))
    if manifest.package_managers:
        click.echo(bilingual("tech_stack.pkg_managers", pkgs=", ".join(manifest.package_managers)))
    if manifest.lint_tools:
        click.echo(bilingual("tech_stack.lint_header"))
        for t in manifest.lint_tools:
            ver = t.detected_version or t.declared_version or "?"
            click.echo(f"  {t.tool_name} @ {ver}")
    if manifest.formatters:
        click.echo(bilingual("tech_stack.formatter_header"))
        for t in manifest.formatters:
            ver = t.detected_version or t.declared_version or "?"
            click.echo(f"  {t.tool_name} @ {ver}")
    if manifest.doc_styles:
        click.echo(bilingual("tech_stack.doc_header"))
        for lang, style in manifest.doc_styles.items():
            click.echo(f"  {lang}: {style}")
    if manifest.introduced_tools:
        click.echo(bilingual("tech_stack.introduced_header"))
        for t in manifest.introduced_tools:
            status = "✓" if t.confirmed else "⚠"
            click.echo(f"  {status} {t.tool_name} @ {t.version} [{t.tool_category}]")


# ---------------------------------------------------------------------------
# tech-stack lint
# ---------------------------------------------------------------------------


@tech_stack_group.command("lint")
@click.argument("language", required=False)
@click.option("--tool", default=None, help="Select and confirm a lint tool.")
@click.option("--version", default="", help="Tool version.")
@click.pass_context
def tech_stack_lint(
    ctx: click.Context,
    language: str | None,
    tool: str | None,
    version: str,
) -> None:
    """List or set lint tools per language.

    \b
    Examples:
      harness tech-stack lint              # list all languages
      harness tech-stack lint Python       # show Python lint status
      harness tech-stack lint Python --tool ruff --version 0.11.0
    """
    root = resolve_root(ctx)
    mgr = TechStackManager(root)
    manifest = mgr.load()

    languages = mgr.detect_project_languages()

    if language is None:
        # List mode: show lint status for all detected languages.
        configured = mgr.detect_configured_lints()
        for lang in languages:
            suggestions = mgr.suggest_lint_tools(lang)
            if lang in configured:
                cfg_path, ver = configured[lang]
                ver_str = f" @ {ver}" if ver else ""
                click.echo(f"  {lang}: {cfg_path}{ver_str}")
            else:
                click.echo(
                    f"  {lang}: {bilingual('tech_stack.not_configured')} "
                    f"({bilingual('tech_stack.suggestions')}: {', '.join(suggestions[:3])})"
                )
        if not languages:
            click.echo(bilingual("tech_stack.no_languages_detected"))
        return

    # Single-language mode.
    if language not in languages and language not in LINT_TOOL_CATALOG:
        click.echo(
            bilingual("tech_stack.unknown_language", lang=language),
            err=True,
        )
        raise SystemExit(1)

    if tool is None:
        # Show status for this language.
        configured = mgr.detect_configured_lints()
        if language in configured:
            cfg_path, ver = configured[language]
            ver_str = f" @ {ver}" if ver else ""
            click.echo(f"{language}: {cfg_path}{ver_str}")
        else:
            suggestions = mgr.suggest_lint_tools(language)
            click.echo(
                f"{language}: {bilingual('tech_stack.not_configured')} — "
                f"{bilingual('tech_stack.suggestions')}: {', '.join(suggestions)}"
            )
        return

    # --tool specified: confirm lint tool for this language.
    intro = mgr.introduce_tool(
        tool_name=tool,
        version=version,
        rationale=f"Lint tool for {language}",
        tool_category="lint",
    )
    # Auto-confirm since the user explicitly selected it.
    mgr.confirm_tool(tool)
    click.echo(
        bilingual(
            "tech_stack.lint_confirmed",
            language=language,
            tool=tool,
            version=version or "latest",
        ),
    )


# ---------------------------------------------------------------------------
# tech-stack docstyle
# ---------------------------------------------------------------------------


@tech_stack_group.command("docstyle")
@click.argument("language", required=False)
@click.option("--style", default=None, help="Select and confirm a doc comment style.")
@click.pass_context
def tech_stack_docstyle(
    ctx: click.Context,
    language: str | None,
    style: str | None,
) -> None:
    """List or set documentation comment styles per language.

    \b
    Examples:
      harness tech-stack docstyle                # list all languages
      harness tech-stack docstyle Python          # show Python doc style
      harness tech-stack docstyle Python --style "Google docstring"
    """
    root = resolve_root(ctx)
    mgr = TechStackManager(root)
    manifest = mgr.load()

    languages = mgr.detect_project_languages()

    if language is None:
        # List mode.
        for lang in languages:
            doc_styles = {}
            if manifest is not None:
                doc_styles = manifest.doc_styles
            if lang in doc_styles:
                click.echo(f"  {lang}: {doc_styles[lang]}")
            else:
                suggestions = mgr.suggest_doc_styles(lang)
                detected = mgr.detect_existing_doc_style(lang)
                detected_str = f" [{bilingual('tech_stack.detected')}: {detected}]" if detected else ""
                click.echo(
                    f"  {lang}: {bilingual('tech_stack.not_configured')}"
                    f"{detected_str} — "
                    f"{bilingual('tech_stack.suggestions')}: {', '.join(suggestions[:3])}"
                )
        if not languages:
            click.echo(bilingual("tech_stack.no_languages_detected"))
        return

    # Single-language mode.
    if language not in languages and language not in DOC_STYLE_CATALOG:
        click.echo(
            bilingual("tech_stack.unknown_language", lang=language),
            err=True,
        )
        raise SystemExit(1)

    if style is None:
        # Show status.
        current = None
        if manifest is not None:
            current = manifest.doc_styles.get(language)
        if current:
            click.echo(f"{language}: {current}")
        else:
            suggestions = mgr.suggest_doc_styles(language)
            detected = mgr.detect_existing_doc_style(language)
            detected_str = f" [{bilingual('tech_stack.detected')}: {detected}]" if detected else ""
            click.echo(
                f"{language}: {bilingual('tech_stack.not_configured')}"
                f"{detected_str} — "
                f"{bilingual('tech_stack.suggestions')}: {', '.join(suggestions)}"
            )
        return

    # --style specified: confirm doc style.
    if manifest is None:
        manifest = mgr.capture()

    existing = dict(manifest.doc_styles)
    existing[language] = style
    manifest.doc_styles = existing
    mgr._persist(manifest)
    click.echo(
        bilingual(
            "tech_stack.docstyle_confirmed",
            language=language,
            style=style,
        ),
    )

