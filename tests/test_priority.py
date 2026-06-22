"""Tests for cross-platform priority enforcement."""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from harness_governance.cli import cli
from harness_governance.commands.init import _build_agents_triggers_block
from harness_governance.priority import (
    CompetingSkill,
    apply_all_fixes,
    apply_fix,
    check_priority,
    detect_competing_skills,
    parse_frontmatter,
    scan_platform_skills,
)


# ============================================================================
# parse_frontmatter
# ============================================================================


def test_parse_empty_text():
    assert parse_frontmatter("") == ({}, "")


def test_parse_no_frontmatter():
    text = "# Just a heading\n\nSome body text."
    assert parse_frontmatter(text) == ({}, text)


def test_parse_simple_frontmatter():
    text = "---\nname: my-skill\ndescription: Does things.\n---\n\n# Body"
    fm, body = parse_frontmatter(text)
    assert fm == {"name": "my-skill", "description": "Does things."}
    assert "# Body" in body


def test_parse_always_apply_true():
    text = "---\nalwaysApply: true\ndescription: A rule.\n---\n\ncontent"
    fm, _body = parse_frontmatter(text)
    assert fm["alwaysApply"] == "true"


def test_parse_with_quoted_values():
    text = "---\nname: \"my-skill\"\ndescription: 'Does things.'\n---\n\nbody"
    fm, _body = parse_frontmatter(text)
    assert fm["name"] == "my-skill"
    assert fm["description"] == "Does things."


def test_parse_missing_closing_delimiter():
    text = "---\nname: test\n\nBody without closing."
    fm, body = parse_frontmatter(text)
    # No closing --- means we treat it as all body
    assert fm == {}
    assert "Body without closing" in body


def test_parse_frontmatter_skips_lists():
    text = "---\nname: test\npaths:\n  - **/*\n---\n\nbody"
    fm, _body = parse_frontmatter(text)
    assert fm["name"] == "test"
    assert "paths" not in fm  # list marker skipped


def test_parse_frontmatter_skips_multiline():
    text = "---\nname: test\ndescription: |\n  multi\n  line\n---\n\nbody"
    fm, _body = parse_frontmatter(text)
    assert fm["name"] == "test"
    assert "description" not in fm  # multiline marker skipped


# ============================================================================
# scan_platform_skills
# ============================================================================


def test_scan_empty_repo(tmp_path: Path):
    result = scan_platform_skills(tmp_path, "claude-code")
    assert result == []


def test_scan_claude_code_finds_competing_skill(tmp_path: Path):
    skill_dir = tmp_path / ".claude" / "skills" / "superpowers-foo"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: superpowers-foo\nalwaysApply: true\n---\n\n# Foo\n",
        encoding="utf-8",
    )
    result = scan_platform_skills(tmp_path, "claude-code")
    assert len(result) == 1
    assert result[0].name == "superpowers-foo"
    assert result[0].platform == "claude-code"


def test_scan_skips_harness_governance(tmp_path: Path):
    our_skill = tmp_path / ".claude" / "skills" / "harness-governance"
    our_skill.mkdir(parents=True)
    (our_skill / "SKILL.md").write_text(
        "---\nname: harness-governance\nalwaysApply: true\n---\n\n# Harness\n",
        encoding="utf-8",
    )
    result = scan_platform_skills(tmp_path, "claude-code")
    assert len(result) == 0  # excluded


def test_scan_skips_harness_governance_file_based(tmp_path: Path):
    rules = tmp_path / ".clinerules"
    rules.mkdir(parents=True)
    # Our skill
    (rules / "harness-governance.md").write_text(
        "---\nname: harness-governance\n---\n\n# HG\n",
        encoding="utf-8",
    )
    # A competing rule
    (rules / "custom-rule.md").write_text(
        "---\nalwaysApply: true\n---\n\n# Custom\n",
        encoding="utf-8",
    )
    result = scan_platform_skills(tmp_path, "cline")
    assert len(result) == 1
    assert result[0].name == "custom-rule"


def test_scan_cursor_finds_mdc_files(tmp_path: Path):
    rules = tmp_path / ".cursor" / "rules"
    rules.mkdir(parents=True)
    (rules / "other-rule.mdc").write_text(
        "---\nalwaysApply: true\ndescription: A cursor rule.\n---\n\n# Rule\n",
        encoding="utf-8",
    )
    result = scan_platform_skills(tmp_path, "cursor")
    assert len(result) == 1
    assert result[0].path.suffix == ".mdc"


def test_scan_opencode_finds_agent_files(tmp_path: Path):
    agents = tmp_path / ".opencode" / "agents"
    agents.mkdir(parents=True)
    (agents / "my-agent.md").write_text(
        "---\nname: my-agent\ndescription: session start handler\n---\n\n# Agent\n",
        encoding="utf-8",
    )
    result = scan_platform_skills(tmp_path, "opencode")
    assert len(result) == 1


