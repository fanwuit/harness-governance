"""Tests for ``harness check``."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from harness_governance.cli import cli
from harness_governance.commands.check import (
    _check_self_docs,
    check_inventory,
    check_routing,
    check_state_contract,
    check_subagent_separation,
    check_user_evidence,
)
from harness_governance import __version__ as _current_version


def test_check_routing_flags_missing_precondition(tmp_repo: Path) -> None:
    skill_dir = tmp_repo / "demo-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "# Demo Skill\n\nNo Harness Precondition block here.\n", encoding="utf-8"
    )
    result = check_routing(tmp_repo)
    assert not result.passed
    assert any("Harness Precondition" in f.message for f in result.findings)


def test_check_inventory_passes_when_readme_matches(tmp_repo: Path) -> None:
    skill_dir = tmp_repo / "demo-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: demo-skill\ndescription: x\n---\n\n## Harness Precondition\n\nx.\n",
        encoding="utf-8",
    )
    (tmp_repo / "README.md").write_text(
        "# README\n\n| x | x | `demo-skill` | x | 是 | x |\n",
        encoding="utf-8",
    )
    result = check_inventory(tmp_repo)
    assert result.passed, [f.message for f in result.findings]


def test_check_inventory_flags_missing_readme(tmp_repo: Path) -> None:
    result = check_inventory(tmp_repo)
    assert not result.passed
    assert any("README.md" in f.message for f in result.findings)


def test_check_routing_cli(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--project-root", str(tmp_repo), "check", "routing"])
    # No skills → no precondition errors → passes.
    assert result.exit_code == 0, result.output


def test_check_packets_cli(tmp_repo: Path) -> None:
    from tests.conftest import seed_session

    seed_session(tmp_repo)
    runner = CliRunner()
    runner.invoke(cli, ["--project-root", str(tmp_repo), "packet", "init", "x"])
    result = runner.invoke(cli, ["--project-root", str(tmp_repo), "check", "packets"])
    assert result.exit_code == 1
    assert "packets check failed" in result.output


def test_check_all_cli(tmp_repo: Path) -> None:
    # Provide a README matching on-disk skills so inventory check passes.
    (tmp_repo / "README.md").write_text(
        "# README\n\n| x | x | x | x | 是 | x |\n\n启用的非 system skills：0 个\n",
        encoding="utf-8",
    )
    _write_state_contract_evidence(tmp_repo)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "--json", "check", "all"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["check"] == "all"


def _write_state_contract_evidence(repo_root: Path) -> None:
    files = {
        "tests/test_commands/test_layer_cmd.py": (
            "test_answer_records_qa_for_gate",
            "test_ask_records",
        ),
        "tests/test_commands/test_tech_stack_cmd.py": (
            "test_check_passes_after_cli_lint",
            "manifest.lint_tools",
        ),
        "tests/test_e2e/test_governed_path_smoke.py": (
            "test_strict_governed_path_minimum_smoke",
        ),
        "tests/STATE_CONTRACTS.md": ("State Contract Closure",),
    }
    for rel, terms in files.items():
        path = repo_root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(terms), encoding="utf-8")


def test_check_state_contract_passes_with_required_evidence(tmp_repo: Path) -> None:
    _write_state_contract_evidence(tmp_repo)

    result = check_state_contract(tmp_repo)

    assert result.passed
    assert result.check == "state-contract"
    assert result.inspected == 4


def test_check_state_contract_cli_fails_when_evidence_missing(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "check", "state-contract"],
    )

    assert result.exit_code == 1
    assert "state-contract" in result.output
    assert "failed" in result.output or "检查未通过" in result.output
    assert "tests/test_commands/test_layer_cmd.py" in result.output


def test_check_all_includes_state_contract(tmp_repo: Path) -> None:
    (tmp_repo / "README.md").write_text(
        "# README\n\n| x | x | x | x | 是 | x |\n\n启用的非 system skills：0 个\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "--json", "check", "all"],
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert any(f["check"] == "state-contract" for f in payload["findings"])


def test_check_user_evidence_passes_real_user_acceptance(tmp_repo: Path) -> None:
    evidence_dir = tmp_repo / "docs" / "verification"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "save-loop.md").write_text(
        """# Save loop

MVP complete.

