"""Tests for ``harness tech-stack`` CLI commands.

Covers: capture, check, add, show, show --json, lint, lint with --tool,
docstyle, and docstyle with --style.
"""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner, Result

from harness_governance.cli import cli
from harness_governance.state_machine.tech_stack import TechStackManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _runner() -> CliRunner:
    return CliRunner()


def _seed_python_project(root: Path) -> None:
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "src" / "main.py").write_text("print('hello')\n", encoding="utf-8")
    (root / "src" / "utils.py").write_text("def helper(): pass\n", encoding="utf-8")


def _seed_js_project(root: Path) -> None:
    (root / "index.js").write_text("console.log('hi');\n", encoding="utf-8")


def _invoke(root: Path, *args: str) -> Result:
    runner = _runner()
    return runner.invoke(cli, ["--project-root", str(root), *args])


# ===========================================================================
# tech-stack capture
# ===========================================================================


class TestTechStackCaptureCLI:
    def test_capture_creates_manifest(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        result = _invoke(tmp_path, "tech-stack", "capture")
        assert result.exit_code == 0, result.output
        assert (tmp_path / ".harness" / "tech-stack.json").is_file()

    def test_capture_output_mentions_languages(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        result = _invoke(tmp_path, "tech-stack", "capture")
        assert result.exit_code == 0, result.output
        assert "Python" in result.output

    def test_capture_empty_project(self, tmp_path: Path) -> None:
        result = _invoke(tmp_path, "tech-stack", "capture")
        assert result.exit_code == 0, result.output
        assert (tmp_path / ".harness" / "tech-stack.json").is_file()

    def test_capture_with_lint_config(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            "[tool.ruff]\nline-length = 88\n", encoding="utf-8"
        )
        result = _invoke(tmp_path, "tech-stack", "capture")
        assert result.exit_code == 0, result.output

    def test_capture_detects_package_managers(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        (tmp_path / "requirements.txt").write_text("flask\n", encoding="utf-8")
        result = _invoke(tmp_path, "tech-stack", "capture")
        assert result.exit_code == 0, result.output

    def test_capture_with_js_project(self, tmp_path: Path) -> None:
        _seed_js_project(tmp_path)
        (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")
        result = _invoke(tmp_path, "tech-stack", "capture")
        assert result.exit_code == 0, result.output
        assert "JavaScript" in result.output


# ===========================================================================
# tech-stack check
# ===========================================================================


class TestTechStackCheckCLI:
    def test_check_fails_without_manifest(self, tmp_path: Path) -> None:
        result = _invoke(tmp_path, "tech-stack", "check")
        assert result.exit_code == 1

    def test_check_passes_for_empty_project(self, tmp_path: Path) -> None:
        _invoke(tmp_path, "tech-stack", "capture")
        result = _invoke(tmp_path, "tech-stack", "check")
        assert result.exit_code == 0, result.output

    def test_check_fails_with_lint_gap(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        _invoke(tmp_path, "tech-stack", "capture")
        result = _invoke(tmp_path, "tech-stack", "check")
        # Should fail because Python has no confirmed lint tool
        assert result.exit_code == 1

    def test_check_shows_violations(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        _invoke(tmp_path, "tech-stack", "capture")
        result = _invoke(tmp_path, "tech-stack", "check")
        # Should mention lint or doc-style issues
        combined = result.output
        assert len(combined) > 0

    def test_check_passes_after_lint_and_docstyle_confirmed(
        self, tmp_path: Path
    ) -> None:
        """After capture detects a lint tool + doc style is set, check passes."""
        _seed_python_project(tmp_path)
        # Create lint config BEFORE capture so it lands in manifest.lint_tools
        (tmp_path / "pyproject.toml").write_text(
            "[tool.ruff]\nline-length = 88\n", encoding="utf-8"
        )
        _invoke(tmp_path, "tech-stack", "capture")
        # Set doc style
        _invoke(
            tmp_path, "tech-stack", "docstyle", "Python", "--style", "Google docstring"
        )
        result = _invoke(tmp_path, "tech-stack", "check")
        assert result.exit_code == 0, result.output


# ===========================================================================
# tech-stack add
# ===========================================================================


class TestTechStackAddCLI:
    def test_add_tool(self, tmp_path: Path) -> None:
        _invoke(tmp_path, "tech-stack", "capture")
        result = _invoke(tmp_path, "tech-stack", "add", "mytool", "--version", "1.0")
        assert result.exit_code == 0, result.output

    def test_add_tool_creates_entry(self, tmp_path: Path) -> None:
        _invoke(tmp_path, "tech-stack", "capture")
        _invoke(tmp_path, "tech-stack", "add", "eslint", "--version", "8.56.0")
        mgr = TechStackManager(tmp_path)
        manifest = mgr.load()
        assert manifest is not None
        assert any(t.tool_name == "eslint" for t in manifest.introduced_tools)

    def test_add_tool_without_version(self, tmp_path: Path) -> None:
        _invoke(tmp_path, "tech-stack", "capture")
        result = _invoke(tmp_path, "tech-stack", "add", "mytool")
        assert result.exit_code == 0, result.output

    def test_add_tool_with_category(self, tmp_path: Path) -> None:
        _invoke(tmp_path, "tech-stack", "capture")
        result = _invoke(
            tmp_path,
            "tech-stack",
            "add",
            "ruff",
            "--version",
            "0.11.0",
            "--category",
            "lint",
        )
        assert result.exit_code == 0, result.output

    def test_add_tool_with_reason(self, tmp_path: Path) -> None:
        _invoke(tmp_path, "tech-stack", "capture")
        result = _invoke(
            tmp_path,
            "tech-stack",
            "add",
            "black",
            "--version",
            "24.0",
            "--reason",
            "Code formatter",
        )
        assert result.exit_code == 0, result.output

    def test_add_tool_with_session_id(self, tmp_path: Path) -> None:
        _invoke(tmp_path, "tech-stack", "capture")
        result = _invoke(
            tmp_path,
            "tech-stack",
            "add",
            "mypy",
            "--version",
            "1.9",
            "--session-id",
            "sess-01",
        )
        assert result.exit_code == 0, result.output

    def test_add_tool_without_manifest_creates_one(self, tmp_path: Path) -> None:
        result = _invoke(tmp_path, "tech-stack", "add", "tool-x", "--version", "1.0")
        assert result.exit_code == 0, result.output
        assert (tmp_path / ".harness" / "tech-stack.json").is_file()


# ===========================================================================
# tech-stack show
# ===========================================================================


class TestTechStackShowCLI:
    def test_show_fails_without_manifest(self, tmp_path: Path) -> None:
        result = _invoke(tmp_path, "tech-stack", "show")
        assert result.exit_code == 1

    def test_show_displays_languages(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        _invoke(tmp_path, "tech-stack", "capture")
        result = _invoke(tmp_path, "tech-stack", "show")
        assert result.exit_code == 0, result.output
        assert "Python" in result.output

    def test_show_json_output(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        _invoke(tmp_path, "tech-stack", "capture")
        result = _invoke(tmp_path, "tech-stack", "show", "--json")
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert "languages" in data
        assert "Python" in data["languages"]

    def test_show_json_contains_captured_at(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        _invoke(tmp_path, "tech-stack", "capture")
        result = _invoke(tmp_path, "tech-stack", "show", "--json")
        data = json.loads(result.output)
        assert "captured_at" in data

    def test_show_with_lint_tools(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            "[tool.ruff]\nline-length = 88\n", encoding="utf-8"
        )
        _invoke(tmp_path, "tech-stack", "capture")
        result = _invoke(tmp_path, "tech-stack", "show")
        assert result.exit_code == 0, result.output

    def test_show_with_introduced_tools(self, tmp_path: Path) -> None:
        _invoke(tmp_path, "tech-stack", "capture")
        _invoke(tmp_path, "tech-stack", "add", "eslint", "--version", "8.0")
        result = _invoke(tmp_path, "tech-stack", "show")
        assert result.exit_code == 0, result.output
        assert "eslint" in result.output

    def test_show_with_package_managers(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        (tmp_path / "poetry.lock").write_text("", encoding="utf-8")
        _invoke(tmp_path, "tech-stack", "capture")
        result = _invoke(tmp_path, "tech-stack", "show")
        assert result.exit_code == 0, result.output


# ===========================================================================
# tech-stack lint
# ===========================================================================


class TestTechStackLintCLI:
    def test_lint_list_mode(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        _invoke(tmp_path, "tech-stack", "capture")
        result = _invoke(tmp_path, "tech-stack", "lint")
        assert result.exit_code == 0, result.output

    def test_lint_list_mode_empty_project(self, tmp_path: Path) -> None:
        result = _invoke(tmp_path, "tech-stack", "lint")
        assert result.exit_code == 0, result.output

    def test_lint_show_python_status(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        _invoke(tmp_path, "tech-stack", "capture")
        result = _invoke(tmp_path, "tech-stack", "lint", "Python")
        assert result.exit_code == 0, result.output

    def test_lint_confirm_tool(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        _invoke(tmp_path, "tech-stack", "capture")
        result = _invoke(
            tmp_path,
            "tech-stack",
            "lint",
            "Python",
            "--tool",
            "ruff",
            "--version",
            "0.11.0",
        )
        assert result.exit_code == 0, result.output

    def test_lint_confirm_tool_persists(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        _invoke(tmp_path, "tech-stack", "capture")
        _invoke(
            tmp_path,
            "tech-stack",
            "lint",
            "Python",
            "--tool",
            "ruff",
            "--version",
            "0.11.0",
        )
        mgr = TechStackManager(tmp_path)
        manifest = mgr.load()
        assert manifest is not None
        assert any(
            t.tool_name == "ruff" and t.confirmed for t in manifest.introduced_tools
        )

    def test_lint_unknown_language(self, tmp_path: Path) -> None:
        _invoke(tmp_path, "tech-stack", "capture")
        result = _invoke(tmp_path, "tech-stack", "lint", "COBOL")
        # COBOL is not in LINT_TOOL_CATALOG and not detected → exit 1
        assert result.exit_code == 1


# ===========================================================================
# tech-stack docstyle
# ===========================================================================


class TestTechStackDocstyleCLI:
    def test_docstyle_list_mode(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        _invoke(tmp_path, "tech-stack", "capture")
        result = _invoke(tmp_path, "tech-stack", "docstyle")
        assert result.exit_code == 0, result.output

    def test_docstyle_list_mode_empty_project(self, tmp_path: Path) -> None:
        result = _invoke(tmp_path, "tech-stack", "docstyle")
        assert result.exit_code == 0, result.output

    def test_docstyle_show_python(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        _invoke(tmp_path, "tech-stack", "capture")
        result = _invoke(tmp_path, "tech-stack", "docstyle", "Python")
        assert result.exit_code == 0, result.output

    def test_docstyle_confirm_style(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        _invoke(tmp_path, "tech-stack", "capture")
        result = _invoke(
            tmp_path,
            "tech-stack",
            "docstyle",
            "Python",
            "--style",
            "Google docstring",
        )
        assert result.exit_code == 0, result.output

    def test_docstyle_confirm_persists(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        _invoke(tmp_path, "tech-stack", "capture")
        _invoke(
            tmp_path, "tech-stack", "docstyle", "Python", "--style", "Google docstring"
        )
        mgr = TechStackManager(tmp_path)
        manifest = mgr.load()
        assert manifest is not None
        assert manifest.doc_styles.get("Python") == "Google docstring"

    def test_docstyle_unknown_language(self, tmp_path: Path) -> None:
        _invoke(tmp_path, "tech-stack", "capture")
        result = _invoke(tmp_path, "tech-stack", "docstyle", "COBOL")
        assert result.exit_code == 1

    def test_docstyle_creates_manifest_if_missing(self, tmp_path: Path) -> None:
        """docstyle --style should capture first if no manifest exists."""
        _seed_python_project(tmp_path)
        result = _invoke(
            tmp_path,
            "tech-stack",
            "docstyle",
            "Python",
            "--style",
            "Google docstring",
        )
        assert result.exit_code == 0, result.output
        assert (tmp_path / ".harness" / "tech-stack.json").is_file()


# ===========================================================================
# Integration: full workflow
# ===========================================================================


class TestTechStackFullWorkflow:
    def test_capture_check_fix_check(self, tmp_path: Path) -> None:
        """Full workflow: capture without lint → check (fail) → re-capture with lint + set docstyle → check (pass)."""
        _seed_python_project(tmp_path)

        # Step 1: capture without lint config → gaps
        result = _invoke(tmp_path, "tech-stack", "capture")
        assert result.exit_code == 0

        # Step 2: check should fail (lint + doc gaps)
        result = _invoke(tmp_path, "tech-stack", "check")
        assert result.exit_code == 1

        # Step 3: add lint config file on disk, then re-capture
        (tmp_path / "pyproject.toml").write_text(
            "[tool.ruff]\nline-length = 88\n", encoding="utf-8"
        )
        result = _invoke(tmp_path, "tech-stack", "capture")
        assert result.exit_code == 0

        # Step 4: fix doc style
        result = _invoke(
            tmp_path,
            "tech-stack",
            "docstyle",
            "Python",
            "--style",
            "Google docstring",
        )
        assert result.exit_code == 0

        # Step 5: check should pass now
        result = _invoke(tmp_path, "tech-stack", "check")
        assert result.exit_code == 0, result.output

    def test_add_and_confirm_tool_workflow(self, tmp_path: Path) -> None:
        _invoke(tmp_path, "tech-stack", "capture")
        _invoke(tmp_path, "tech-stack", "add", "custom-tool", "--version", "2.0")

        # Tool should be unconfirmed
        mgr = TechStackManager(tmp_path)
        manifest = mgr.load()
        assert manifest is not None
        tool = [t for t in manifest.introduced_tools if t.tool_name == "custom-tool"][0]
        assert tool.confirmed is False

        # Confirm it
        mgr.confirm_tool("custom-tool")
        manifest = mgr.load()
        tool = [t for t in manifest.introduced_tools if t.tool_name == "custom-tool"][0]
        assert tool.confirmed is True