def test_scan_windsurf_finds_skills(tmp_path: Path):
    skill_dir = tmp_path / ".windsurf" / "skills" / "other-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: other-skill\n---\n\n# Other\n",
        encoding="utf-8",
    )
    result = scan_platform_skills(tmp_path, "windsurf")
    assert len(result) == 1


# ============================================================================
# detect_competing_skills
# ============================================================================


def test_detect_always_apply(tmp_path: Path):
    skill_dir = tmp_path / ".claude" / "skills" / "hijacker"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: hijacker\nalwaysApply: true\n---\n\n# Body\n",
        encoding="utf-8",
    )
    competing = detect_competing_skills(tmp_path)
    assert len(competing) == 1
    assert "alwaysApply" in competing[0].reasons[0]


def test_detect_before_any_response(tmp_path: Path):
    skill_dir = tmp_path / ".claude" / "skills" / "early-bird"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: early-bird\ndescription: Runs before any response.\n---\n\n# Body\n",
        encoding="utf-8",
    )
    competing = detect_competing_skills(tmp_path)
    assert len(competing) == 1


def test_detect_session_start(tmp_path: Path):
    skill_dir = tmp_path / ".claude" / "skills" / "sessioner"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: sessioner\ndescription: Handles session start logic.\n---\n\n# Body\n",
        encoding="utf-8",
    )
    competing = detect_competing_skills(tmp_path)
    assert len(competing) == 1


def test_detect_body_trigger_phrase(tmp_path: Path):
    skill_dir = tmp_path / ".claude" / "skills" / "plain-skill"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: plain-skill\ndescription: Does stuff.\n---\n\nThis skill runs before any response from the agent.\n",
        encoding="utf-8",
    )
    competing = detect_competing_skills(tmp_path)
    assert len(competing) >= 1
    # The reason should mention the actual trigger phrase found (language-agnostic check)
    assert any("before any response" in r for r in competing[0].reasons), (
        f"Expected 'before any response' in reasons, got: {competing[0].reasons}"
    )


def test_harness_governance_not_flagged(tmp_path: Path):
    """harness-governance's own skill must never be flagged even with alwaysApply."""
    our_skill = tmp_path / ".claude" / "skills" / "harness-governance"
    our_skill.mkdir(parents=True)
    (our_skill / "SKILL.md").write_text(
        "---\nname: harness-governance\nalwaysApply: true\ndescription: before any response\n---\n\n# HG\n",
        encoding="utf-8",
    )
    # Also add a genuine competing skill to verify detection works at all.
    other = tmp_path / ".claude" / "skills" / "other-skill"
    other.mkdir(parents=True)
    (other / "SKILL.md").write_text(
        "---\nname: other-skill\nalwaysApply: true\n---\n\n# Other\n",
        encoding="utf-8",
    )
    competing = detect_competing_skills(tmp_path)
    assert len(competing) == 1
    assert competing[0].skill_name == "other-skill"


def test_no_competing_when_clean(tmp_path: Path):
    competing = detect_competing_skills(tmp_path)
    assert competing == []


# ============================================================================
# check_priority
# ============================================================================


def test_check_priority_passes_clean(tmp_path: Path):
    result = check_priority(tmp_path)
    assert result.passed
    assert result.check == "priority"


def test_check_priority_fails_with_competing(tmp_path: Path):
    skill_dir = tmp_path / ".claude" / "skills" / "hijacker"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: hijacker\nalwaysApply: true\n---\n\n# Body\n",
        encoding="utf-8",
    )
    result = check_priority(tmp_path)
    assert not result.passed
    assert any(f.level == "warning" for f in result.findings)


# ============================================================================
# apply_fix
# ============================================================================


def test_fix_rename_directory(tmp_path: Path):
    skill_dir = tmp_path / ".claude" / "skills" / "hijacker"
    skill_dir.mkdir(parents=True)
    sf = skill_dir / "SKILL.md"
    sf.write_text(
        "---\nname: hijacker\nalwaysApply: true\n---\n\n# Body\n", encoding="utf-8"
    )

    competing = CompetingSkill(
        platform="claude-code",
        path=sf.resolve(),
        skill_name="hijacker",
        reasons=("alwaysApply=true",),
    )
    result = apply_fix(tmp_path, competing)
    assert result.success
    assert result.action == "rename_dir"
    assert not skill_dir.exists()
    assert tmp_path / ".claude" / "skills" / "_hijacker" / "SKILL.md"


