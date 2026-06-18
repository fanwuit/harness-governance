"""Tests for ``harness governed-start``."""

from __future__ import annotations

from pathlib import Path

import json

from click.testing import CliRunner

from harness_governance.cli import cli


def test_governed_start_classifies_qa_as_fast() -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli, ["--project-root", ".", "governed-start", "What does this skill do?"]
    )
    assert result.exit_code == 0, result.output
    assert "fast-path" in result.output


def test_governed_start_classifies_rename_as_trivial(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "governed-start",
            "Rename local variable foo to bar in src/a.py",
            "--files",
            "src/a.py",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "trivial-safe-change" in result.output


def test_governed_start_classifies_public_api_as_governed(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "governed-start",
            "Expose new /v2/widgets endpoint",
            "--files",
            "src/api.py",
            "--contracts",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "governed-path" in result.output
    assert "Disclosure" in result.output
    assert "Layer path:" in result.output
    assert "intake-orientation -> idea -> fact-discovery" in result.output
    assert "Next layer: idea" in result.output
    assert "harness layer show" in result.output
    assert "harness gate status" in result.output


def test_governed_start_json_includes_layer_path(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "--json",
            "governed-start",
            "Expose new /v2/widgets endpoint",
            "--files",
            "src/api.py",
            "--contracts",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["path"] == "governed-path"
    assert payload["current_layer"] == "intake-orientation"
    assert payload["next_layer"] == "idea"
    assert payload["layer_path"].startswith("intake-orientation -> idea")
    assert payload["layer_path"].endswith("verification -> review-next")


def test_governed_start_warns_on_stale_skill(tmp_repo: Path, monkeypatch) -> None:
    """When the on-disk skill is older than the installed template,
    governed-start must surface a `skill_version_warning` in both
    text and JSON output so the user (or a wrapping agent) sees the
    staleness at entry time, not after a full Governed run.
    """
    from harness_governance.commands import init as init_mod
    from harness_governance.config.defaults import PLATFORM_SKILL_PATHS

    new_template = (
        "---\nname: harness-governance\ndescription: new\n---\n\n"
        "<!-- harness-skill-version: 9.9.9 -->\nbody"
    )
    monkeypatch.setattr(init_mod, "load_skill_template", lambda p: new_template)

    # Lay down an old (no-sentinel) skill file for codex.
    skill_path = tmp_repo / PLATFORM_SKILL_PATHS["codex"]
    skill_path.parent.mkdir(parents=True, exist_ok=True)
    skill_path.write_text("---\nname: x\n---\nold\n", encoding="utf-8")

    # Need the .agents/ marker so detect_platform finds codex.
    (tmp_repo / ".agents").mkdir(exist_ok=True)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "--json",
            "governed-start",
            "What does this skill do?",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["skill_version_warning"] is not None
    assert "codex" in payload["skill_version_warning"]
    assert "9.9.9" in payload["skill_version_warning"]


def test_governed_start_skips_agents_md(tmp_repo: Path, monkeypatch) -> None:
    """AGENTS.md is a user-maintained project doc, NOT a skill template.

    The fresh skill file for generic/qoderwork lives at AGENTS.md per
    PLATFORM_SKILL_PATHS, but real-world AGENTS.md is full of project
    rules (typically starting with ``# AGENTS.md``) — comparing it to
    a skill template yields a false-positive staleness warning.

    Fix: skip files that do not start with YAML frontmatter.
    """
    from harness_governance.commands import init as init_mod
    from harness_governance.commands.governed_start import _check_skill_freshness

    new_template = (
        "---\nname: harness-governance\ndescription: new\n---\n\n"
        "<!-- harness-skill-version: 9.9.9 -->\nbody"
    )
    monkeypatch.setattr(init_mod, "load_skill_template", lambda p: new_template)

    # User's real-world AGENTS.md: no YAML frontmatter.
    (tmp_repo / "AGENTS.md").write_text(
        "# AGENTS.md\n\n13KB of project rules go here...\n",
        encoding="utf-8",
    )

    assert _check_skill_freshness(tmp_repo) is None, (
        "AGENTS.md without frontmatter was wrongly flagged as stale"
    )


def test_governed_start_includes_companions(tmp_repo: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "--json",
            "governed-start",
            "Add new persistence layer",
            "--files",
            "src/db.py",
            "--external",
            "--companion",
            "superpowers:subagent-driven-development",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["path"] == "governed-path"
    assert "superpowers:subagent-driven-development" in payload["disclosure"]


# ---------------------------------------------------------------------------
# Friction reduction: fast-path and trivial lightweight output
# ---------------------------------------------------------------------------


def test_fast_path_minimal_output() -> None:
    """Fast-path produces a one-liner + recommendation, no disclosure block."""
    runner = CliRunner()
    result = runner.invoke(
        cli, ["--project-root", ".", "governed-start", "What does this skill do?"]
    )
    assert result.exit_code == 0, result.output
    assert "fast-path" in result.output.lower()
    # Should NOT contain the full disclosure block
    assert "Disclosure" not in result.output
    # Should contain the recommendation
    assert "directly" in result.output.lower() or "直接" in result.output


def test_fast_path_verbose_shows_full_disclosure() -> None:
    """--verbose forces full disclosure block even for fast-path."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            ".",
            "--verbose",
            "governed-start",
            "What does this skill do?",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Disclosure" in result.output


def test_trivial_compact_output(tmp_repo: Path) -> None:
    """Trivial path produces compact output without disclosure block."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project-root",
            str(tmp_repo),
            "governed-start",
            "Rename local variable foo to bar in src/a.py",
            "--files",
            "src/a.py",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "trivial-safe-change" in result.output
    # Should NOT contain full disclosure block
    assert "Disclosure" not in result.output
    # Recommendation should mention direct action without requiring queue
    assert "directly" in result.output.lower() or "直接" in result.output


# ---------------------------------------------------------------------------
# Rigor tier (v0.7.0)
# ---------------------------------------------------------------------------


class TestGovernedStartRigor:
    """``governed-start --rigor`` controls governance depth."""

    def test_default_rigor_is_strict_in_json(self, tmp_repo: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root",
                str(tmp_repo),
                "--json",
                "governed-start",
                "add a new feature to user module",
                "--files",
                "src/user.py",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["rigor_tier"] == "strict"

    def test_explicit_rigor_light(self, tmp_repo: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root",
                str(tmp_repo),
                "--json",
                "governed-start",
                "fix a typo in README",
                "--files",
                "README.md",
                "--rigor",
                "light",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["rigor_tier"] == "light"

    def test_explicit_rigor_standard(self, tmp_repo: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root",
                str(tmp_repo),
                "--json",
                "governed-start",
                "add avatar field to user table",
                "--files",
                "src/models.py",
                "--rigor",
                "standard",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["rigor_tier"] == "standard"

    def test_rigor_tier_in_text_output(self, tmp_repo: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root",
                str(tmp_repo),
                "--verbose",
                "governed-start",
                "build a new SaaS platform",
                "--files",
                "src/",
                "--contracts",
            ],
        )
        assert result.exit_code == 0, result.output
        assert "strict" in result.output.lower()

    def test_governed_path_creates_session_with_rigor(self, tmp_repo: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root",
                str(tmp_repo),
                "--json",
                "governed-start",
                "implement payment billing system",
                "--files",
                "src/billing.py",
                "--external",
                "--rigor",
                "strict",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["path"] == "governed-path"
        sid = payload["session_id"]
        assert sid is not None

        # Verify the session file has rigor_tier.
        session_path = tmp_repo / ".harness" / "sessions" / f"{sid}.json"
        assert session_path.is_file()
        session_data = json.loads(session_path.read_text(encoding="utf-8"))
        assert session_data["rigor_tier"] == "strict"

    def test_auto_detect_strict_from_description(self, tmp_repo: Path) -> None:
        """Description with '平台' keyword auto-detects STRICT."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root",
                str(tmp_repo),
                "--json",
                "governed-start",
                "从零构建一个SaaS平台",
                "--files",
                "src/",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["rigor_tier"] == "strict"


# ---------------------------------------------------------------------------
# Auto-infer flags (prevents agent misroute when flags are omitted)
# ---------------------------------------------------------------------------


class TestAutoInferFlags:
    """When agents omit --contracts/--external, the CLI auto-infers
    them from the description keywords to prevent fast-path misroute.
    """

    def test_saas_platform_no_flags_routes_governed(self, tmp_repo: Path) -> None:
        """Exact bug scenario: 'SaaS 平台' without --files/--external."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root",
                str(tmp_repo),
                "--json",
                "governed-start",
                "SaaS 平台 - 用户与认证系统",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["path"] == "governed-path"

    def test_auth_keyword_infers_contracts(self, tmp_repo: Path) -> None:
        """Description with 'authentication' auto-infers --contracts."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root",
                str(tmp_repo),
                "--json",
                "governed-start",
                "Add authentication to the API",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["path"] == "governed-path"

    def test_database_keyword_infers_external(self, tmp_repo: Path) -> None:
        """Description with 'database' auto-infers --external."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root",
                str(tmp_repo),
                "--json",
                "governed-start",
                "Add database migration for user table",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["path"] == "governed-path"

    def test_pure_qa_still_fast_path(self) -> None:
        """Pure Q&A without trigger keywords still gets fast-path."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root",
                ".",
                "--json",
                "governed-start",
                "What does the harness-engineering skill do?",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["path"] == "fast-path"

    def test_readonly_file_mention_no_flags_stays_fast_path(self) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root",
                ".",
                "--json",
                "governed-start",
                "解释 upgrade.md 是什么",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["path"] == "fast-path"

    def test_low_risk_markdown_update_no_flags_routes_trivial(
        self, tmp_repo: Path
    ) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root",
                str(tmp_repo),
                "--json",
                "governed-start",
                "同步 upgrade.md 状态",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["path"] == "trivial-safe-change"
        assert payload["session_id"] is None

    def test_cli_and_tests_work_no_flags_routes_governed(self, tmp_repo: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root",
                str(tmp_repo),
                "--json",
                "governed-start",
                "修改 governed-start 输出 12 层路径并加测试",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["path"] == "governed-path"
        assert payload["next_layer"] == "idea"

    def test_english_complete_improvements_no_flags_routes_governed(
        self, tmp_repo: Path
    ) -> None:
        """Execution verbs should route governed even when flags are omitted."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root",
                str(tmp_repo),
                "--json",
                "governed-start",
                "complete improvements 1-4",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["path"] == "governed-path"
        assert payload["layer_path"].startswith("intake-orientation -> idea")

    def test_explicit_no_contracts_overrides_infer(self, tmp_repo: Path) -> None:
        """--no-contracts explicitly overrides auto-inference."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project-root",
                str(tmp_repo),
                "--json",
                "governed-start",
                "Add authentication to the API",
                "--no-contracts",
            ],
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        # --no-contracts forces contracts=False, but STRICT keyword gate
        # in classification.py still forces governed-path for "authentication"
        # So this should still be governed (safety net kicks in).
        assert payload["path"] == "governed-path"

    def test_infer_flags_unit(self) -> None:
        """Unit test for _infer_flags function."""
        from harness_governance.commands.governed_start import _infer_flags

        # SaaS + platform → both True
        c, e = _infer_flags("SaaS 平台 - 用户与认证系统")
        assert c is True
        assert e is True

        # API → external=True (api is in _EXTERNAL_IMPLYING_KEYWORDS)
        c, e = _infer_flags("Expose new API endpoint")
        assert e is True

        # Database → external=True
        c, e = _infer_flags("Add database migration")
        assert e is True

        # Pure Q&A → both False
        c, e = _infer_flags("What does this skill do?")
        assert c is False
        assert e is False