## User-Perceived Integration Evidence
- Evidence level: real-user acceptance
- Real User Entry: Save button in the package editor toolbar
- User-Visible State: Editor shows the saved title after reload
- Persistence/External State: GET /packages/123 returns the same title
- Anti-Self-Proof Assertion: UI value, PUT payload, GET response, and reopened UI match
- Forbidden Test Shortcuts: none
- Command: npm run test:e2e -- save-loop
- Result: passed 2026-06-18
""",
        encoding="utf-8",
    )

    result = check_user_evidence(tmp_repo)

    assert result.passed, [f.message for f in result.findings]
    assert result.inspected == 1


def test_check_user_evidence_fails_missing_required_field(tmp_repo: Path) -> None:
    evidence_dir = tmp_repo / "docs" / "verification"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "save-loop.md").write_text(
        """# Save loop

## User-Perceived Integration Evidence
- Evidence level: real-user acceptance
- Real User Entry: Save button
- User-Visible State:
- Persistence/External State: GET /packages/123
- Anti-Self-Proof Assertion: UI/payload/readback/reopen match
- Forbidden Test Shortcuts: none
- Command: npm run test:e2e
- Result: passed
""",
        encoding="utf-8",
    )

    result = check_user_evidence(tmp_repo)

    assert not result.passed
    assert any("User-Visible State" in f.message for f in result.findings)


def test_check_user_evidence_rejects_closure_claim_without_acceptance(
    tmp_repo: Path,
) -> None:
    evidence_dir = tmp_repo / "docs" / "verification"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "save-loop.md").write_text(
        """# Save loop

closed loop complete.

## User-Perceived Integration Evidence
- Evidence level: contract
- Real User Entry: Save button
- User-Visible State: Editor shows saved title
- Persistence/External State: GET /packages/123
- Anti-Self-Proof Assertion: UI/payload/readback/reopen match
- Forbidden Test Shortcuts: none
- Command: npm run test:contract
- Result: passed
""",
        encoding="utf-8",
    )

    result = check_user_evidence(tmp_repo)

    assert not result.passed
    assert any("real-user acceptance" in f.message for f in result.findings)


def test_check_user_evidence_allows_explicit_not_applicable(tmp_repo: Path) -> None:
    evidence_dir = tmp_repo / "docs" / "verification"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "docs-only.md").write_text(
        """# Docs only

## User-Perceived Integration Not Applicable
- Reason: Documentation-only change with no product path
- Replacement verification: harness check docs
- Residual risk: none
""",
        encoding="utf-8",
    )

    result = check_user_evidence(tmp_repo)

    assert result.passed, [f.message for f in result.findings]


def test_check_user_evidence_requires_change_packet_verification(
    tmp_repo: Path,
) -> None:
    change_dir = tmp_repo / "docs" / "changes" / "save-loop"
    change_dir.mkdir(parents=True)
    (change_dir / "proposal.md").write_text(
        "# Save package\n\nThis adds a user-visible save closed loop.\n",
        encoding="utf-8",
    )

    result = check_user_evidence(tmp_repo)

    assert not result.passed
    assert any("verification.md" in f.target for f in result.findings)


def test_check_subagent_separation_passes_required_with_role_invocations(
    tmp_repo: Path,
) -> None:
    evidence_dir = tmp_repo / "docs" / "verification"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "subagent.md").write_text(
        """# Governed feature

ship ready by verifier.

## Subagent Separation
- Required: yes
- Contract Owner: contract-writer invocation contract-1
- Test/Evidence Owner: fact-finder-reviewer invocation evidence-1
- Implementer: implementer invocation impl-1
- Verifier: reviewer invocation verify-1
- Waiver:
""",
        encoding="utf-8",
    )
    invocation_log = tmp_repo / ".harness" / "invocations.ndjson"
    invocation_log.parent.mkdir()
    invocation_log.write_text(
        "\n".join(
            [
                '{"role":"contract-writer","invocation_id":"contract-1"}',
                '{"role":"fact-finder-reviewer","invocation_id":"evidence-1"}',
                '{"role":"implementer","invocation_id":"impl-1"}',
                '{"role":"reviewer","invocation_id":"verify-1"}',
            ]
        ),
        encoding="utf-8",
    )

    result = check_subagent_separation(tmp_repo)

    assert result.passed, [f.message for f in result.findings]
    assert result.check == "subagent-separation"


def test_check_subagent_separation_requires_section_for_trigger(
    tmp_repo: Path,
) -> None:
    evidence_dir = tmp_repo / "docs" / "verification"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "missing.md").write_text(
        "# P0 work\n\nThis P0 task changes a CLI contract and is ship ready.\n",
        encoding="utf-8",
    )

    result = check_subagent_separation(tmp_repo)

    assert not result.passed
    assert any("Subagent Separation" in f.message for f in result.findings)


def test_check_subagent_separation_requires_role_fields(tmp_repo: Path) -> None:
    evidence_dir = tmp_repo / "docs" / "verification"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "missing-role.md").write_text(
        """# P1 governed work