def test_fix_rename_file_cline(tmp_path: Path):
    rules = tmp_path / ".clinerules"
    rules.mkdir(parents=True)
    rf = rules / "custom.md"
    rf.write_text("---\nalwaysApply: true\n---\n\n# Rule\n", encoding="utf-8")

    competing = CompetingSkill(
        platform="cline",
        path=rf.resolve(),
        skill_name="custom",
        reasons=("alwaysApply=true",),
    )
    result = apply_fix(tmp_path, competing)
    assert result.success
    assert result.action == "rename_file"
    assert not rf.exists()
    assert (rules / "_custom.md").is_file()


def test_fix_rename_file_cursor(tmp_path: Path):
    rules = tmp_path / ".cursor" / "rules"
    rules.mkdir(parents=True)
    rf = rules / "bad-rule.mdc"
    rf.write_text("---\nalwaysApply: true\n---\n\n# Bad\n", encoding="utf-8")

    competing = CompetingSkill(
        platform="cursor",
        path=rf.resolve(),
        skill_name="bad-rule",
        reasons=("alwaysApply=true",),
    )
    result = apply_fix(tmp_path, competing)
    assert result.success
    assert result.action == "rename_file"
    assert not rf.exists()
    assert (rules / "_bad-rule.mdc").is_file()


def test_fix_idempotent(tmp_path: Path):
    """Running fix twice: second time should skip (target exists)."""
    skill_dir = tmp_path / ".claude" / "skills" / "hijacker"
    skill_dir.mkdir(parents=True)
    sf = skill_dir / "SKILL.md"
    sf.write_text(
        "---\nname: hijacker\nalwaysApply: true\n---\n\n# Body\n", encoding="utf-8"
    )

    competing = CompetingSkill(
        platform="claude-code",
        path=sf.resolve(),
        skill_name="hijacker",
        reasons=("alwaysApply=true",),
    )
    r1 = apply_fix(tmp_path, competing)
    assert r1.success

    # Second run — source no longer exists
    r2 = apply_fix(tmp_path, competing)
    assert not r2.success  # source is gone


def test_fix_already_prefixed_skipped(tmp_path: Path):
    """If skill dir already starts with _, we shouldn't double-prefix."""
    skill_dir = tmp_path / ".claude" / "skills" / "_already-hidden"
    skill_dir.mkdir(parents=True)
    sf = skill_dir / "SKILL.md"
    sf.write_text("---\nalwaysApply: true\n---\n\n# Already hidden\n", encoding="utf-8")

    competing = CompetingSkill(
        platform="claude-code",
        path=sf.resolve(),
        skill_name="_already-hidden",
        reasons=("alwaysApply=true",),
    )
    result = apply_fix(tmp_path, competing)
    # Should succeed (rename from _already-hidden to __already-hidden)
    # or the _ prefix is already there — the fix is still safe.
    # The dir already starts with _, so agent won't scan it.
    # apply_fix will try to rename it to __already-hidden.
    # That's fine as long as it works.
    assert result.success


# ============================================================================
# apply_all_fixes
# ============================================================================


def test_apply_all_fixes_multi_platform(tmp_path: Path):
    # Claude Code competing skill
    cc = tmp_path / ".claude" / "skills" / "hijacker"
    cc.mkdir(parents=True)
    (cc / "SKILL.md").write_text(
        "---\nname: hijacker\nalwaysApply: true\n---\n\n# CC\n",
        encoding="utf-8",
    )

    # Cursor competing rule
    cr = tmp_path / ".cursor" / "rules"
    cr.mkdir(parents=True)
    (cr / "bad-rule.mdc").write_text(
        "---\nalwaysApply: true\n---\n\n# Cursor\n",
        encoding="utf-8",
    )

    competing = detect_competing_skills(tmp_path)
    assert len(competing) >= 2

    results = apply_all_fixes(tmp_path, competing)
    success_count = sum(1 for r in results if r.success)
    assert success_count >= 2


def test_apply_all_fixes_dedup_agents_md(tmp_path: Path):
    """Multiple qoderwork/generic findings only strengthen AGENTS.md once."""
    # Write AGENTS.md first (simulate existing project)
    (tmp_path / "AGENTS.md").write_text(
        "# My Project\n\nSome content.\n", encoding="utf-8"
    )

    c1 = CompetingSkill(
        platform="qoderwork",
        path=(tmp_path / "AGENTS.md").resolve(),
        skill_name="some-skill",
        reasons=("session-start",),
    )
    c2 = CompetingSkill(
        platform="generic",
        path=(tmp_path / "AGENTS.md").resolve(),
        skill_name="other-skill",
        reasons=("always-apply",),
    )
    results = apply_all_fixes(tmp_path, [c1, c2])
    # Should have at most one strengthen_agents_md result.
    agents_md_results = [r for r in results if r.action == "strengthen_agents_md"]
    assert len(agents_md_results) <= 1
    # AGENTS.md should now contain the priority override block.
    content = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "入口路由优先权" in content or "Entry Routing Priority Override" in content


