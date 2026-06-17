"""``harness entry {check,record}`` commands.

Mirrors the legacy ``governed-implementation-entry/scripts/check-entry-record.mjs``
behavior: accept both ``Implementation Entry Record`` and
``Trivial Safe Change Entry`` blocks; reject placeholder values.
"""

from __future__ import annotations

import re
from pathlib import Path

import click

from ..file_ops import entry as entry_ops
from ..messages import bilingual
from ..models.schemas import CheckResult, EntryRecord
from ..session import find_active_session
from ..state_machine.layers import HarnessLayer

_PLACEHOLDER = re.compile(r"^(?:\s*|tbd|todo|missing|n/a|\?)$", re.IGNORECASE)

# Required fields per entry kind, mirroring the legacy mjs script.
_IMPLEMENTATION_FIELDS: tuple[str, ...] = (
    "Current layer",
    "Target",
    "Scope",
    "Contract evidence",
    "Readiness gate",
    "Packetization",
    "Verification command",
    "Review / Next state file",
    "Stop conditions",
)

_TRIVIAL_FIELDS: tuple[str, ...] = (
    "Target",
    "Scope",
    "Why trivial",
    "Existing contract or reason not needed",
    "Verification",
    "Stop conditions",
)


def _field_value(text: str, field: str) -> str | None:
    # Field names are controlled and may include spaces. Build a literal
    # pattern character-by-character; only escape the regex specials.
    # Use ``[ \t]`` instead of ``\s`` so the regex cannot cross newlines.
    specials = set(".+*?^$(){}[]|\\")
    literal = "".join("\\" + ch if ch in specials else ch for ch in field)
    pattern = re.compile(
        rf"^-[ \t]*{literal}[ \t]*:[ \t]*(.*)$",
        re.IGNORECASE | re.MULTILINE,
    )
    match = pattern.search(text)
    return match.group(1).strip() if match else None


def _has_heading(text: str, heading: str) -> bool:
    return bool(re.search(rf"{re.escape(heading)}\s*:", text, re.IGNORECASE))


def _validate_implementation(text: str) -> list[str]:
    """Implementation-specific validation (mirrors legacy script).

    Returns a list of marker tokens the caller can pass to the i18n
    catalog — keeps message strings centralized in :mod:`messages`.
    """
    errors: list[str] = []
    readiness = _field_value(text, "Readiness gate") or ""
    if readiness and not re.search(r"\b(?:pass|fail)\b", readiness, re.IGNORECASE):
        errors.append("Readiness gate")
    packetization = _field_value(text, "Packetization") or ""
    if packetization and not re.search(
        r"\b(?:ready|not-needed|missing)\b", packetization, re.IGNORECASE
    ):
        errors.append("Packetization")
    return errors


def check_file(file: Path, repo_root: Path | None = None) -> list[str]:
    """Validate one entry-record Markdown file. Returns error messages."""
    label = str(file)
    if repo_root is not None:
        try:
            label = str(file.resolve().relative_to(repo_root.resolve()))
        except ValueError:
            label = str(file)

    if not file.exists():
        return [bilingual("packet.label_does_not_exist", label=label)]
    if not file.is_file():
        return [bilingual("packet.label_not_a_dir", label=label)]
    text = file.read_text(encoding="utf-8")

    impl_match = _has_heading(text, "Implementation Entry Record")
    trivial_match = _has_heading(text, "Trivial Safe Change Entry")

    if not impl_match and not trivial_match:
        return [bilingual("entry.missing_heading", label=label)]

    errors: list[str] = []
    fields = _IMPLEMENTATION_FIELDS if impl_match else _TRIVIAL_FIELDS
    for field in fields:
        value = _field_value(text, field)
        if value is None:
            errors.append(bilingual("entry.missing_field", label=label, field=field))
            continue
        if _PLACEHOLDER.match(value):
            errors.append(bilingual("entry.empty_field", label=label, field=field))

    if impl_match:
        errors.extend(
            bilingual(
                "entry.readiness_format"
                if "Readiness gate" in msg
                else "entry.packetization_format",
                label=label,
            )
            for msg in _validate_implementation(text)
        )

    return errors


def discover_entry_files(
    repo_root: Path, marker: str = "Implementation Entry Record"
) -> list[Path]:
    """Return the default set of entry-record files to check.

    Mirrors the legacy discovery: ``governed-implementation-entry/tests/fixtures/valid-entry-record.md``
    plus any ``docs/remediation/整改记录.md`` files.
    """
    from importlib import resources

    files: list[Path] = []
    try:
        bundled = resources.files("harness_governance.data.fixtures").joinpath(
            "valid-entry-record.md"
        )
        if bundled.is_file():
            with resources.as_file(bundled) as fp:
                files.append(Path(fp))
    except (ModuleNotFoundError, FileNotFoundError):
        pass

    remediation = repo_root / "docs" / "remediation"
    if remediation.is_dir():
        for entry in sorted(remediation.iterdir()):
            if entry.is_file() and entry.name.endswith("整改记录.md"):
                files.append(entry)
    return files