## Subagent Separation
- Required: yes
- Contract Owner: contract-writer invocation contract-1
- Test/Evidence Owner: fact-finder-reviewer invocation evidence-1
- Implementer:
- Verifier: reviewer invocation verify-1
- Waiver:
""",
        encoding="utf-8",
    )

    result = check_subagent_separation(tmp_repo)

    assert not result.passed
    assert any("Implementer" in f.message for f in result.findings)


def test_check_subagent_separation_requires_invocation_evidence(
    tmp_repo: Path,
) -> None:
    evidence_dir = tmp_repo / "docs" / "verification"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "no-log.md").write_text(
        """# P0 governed work

## Subagent Separation
- Required: yes
- Contract Owner: contract-writer invocation contract-1
- Test/Evidence Owner: fact-finder-reviewer invocation evidence-1
- Implementer: implementer invocation impl-1
- Verifier: reviewer invocation verify-1
- Waiver:
""",
        encoding="utf-8",
    )

    result = check_subagent_separation(tmp_repo)

    assert not result.passed
    assert any("invocation" in f.message.lower() for f in result.findings)


def test_check_subagent_separation_requires_waiver_details(
    tmp_repo: Path,
) -> None:
    evidence_dir = tmp_repo / "docs" / "verification"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "waiver.md").write_text(
        """# P1 governed work

## Subagent Separation
- Required: no
- Waiver: documentation-only change
- Replacement Verification:
- Residual Risk:
""",
        encoding="utf-8",
    )

    result = check_subagent_separation(tmp_repo)

    assert not result.passed
    assert any("Replacement Verification" in f.message for f in result.findings)
    assert any("Residual Risk" in f.message for f in result.findings)


def test_check_subagent_separation_rejects_ownership_violation(
    tmp_repo: Path,
) -> None:
    evidence_dir = tmp_repo / "docs" / "verification"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "ownership.md").write_text(
        """# P0 governed work

implementer modified contract files.

## Subagent Separation
- Required: no
- Waiver: emergency repair
- Replacement Verification: reviewer inspected docs
- Residual Risk: medium
""",
        encoding="utf-8",
    )

    result = check_subagent_separation(tmp_repo)

    assert not result.passed
    assert any("ownership" in f.message.lower() for f in result.findings)


def test_check_subagent_separation_rejects_same_implementer_verifier(
    tmp_repo: Path,
) -> None:
    evidence_dir = tmp_repo / "docs" / "verification"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "same-role.md").write_text(
        """# P0 governed work