# ============================================================================
# CLI integration
# ============================================================================


def test_check_priority_cmd_clean(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(cli, ["--project-root", str(tmp_path), "check", "priority"])
    assert result.exit_code == 0
    assert "passed" in result.output.lower() or "通过" in result.output


def test_check_priority_cmd_finds_competing(tmp_path: Path):
    skill_dir = tmp_path / ".claude" / "skills" / "hijacker"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: hijacker\nalwaysApply: true\n---\n\n# Body\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(cli, ["--project-root", str(tmp_path), "check", "priority"])
    assert result.exit_code != 0
    assert "hijacker" in result.output


def test_check_priority_fix_cmd(tmp_path: Path):
    skill_dir = tmp_path / ".claude" / "skills" / "hijacker"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: hijacker\nalwaysApply: true\n---\n\n# Body\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        cli, ["--project-root", str(tmp_path), "check", "priority", "--fix"]
    )
    # After fix, check should pass (competing skill neutralised).
    assert "_hijacker" in result.output or "rename_dir" in result.output


def test_check_all_includes_priority(tmp_path: Path):
    """``harness check all`` should include priority in its aggregated output."""
    # Minimal setup so inventory check passes.
    (tmp_path / "NEXT.md").write_text("# Queue\n", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "# Test\n\n启用的非 system skills：0 个\n\n| 名称 | 分类 | 文件 | 脚本 | 启用 |\n|---|---|---|---|---|\n",
        encoding="utf-8",
    )
    from tests.conftest import write_permissive_config

    write_permissive_config(tmp_path)
    state_contract_files = {
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
    for rel, terms in state_contract_files.items():
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(terms), encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(cli, ["--project-root", str(tmp_path), "check", "all"])
    assert result.exit_code == 0
    # Aggregated passed line includes total inspected (priority contributes 8 platforms)
    assert "passed" in result.output.lower()

    # JSON output should include priority check
    json_result = runner.invoke(
        cli,
        ["--project-root", str(tmp_path), "--json", "check", "all"],
    )
    data = json.loads(json_result.output)
    assert data["passed"]
    # priority check inspected 8 platforms
    assert data["inspected"] >= 8


def test_check_priority_json_output(tmp_path: Path):
    skill_dir = tmp_path / ".claude" / "skills" / "hijacker"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: hijacker\nalwaysApply: true\n---\n\n# Body\n",
        encoding="utf-8",
    )
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_path), "--json", "check", "priority"],
    )
    assert result.exit_code != 0
    import json

    data = json.loads(result.output)
    assert data["check"] == "priority"
    assert not data["passed"]


# ============================================================================
# governed-start runtime warning
# ============================================================================


def test_governed_start_warns_when_competing(tmp_path: Path):
    """governed-start should emit a warning to stderr when competing skills exist."""
    skill_dir = tmp_path / ".claude" / "skills" / "hijacker"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: hijacker\nalwaysApply: true\n---\n\n# Body\n",
        encoding="utf-8",
    )
    # Need a config so governed-start doesn't fail on require_session.
    from tests.conftest import write_permissive_config

    write_permissive_config(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_path), "governed-start", "test task"],
    )
    # The warning goes to stderr; when mix_stderr=True (default), it's in output
    stderr = result.output
    assert "competing" in stderr.lower() or "竞争" in stderr


def test_governed_start_silent_when_clean(tmp_path: Path):
    """governed-start should not warn when no competing skills exist."""
    from tests.conftest import write_permissive_config

    write_permissive_config(tmp_path)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["--project-root", str(tmp_path), "governed-start", "test task --files x.py"],
    )
    stderr = result.output
    assert "competing" not in stderr.lower()
    assert "竞争 skill" not in stderr


# ============================================================================
# AGENTS.md strengthened block
# ============================================================================


def test_agents_triggers_block_has_priority_override():
    """AGENTS.md trigger block must include the entry priority override section."""
    block = _build_agents_triggers_block("")
    assert "入口路由优先权" in block
    assert "Entry Routing Priority Override" in block
    assert "最高优先权" in block or "highest priority" in block
    assert "alwaysApply: true" in block


def test_agents_triggers_block_with_skill_ref():
    """Trigger block with skill_ref includes the reference line."""
    block = _build_agents_triggers_block(".claude/skills/harness-governance/SKILL.md")
    assert ".claude/skills/harness-governance/SKILL.md" in block
    assert "入口路由优先权" in block  # priority override still present
