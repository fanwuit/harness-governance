"""``harness check {routing,packets,entry,inventory,all}`` commands.

Each subcommand mirrors a legacy script and produces a structured
:class:`CheckResult`.
"""

from __future__ import annotations

import re
from pathlib import Path

import click

from ..commands.entry import check_file as check_entry_file
from ..commands.entry import discover_entry_files
from ..file_ops import packet as packet_ops
from ..messages import bilingual
from ..models.schemas import CheckFinding, CheckResult
from ..priority import check_priority
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


def _get_check_frequency(repo_root: Path) -> str:
    """Load check_frequency from project config, defaulting to 'targeted'."""
    try:
        from ..config import load_config

        cfg = load_config(repo_root)
        return cfg.check_frequency
    except Exception:
        return "targeted"


def _find_enabled_skills(repo_root: Path) -> list[Path]:
    """Find every ``SKILL.md`` excluding system / router skills.

    The tiered skill layout (since v0.7.0) writes files to paths like
    ``.claude/skills/harness-governance-standard/SKILL.md`` (3 levels deep),
    so we recurse with ``rglob`` rather than the single-level ``*/SKILL.md``
    glob used historically.
    """
    skip = {".system", "harness-engineering", "skill-use-transparency"}
    skills: list[Path] = []
    for path in sorted(repo_root.rglob("SKILL.md")):
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
        rel = str(path.relative_to(repo_root))
        if _HARNESS_PRECONDITION not in text:
            findings.append(
                CheckFinding(
                    check="routing",
                    target=rel,
                    level="error",
                    message=bilingual("check.missing_precondition", path=rel),
                )
            )
        for term in _CANONICAL_LAYER_TERMS:
            if term not in text:
                findings.append(
                    CheckFinding(
                        check="routing",
                        target=rel,
                        level="warning",
                        message=bilingual(
                            "check.missing_layer_term", path=rel, term=term
                        ),
                    )
                )
        if _OLD_CHAIN.search(text) and "简化视图" not in text:
            findings.append(
                CheckFinding(
                    check="routing",
                    target=rel,
                    level="warning",
                    message=bilingual("check.old_chain_without_marker", path=rel),
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
                message=bilingual("check.state_machine_bypass"),
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
        CheckFinding(
            check="packets", target="docs/changes/", level="error", message=err
        )
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
    findings: list[CheckFinding] = []
    for file in files:
        file_errors = check_entry_file(file, repo_root=repo_root)
        all_errors.extend(file_errors)
        for err in file_errors:
            findings.append(
                CheckFinding(
                    check="entry", target=str(file), level="error", message=err
                )
            )
    return CheckResult(
        check="entry",
        passed=not all_errors,
        findings=tuple(findings),
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
                    message=bilingual("check.inventory_no_readme"),
                ),
            ),
        )

    text = readme.read_text(encoding="utf-8")
    enabled = sorted(path.parent.name for path in _find_enabled_skills(repo_root))

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
                    message=bilingual(
                        "check.inventory_count_drift",
                        declared=declared,
                        actual=len(enabled),
                    ),
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
                    message=bilingual("check.inventory_missing_skill", skill=skill),
                )
            )
    for skill in table_skills:
        if skill not in enabled:
            findings.append(
                CheckFinding(
                    check="inventory",
                    target="README.md",
                    level="warning",
                    message=bilingual("check.inventory_extra_skill", skill=skill),
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


def _check_self_docs(repo_root: Path, current_version: str) -> list[CheckFinding]:
    """Harness-governance self-documentation consistency checks.

    Only runs when ``--self`` is passed to ``harness check docs``.
    Checks that CHANGELOG, README, CLAUDE.md, i18n, and skill versions
    are in sync with the codebase.
    """

    findings: list[CheckFinding] = []

    # 1. CHANGELOG version vs __version__  ------------------------------
    changelog = repo_root / "CHANGELOG.md"
    if changelog.is_file():
        text = changelog.read_text(encoding="utf-8")
        # Find the first version header: ## [X.Y.Z]
        m = re.search(r"##\s*\[([0-9]+\.[0-9]+\.[0-9]+)\]", text)
        if m and m.group(1) != current_version:
            findings.append(
                CheckFinding(
                    check="docs-self",
                    target="CHANGELOG.md",
                    level="error",
                    message=(
                        f"CHANGELOG latest version [{m.group(1)}] "
                        f"!= __version__ [{current_version}]"
                    ),
                )
            )

    # 2. README command list vs cli.py registrations  -------------------
    readme = repo_root / "README.md"
    if readme.is_file():
        readme_text = readme.read_text(encoding="utf-8")
        # Parse cli.py for add_command calls
        cli_path = repo_root / "src" / "harness_governance" / "cli.py"
        registered: set[str] = set()
        if cli_path.is_file():
            for line in cli_path.read_text(encoding="utf-8").splitlines():
                m_add = re.match(r"\s*cli\.add_command\((\w+)", line)
                if m_add:
                    registered.add(
                        m_add.group(1).replace("_group", "").replace("_cmd", "")
                    )
        for cmd_name in sorted(registered):
            # Look for the command name in README code blocks
            if cmd_name not in readme_text:
                findings.append(
                    CheckFinding(
                        check="docs-self",
                        target="README.md",
                        level="warning",
                        message=(
                            f"CLI command '{cmd_name}' registered in cli.py "
                            f"but not mentioned in README.md"
                        ),
                    )
                )

    # 3. Architecture section — commands/*.py + state_machine/*.py  -----
    claude_md = repo_root / "CLAUDE.md"
    if claude_md.is_file():
        claude_text = claude_md.read_text(encoding="utf-8")
        for src_dir, label in (
            ("commands", "command"),
            ("state_machine", "state_machine"),
        ):
            src_path = repo_root / "src" / "harness_governance" / src_dir
            if src_path.is_dir():
                for py_file in sorted(src_path.glob("*.py")):
                    if py_file.name.startswith("_"):
                        continue
                    stem = py_file.stem
                    if (
                        stem not in claude_text
                        and stem.replace("_", "") not in claude_text
                    ):
                        findings.append(
                            CheckFinding(
                                check="docs-self",
                                target="CLAUDE.md",
                                level="warning",
                                message=(
                                    f"{label} module '{stem}.py' not mentioned "
                                    f"in CLAUDE.md architecture section"
                                ),
                            )
                        )

    # 4. i18n coverage — bilingual() calls vs messages.py catalog  ------
    messages_path = repo_root / "src" / "harness_governance" / "messages.py"
    if messages_path.is_file():
        msg_text = messages_path.read_text(encoding="utf-8")
        # Collect all message keys from _MESSAGES dict
        msg_keys: set[str] = set()
        for m in re.finditer(r'"([a-z][a-z_.]+\.[a-z_]+)"\s*:', msg_text):
            msg_keys.add(m.group(1))

        # Find bilingual("key", ...) calls in all source .py files
        src_root = repo_root / "src" / "harness_governance"
        for py_file in src_root.rglob("*.py"):
            try:
                py_text = py_file.read_text(encoding="utf-8")
            except OSError:
                continue
            for m in re.finditer(r'bilingual\("([a-z][a-z_.]+\.[a-z_]+)"', py_text):
                key = m.group(1)
                if key not in msg_keys:
                    rel = str(py_file.relative_to(repo_root))
                    findings.append(
                        CheckFinding(
                            check="docs-self",
                            target=rel,
                            level="error",
                            message=(
                                f"bilingual() key {key!r} used in {rel} "
                                f"but missing from messages.py catalog"
                            ),
                        )
                    )

    # 5. Skill version sentinel vs __version__  -------------------------
    skills_root = repo_root / "src" / "harness_governance" / "data" / "skills"
    if skills_root.is_dir():
        major_minor = ".".join(current_version.split(".")[:2])
        for skill_file in sorted(skills_root.glob("*/*")):
            if skill_file.suffix not in (".md", ".mdc"):
                continue
            try:
                content = skill_file.read_text(encoding="utf-8")
            except OSError:
                continue
            sv = re.search(
                r"<!--\s*harness-skill-version:\s*([0-9.]+)\s*-->",
                content,
            )
            if sv:
                skill_ver = sv.group(1)
                if not skill_ver.startswith(major_minor):
                    rel = str(skill_file.relative_to(repo_root))
                    findings.append(
                        CheckFinding(
                            check="docs-self",
                            target=rel,
                            level="error",
                            message=(
                                f"Skill version {skill_ver!r} does not "
                                f"match package version {current_version!r}"
                            ),
                        )
                    )

    # 6. Model docs — schemas.py classes vs CLAUDE.md  ------------------
    schemas_path = repo_root / "src" / "harness_governance" / "models" / "schemas.py"
    if schemas_path.is_file() and claude_md.is_file():
        schema_text = schemas_path.read_text(encoding="utf-8")
        claude_text = claude_md.read_text(encoding="utf-8")
        # Find class definitions that inherit from BaseModel
        for m in re.finditer(
            r"class\s+(\w+)\s*\(\s*(?:BaseModel|HarnessConfig)",
            schema_text,
        ):
            class_name = m.group(1)
            if class_name not in claude_text:
                findings.append(
                    CheckFinding(
                        check="docs-self",
                        target="CLAUDE.md",
                        level="warning",
                        message=(
                            f"Pydantic model '{class_name}' from schemas.py "
                            f"not mentioned in CLAUDE.md"
                        ),
                    )
                )

    # 7. GLOSSARY coverage — key terms from new modules should appear  -----
    glossary = repo_root / "GLOSSARY.md"
    if glossary.is_file():
        glossary_text = glossary.read_text(encoding="utf-8")
        # Terms that MUST appear in GLOSSARY based on v0.7.x additions.
        _required_terms = {
            "rigor.py": ("Rigor Tier", "RigorTier", "rigor tier"),
            "gates.py": ("Layer Gate", "Lock File", "Gate Catalog"),
            "gate.py": ("Gate Check", "gate check"),
            "check docs": ("Document Gardener", "check docs"),
            "subagent dispatch": ("Subagent Dispatch", "context isolation"),
            "gate timing": ("gate timing", "timing"),
        }
        for module, term_choices in _required_terms.items():
            if not any(t.lower() in glossary_text.lower() for t in term_choices):
                findings.append(
                    CheckFinding(
                        check="docs-self",
                        target="GLOSSARY.md",
                        level="warning",
                        message=(
                            f"GLOSSARY.md missing entry for '{module}' "
                            f"(expected one of: {', '.join(term_choices)})"
                        ),
                    )
                )

    # 8. Obsolete skill names in user-facing text  ------------------------
    _obsolete_names: dict[str, str] = {
        "skill-use-transparency": (
            "Obsolete skill name; replace with CLI commands (`harness governed-start`)"
        ),
        "harness-engineering": (
            "Obsolete skill name; replace with CLI commands "
            "(`harness governed-start`, `harness layer advance`)"
        ),
        "superpowers:subagent-driven-development": (
            "External skill reference; should not appear in harness docs"
        ),
    }
    for md_path in sorted(
        list(repo_root.glob("*.md")) + list((repo_root / "src").rglob("*.md"))
    ):
        try:
            text = md_path.read_text(encoding="utf-8")
        except OSError:
            continue
        for old_name, hint in _obsolete_names.items():
            if old_name in text:
                rel = str(md_path.relative_to(repo_root))
                # Skip layer-progression.md — it documents these as internal labels.
                if "layer-progression" in rel or "layers.py" in rel:
                    continue
                findings.append(
                    CheckFinding(
                        check="docs-self",
                        target=rel,
                        level="warning",
                        message=f"References obsolete name '{old_name}': {hint}",
                    )
                )

    # 9. Obsolete flat skill paths  ----------------------------------------
    _obsolete_paths: list[tuple[str, str]] = [
        (
            ".claude/skills/harness-governance/SKILL.md",
            ".claude/skills/harness-governance-{tier}/SKILL.md (4 tiers)",
        ),
        (
            ".codex/skills/harness-governance/SKILL.md",
            ".agents/skills/harness-governance-{tier}/SKILL.md (4 tiers)",
        ),
        (
            ".cursor/rules/harness-governance.mdc",
            ".cursor/rules/harness-governance-{tier}.mdc (4 tiers)",
        ),
    ]
    for md_path in sorted(
        list(repo_root.glob("*.md")) + list((repo_root / "src").rglob("*.md"))
    ):
        try:
            text = md_path.read_text(encoding="utf-8")
        except OSError:
            continue
        for old_path, new_path in _obsolete_paths:
            if old_path in text:
                rel = str(md_path.relative_to(repo_root))
                findings.append(
                    CheckFinding(
                        check="docs-self",
                        target=rel,
                        level="warning",
                        message=(
                            f"References obsolete path '{old_path}'; "
                            f"update to '{new_path}'"
                        ),
                    )
                )

    # 10. Platform count in docs  -------------------------------------------
    _platform_count_re = re.compile(r"(\d)\s*(?:个\s*)?platform|(\d)\s*(?:个\s*)?平台")
    for md_path in sorted(
        list(repo_root.glob("*.md")) + list((repo_root / "src").rglob("*.md"))
    ):
        try:
            text = md_path.read_text(encoding="utf-8")
        except OSError:
            continue
        for m in _platform_count_re.finditer(text):
            count = int(m.group(1) or m.group(2))
            if count < 8 and count > 0:
                rel = str(md_path.relative_to(repo_root))
                findings.append(
                    CheckFinding(
                        check="docs-self",
                        target=rel,
                        level="warning",
                        message=(
                            f"Platform count '{count}' is outdated; "
                            f"currently 8 platforms are supported"
                        ),
                    )
                )

    # 11. Repo URL check  ----------------------------------------------------
    pyproject = repo_root / "pyproject.toml"
    if pyproject.is_file():
        pptext = pyproject.read_text(encoding="utf-8")
        # Extract URL from pyproject.toml
        url_match = re.search(r'["\']?(https://github\.com/[^"\')\s]+)["\']?', pptext)
        if url_match:
            expected_url = url_match.group(1)
            for md_path in sorted(
                list(repo_root.glob("*.md")) + list(repo_root.glob("CONTRIBUTING.md"))
            ):
                try:
                    text = md_path.read_text(encoding="utf-8")
                except OSError:
                    continue
                # Find all github URLs and compare
                for url_m in re.finditer(r"https://github\.com/[^\s)>]+", text):
                    found_url = url_m.group(0).rstrip(".")
                    if (
                        "fanwuit" in found_url
                        and expected_url not in found_url
                        and "my-agent-first-skills" in found_url
                    ):
                        rel = str(md_path.relative_to(repo_root))
                        findings.append(
                            CheckFinding(
                                check="docs-self",
                                target=rel,
                                level="warning",
                                message=(
                                    f"Old repo URL '{found_url}'; "
                                    f"expected '{expected_url}'"
                                ),
                            )
                        )

    return findings


def check_docs(
    repo_root: Path, stale_days: int = 90, self_check: bool = False
) -> CheckResult:
    """Document gardener check: stale ADRs, broken links, version drift.

    Four project-agnostic checks (always):
    1. Stale ADR references — ADR files that reference code files that no longer exist.
    2. Broken cross-references — ``[text](path)`` links pointing nowhere.
    3. Version drift — documents referencing old harness-governance versions.
    4. Empty sections — gate-catalog artifact files with empty or missing key sections.

    When *self_check* is True, six additional checks validate harness-governance's
    own documentation: CHANGELOG version, README command list, CLAUDE.md
    architecture, i18n coverage, skill version sentinels, and model docs.
    """
    from .. import __version__ as current_version

    findings: list[CheckFinding] = []
    inspected = 0

    # 1. Stale ADR references — ADRs that reference non-existent code files.
    adr_dir = repo_root / "docs" / "adr"
    if adr_dir.is_dir():
        for adr_path in sorted(adr_dir.glob("*.md")):
            inspected += 1
            try:
                text = adr_path.read_text(encoding="utf-8")
            except OSError:
                continue
            rel = str(adr_path.relative_to(repo_root))
            # Find file-path references: backtick paths, bare paths, markdown links.
            refs: set[str] = set()
            # backtick-quoted paths: `src/foo.py`
            for m in re.finditer(r"`([^`]+\.[a-zA-Z]{1,6})`", text):
                refs.add(m.group(1))
            # markdown links: [text](path)
            for m in re.finditer(r"\[[^\]]*\]\(([^)]+)\)", text):
                target = m.group(1).split("#")[0].strip()  # strip anchors
                if target and not target.startswith(("http:", "https:", "/")):
                    refs.add(target)
            # Check each referenced file.
            for ref in sorted(refs):
                resolved = (adr_path.parent / ref).resolve()
                if not resolved.is_file():
                    # Try relative to repo root too.
                    resolved2 = (repo_root / ref).resolve()
                    if not resolved2.is_file():
                        findings.append(
                            CheckFinding(
                                check="docs",
                                target=rel,
                                level="error",
                                message=bilingual(
                                    "check.docs_stale_adr",
                                    path=rel,
                                    ref=ref,
                                ),
                            )
                        )

    # 2. Broken cross-references in docs/.
    docs_dir = repo_root / "docs"
    if docs_dir.is_dir():
        for md_path in sorted(docs_dir.glob("**/*.md")):
            inspected += 1
            try:
                text = md_path.read_text(encoding="utf-8")
            except OSError:
                continue
            rel = str(md_path.relative_to(repo_root))
            for m in re.finditer(r"\[[^\]]*\]\(([^)]+)\)", text):
                target = m.group(1).split("#")[0].strip()
                if not target or target.startswith(("http:", "https:", "/")):
                    continue
                # Resolve relative to the containing file's directory.
                resolved = (md_path.parent / target).resolve()
                if not resolved.exists():
                    findings.append(
                        CheckFinding(
                            check="docs",
                            target=rel,
                            level="warning",
                            message=bilingual(
                                "check.docs_broken_link",
                                source=rel,
                                target=target,
                            ),
                        )
                    )

    # 3. Version references — documents mentioning old harness versions.
    _version_ref = re.compile(r"harness(?:-governance)?\s+v?([0-9]+\.[0-9]+\.[0-9]+)")
    # Scan skill files and docs for stale version references.
    for glob_pat in ("*/SKILL.md", "*.md", "docs/**/*.md"):
        for path in sorted(repo_root.glob(glob_pat)):
            try:
                text = path.read_text(encoding="utf-8")
            except OSError:
                continue
            for m in _version_ref.finditer(text):
                ref_ver = m.group(1)
                if ref_ver != current_version:
                    rel = str(path.relative_to(repo_root))
                    findings.append(
                        CheckFinding(
                            check="docs",
                            target=rel,
                            level="warning",
                            message=bilingual(
                                "check.docs_version_mismatch",
                                path=rel,
                                old_version=ref_ver,
                                current_version=current_version,
                            ),
                        )
                    )

    # 4. Empty / missing sections in gate-catalog artifact files.
    _heading_re = re.compile(r"^#{1,4}\s+(.+)$", re.MULTILINE)
    _expected_sections: dict[str, tuple[str, ...]] = {
        "docs/briefs/": ("Goal", "Non-Goals", "Success Criteria"),
        "docs/adr/": ("Decision", "Rationale", "Consequences"),
        "docs/contracts/": ("Behaviour", "Failure Cases", "Scope"),
        "docs/architecture/": ("Boundaries", "Data Flow", "Owners"),
        "docs/verification/": ("Results", "Evidence"),
    }
    for dir_prefix, required in _expected_sections.items():
        for md_path in sorted(repo_root.glob(f"{dir_prefix}*.md")):
            inspected += 1
            try:
                text = md_path.read_text(encoding="utf-8")
            except OSError:
                continue
            rel = str(md_path.relative_to(repo_root))
            headings = {m.group(1).strip() for m in _heading_re.finditer(text)}
            for section in required:
                if section not in headings:
                    findings.append(
                        CheckFinding(
                            check="docs",
                            target=rel,
                            level="info",
                            message=bilingual(
                                "check.docs_empty_section",
                                path=rel,
                                section=section,
                            ),
                        )
                    )

    # 5. Self-documentation consistency (when --self is passed).
    if self_check:
        self_findings = _check_self_docs(repo_root, current_version)
        findings.extend(self_findings)
        inspected += len(self_findings)

    return CheckResult(
        check="docs",
        passed=not any(f.level == "error" for f in findings),
        findings=tuple(findings),
        inspected=inspected,
    )


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
            click.echo(
                bilingual(
                    "check.passed_with_count", check=result.check, n=result.inspected
                )
            )
        else:
            click.echo(bilingual("check.passed", check=result.check))
        return
    click.echo(bilingual("check.failed_header", check=result.check))
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


@check_group.command("docs")
@click.option(
    "--stale-days",
    type=int,
    default=90,
    help="Age threshold in days for stale ADR warnings.",
)
@click.option(
    "--self",
    "self_check",
    is_flag=True,
    default=False,
    help=(
        "Run harness-governance self-documentation consistency checks "
        "(CHANGELOG, README, CLAUDE.md, i18n, skill versions, model docs)."
    ),
)
@click.pass_context
def check_docs_cmd(ctx: click.Context, stale_days: int, self_check: bool) -> None:
    """Document gardener check: stale ADRs, broken links, version drift, empty sections.

    Pass --self to validate harness-governance's own documentation consistency.
    """
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    _emit(ctx, check_docs(project_root, stale_days=stale_days, self_check=self_check))


@check_group.command("priority")
@click.option(
    "--fix",
    "fix_mode",
    is_flag=True,
    default=False,
    help="Apply fixes to neutralise competing skills.",
)
@click.pass_context
def check_priority_cmd(ctx: click.Context, fix_mode: bool) -> None:
    """Check for skills that could hijack entry routing before harness governance."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())

    if fix_mode:
        from ..priority import apply_all_fixes, detect_competing_skills

        competing = detect_competing_skills(project_root)
        if not competing:
            click.echo(bilingual("priority.nothing_to_fix"))
            return
        results = apply_all_fixes(project_root, competing)
        for r in results:
            if r.success:
                click.echo(
                    bilingual(
                        "priority.fix_applied",
                        action=r.action,
                        path=str(r.path),
                        new_path=str(r.new_path or ""),
                    )
                )
                if r.detail:
                    click.echo(f"  {r.detail}")
            else:
                click.echo(
                    bilingual("priority.fix_failed", path=str(r.path), detail=r.detail)
                )
        click.echo("")
        # Re-run check after fix to show current state.
        from ..priority import check_priority as _cp

        result = _cp(project_root)
    else:
        from ..priority import check_priority as _cp

        result = _cp(project_root)
    _emit(ctx, result)


@check_group.command("all")
@click.pass_context
def check_all_cmd(ctx: click.Context) -> None:
    """Run every check; aggregate pass/fail."""
    project_root: Path = ctx.obj.get("project_root", Path.cwd())
    if not ctx.obj.get("json_output"):
        freq = _get_check_frequency(project_root)
        click.echo(bilingual("check.frequency_note", frequency=freq))
    results: list[CheckResult] = [
        check_routing(project_root),
        check_priority(project_root),
        check_packets(project_root),
        check_entry(project_root),
        check_inventory(project_root),
        check_docs(project_root),
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
    "check_docs_cmd",
    "check_priority_cmd",
    "check_all_cmd",
    "check_routing",
    "check_packets",
    "check_entry",
    "check_inventory",
    "check_docs",
    "check_priority",
]