## Subagent Separation
- Required: yes
- Contract Owner: contract-writer invocation contract-1
- Test/Evidence Owner: fact-finder-reviewer invocation evidence-1
- Implementer: implementer invocation same-1
- Verifier: reviewer invocation same-1
- Waiver:
""",
        encoding="utf-8",
    )
    invocation_log = tmp_repo / ".harness" / "invocations.ndjson"
    invocation_log.parent.mkdir()
    invocation_log.write_text(
        "\n".join(
            [
                '{"role":"contract-writer","invocation_id":"contract-1"}',
                '{"role":"fact-finder-reviewer","invocation_id":"evidence-1"}',
                '{"role":"implementer","invocation_id":"same-1"}',
                '{"role":"reviewer","invocation_id":"same-1"}',
            ]
        ),
        encoding="utf-8",
    )

    result = check_subagent_separation(tmp_repo)

    assert not result.passed
    assert any("same invocation" in f.message.lower() for f in result.findings)


def test_check_subagent_separation_cli_and_check_all(tmp_repo: Path) -> None:
    (tmp_repo / "README.md").write_text(
        "# README\n\n| x | x | x | x | 是 | x |\n\n启用的非 system skills：0 个\n",
        encoding="utf-8",
    )
    evidence_dir = tmp_repo / "docs" / "verification"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "bad.md").write_text(
        "# Bad governed work\n\nP0 task is ship ready without separation evidence.\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "check", "subagent-separation"],
    )
    assert result.exit_code == 1
    assert "subagent-separation check failed" in result.output

    all_result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "--json", "check", "all"],
    )
    assert all_result.exit_code == 1
    payload = json.loads(all_result.output)
    assert any(f["check"] == "subagent-separation" for f in payload["findings"])


def test_check_user_evidence_cli(tmp_repo: Path) -> None:
    evidence_dir = tmp_repo / "docs" / "verification"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "bad.md").write_text(
        "# Bad save\n\nsave feature without evidence sections.\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "check", "user-evidence"],
    )

    assert result.exit_code == 1
    assert "user-evidence check failed" in result.output


def test_check_all_includes_user_evidence(tmp_repo: Path) -> None:
    (tmp_repo / "README.md").write_text(
        "# README\n\n| x | x | x | x | 鏄?| x |\n\n鍚敤鐨勯潪 system skills锛? 涓猏n",
        encoding="utf-8",
    )
    evidence_dir = tmp_repo / "docs" / "verification"
    evidence_dir.mkdir(parents=True)
    (evidence_dir / "bad.md").write_text(
        "# Bad save\n\nsave feature without evidence sections.\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "--json", "check", "all"],
    )

    assert result.exit_code == 1
    payload = json.loads(result.output)
    assert any(f["check"] == "user-evidence" for f in payload["findings"])


def test_check_inventory_handles_count_drift(tmp_repo: Path) -> None:
    skill_dir = tmp_repo / "demo-skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: demo-skill\ndescription: x\n---\n\n## Harness Precondition\n\nx.\n",
        encoding="utf-8",
    )
    (tmp_repo / "README.md").write_text(
        "# README\n\n| x | x | `demo-skill` | x | 是 | x |\n\n启用的非 system skills：99 个\n",
        encoding="utf-8",
    )
    result = check_inventory(tmp_repo)
    assert not result.passed
    assert any("count" in f.message for f in result.findings)


# ---------------------------------------------------------------------------
# check docs --self tests
# ---------------------------------------------------------------------------


def test_self_check_catches_changelog_version_mismatch(tmp_repo: Path) -> None:
    """--self flags when CHANGELOG version doesn't match __version__."""
    (tmp_repo / "CHANGELOG.md").write_text(
        "## [0.0.1] - 2020-01-01\n\nOld version.\n",
        encoding="utf-8",
    )
    findings = _check_self_docs(tmp_repo, "0.7.1")
    assert any("CHANGELOG" in f.target for f in findings)


def test_self_check_catches_missing_i18n_key(tmp_repo: Path) -> None:
    """--self flags when bilingual() key is not in messages.py catalog."""
    messages_dir = tmp_repo / "src" / "harness_governance"
    messages_dir.mkdir(parents=True, exist_ok=True)
    (messages_dir / "messages.py").write_text(
        "_MESSAGES = {}\n",
        encoding="utf-8",
    )
    src_file = messages_dir / "fake_cmd.py"
    src_file.write_text(
        'bilingual("missing.key", x=1)\n',
        encoding="utf-8",
    )
    findings = _check_self_docs(tmp_repo, "0.7.1")
    assert any("missing.key" in f.message for f in findings)


def test_self_check_catches_skill_version_mismatch(tmp_repo: Path) -> None:
    """--self flags when skill version sentinel doesn't match package version."""
    skills_dir = tmp_repo / "src" / "harness_governance" / "data" / "skills" / "strict"
    skills_dir.mkdir(parents=True, exist_ok=True)
    (skills_dir / "claude-code.md").write_text(
        "<!-- harness-skill-version: 0.6.0 -->\n\n# Skill\n",
        encoding="utf-8",
    )
    findings = _check_self_docs(tmp_repo, "0.7.1")
    assert any("0.6.0" in f.message and "0.7.1" in f.message for f in findings)


def test_self_check_passes_on_clean_project(tmp_repo: Path) -> None:
    """--self passes when docs are in sync."""
    (tmp_repo / "CHANGELOG.md").write_text(
        f"## [{_current_version}] - 2026-06-16\n\nStuff.\n",
        encoding="utf-8",
    )
    findings = _check_self_docs(tmp_repo, _current_version)
    errors = [f for f in findings if f.level == "error"]
    assert not errors, [f.message for f in errors]


def test_docs_self_cli_flag(tmp_repo: Path) -> None:
    """harness check docs --self exits 0 on clean project."""
    (tmp_repo / "CHANGELOG.md").write_text(
        f"## [{_current_version}] - 2026-06-16\n\nStuff.\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_repo), "check", "docs", "--self"],
    )
    assert result.exit_code == 0, result.output