@click.group("entry")
def entry_group() -> None:
    """Manage Implementation Entry Records."""


@entry_group.command("check")
@click.argument("targets", nargs=-1, type=click.Path(exists=False, path_type=Path))
@click.option(
    "--repo",
    "repo_root",
    default=None,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Project root (defaults to --project-root).",
)
@click.pass_context
def entry_check_cmd(
    ctx: click.Context,
    targets: tuple[Path, ...],
    repo_root: Path | None,
) -> None:
    """Validate entry records in the current repo or the given files."""
    root = repo_root or ctx.obj.get("project_root", Path.cwd())
    # Load entry_block_marker from config
    marker = "Implementation Entry Record"
    try:
        from ..config import load_config

        cfg = load_config(root)
        marker = cfg.entry_block_marker
    except Exception:
        pass
    files = list(targets) if targets else discover_entry_files(root, marker=marker)
    all_errors: list[str] = []
    for file in files:
        all_errors.extend(check_file(file, repo_root=root))

    passed = not all_errors
    result = CheckResult(
        check="entry",
        passed=passed,
        inspected=len(files),
    )
    if ctx.obj.get("json_output"):
        import json

        click.echo(
            json.dumps(
                {
                    "check": result.check,
                    "passed": result.passed,
                    "inspected": result.inspected,
                    "errors": all_errors,
                },
                indent=2,
            )
        )
        if not passed:
            raise click.exceptions.Exit(code=1)
        return

    if not files:
        click.echo(bilingual("entry.check_passed_empty"))
        return
    if passed:
        click.echo(bilingual("entry.check_passed_with_count", n=len(files)))
        return
    click.echo(bilingual("entry.check_failed_header"))
    for error in all_errors:
        click.echo(f"- {error}")
    raise click.exceptions.Exit(code=1)


@entry_group.command("record")
@click.option(
    "--target",
    required=True,
    help="Target file/module being changed.",
)
@click.option("--scope", required=True, help="Scope of the change (one sentence).")
@click.option(
    "--layer",
    "layer",
    required=True,
    type=click.Choice([layer.value for layer in HarnessLayer]),
    help="Current harness layer.",
)
@click.option(
    "--contract-evidence",
    default="none",
    help="Path or description of contract evidence.",
)
@click.option(
    "--readiness-gate",
    default="pass",
    show_default=True,
    help="Readiness gate result (must contain pass or fail).",
)
@click.option(
    "--packetization",
    default="not-needed",
    show_default=True,
    help="Packetization state (ready|not-needed|missing).",
)
@click.option(
    "--verification-command",
    required=True,
    help="Command that proves the change works.",
)
@click.option(
    "--review-next-state",
    required=True,
    help="Path to the Review / Next state file.",
)
@click.option("--stop-conditions", required=True, help="Conditions that force a stop.")
@click.option(
    "--output",
    "output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Write the rendered block here (defaults to stdout).",
)
@click.pass_context
def entry_record_cmd(
    ctx: click.Context,
    target: str,
    scope: str,
    layer: str,
    contract_evidence: str,
    readiness_gate: str,
    packetization: str,
    verification_command: str,
    review_next_state: str,
    stop_conditions: str,
    output: Path | None,
) -> None:
    """Render an Implementation Entry Record block.

    By default prints to stdout. With ``--output`` writes to the given file.
    The block can then be pasted into chat, a status file, or a review doc.
    """
    # Session gate: when require_session is enabled, reject if no active session.
    root = ctx.obj.get("project_root", Path.cwd())
    from ..config import load_config

    try:
        cfg = load_config(root)
    except Exception:
        cfg = None
    if cfg and cfg.require_session:
        active = find_active_session(root)
        if active is None:
            raise click.ClickException(bilingual("session.require_session"))

    record = EntryRecord(
        current_layer=HarnessLayer(layer),
        target=target,
        scope=scope,
        contract_evidence=contract_evidence,
        readiness_gate=readiness_gate,
        packetization=packetization,
        verification_command=verification_command,
        review_next_state=review_next_state,
        stop_conditions=stop_conditions,
    )
    rendered = entry_ops.render_entry_record(record) + "\n"
    if output:
        from ..file_ops._util import assert_inside

        try:
            assert_inside(root, output)
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
        output.write_text(rendered, encoding="utf-8")
        click.echo(bilingual("entry.record_written", path=str(output)))
    else:
        click.echo(rendered, nl=False)


__all__ = [
    "entry_group",
    "entry_check_cmd",
    "entry_record_cmd",
    "check_file",
    "discover_entry_files",
]
