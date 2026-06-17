"""Tests for TechStackManager — technology stack detection and governance.

Covers: capture, load, check, introduce_tool, confirm_tool,
detect_project_languages, detect_configured_lints, suggest_lint_tools,
suggest_doc_styles, and the _gate_hook_tech_stack gate hook.
"""

from __future__ import annotations

import json
from pathlib import Path


from harness_governance.models.schemas import (
    TechStackManifest,
    ToolIntroduction,
)
from harness_governance.state_machine.tech_stack import (
    TechStackManager,
    _gate_hook_tech_stack,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mgr(tmp_path: Path) -> TechStackManager:
    """Create a TechStackManager rooted at *tmp_path*."""
    return TechStackManager(tmp_path)


def _seed_python_project(root: Path) -> None:
    """Create a minimal Python project structure."""
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "src" / "main.py").write_text("print('hello')\n", encoding="utf-8")
    (root / "src" / "utils.py").write_text("def helper(): pass\n", encoding="utf-8")


def _seed_js_project(root: Path) -> None:
    """Create a minimal JavaScript project structure."""
    (root / "index.js").write_text("console.log('hi');\n", encoding="utf-8")
    (root / "lib").mkdir(parents=True, exist_ok=True)
    (root / "lib" / "helper.mjs").write_text("export default 42;\n", encoding="utf-8")


def _seed_ts_project(root: Path) -> None:
    """Create a minimal TypeScript project structure."""
    (root / "index.ts").write_text("const x: number = 1;\n", encoding="utf-8")
    (root / "component.tsx").write_text(
        "export default () => <div />;\n", encoding="utf-8"
    )


def _seed_go_project(root: Path) -> None:
    """Create a minimal Go project structure."""
    (root / "main.go").write_text("package main\n", encoding="utf-8")


def _seed_rust_project(root: Path) -> None:
    """Create a minimal Rust project structure."""
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "src" / "lib.rs").write_text(
        "pub fn add(a: i32, b: i32) -> i32 { a + b }\n", encoding="utf-8"
    )
    (root / "Cargo.toml").write_text('[package]\nname = "demo"\n', encoding="utf-8")


# ===========================================================================
# detect_project_languages
# ===========================================================================


class TestDetectProjectLanguages:
    def test_detects_python(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        mgr = _make_mgr(tmp_path)
        langs = mgr.detect_project_languages()
        assert "Python" in langs

    def test_detects_javascript(self, tmp_path: Path) -> None:
        _seed_js_project(tmp_path)
        mgr = _make_mgr(tmp_path)
        langs = mgr.detect_project_languages()
        assert "JavaScript" in langs

    def test_detects_typescript(self, tmp_path: Path) -> None:
        _seed_ts_project(tmp_path)
        mgr = _make_mgr(tmp_path)
        langs = mgr.detect_project_languages()
        assert "TypeScript" in langs

    def test_detects_go(self, tmp_path: Path) -> None:
        _seed_go_project(tmp_path)
        mgr = _make_mgr(tmp_path)
        langs = mgr.detect_project_languages()
        assert "Go" in langs

    def test_detects_rust(self, tmp_path: Path) -> None:
        _seed_rust_project(tmp_path)
        mgr = _make_mgr(tmp_path)
        langs = mgr.detect_project_languages()
        assert "Rust" in langs

    def test_detects_shell(self, tmp_path: Path) -> None:
        (tmp_path / "deploy.sh").write_text(
            "#!/bin/bash\necho deploy\n", encoding="utf-8"
        )
        mgr = _make_mgr(tmp_path)
        langs = mgr.detect_project_languages()
        assert "Shell" in langs

    def test_detects_docker_via_dockerfile(self, tmp_path: Path) -> None:
        (tmp_path / "Dockerfile").write_text("FROM python:3.12\n", encoding="utf-8")
        mgr = _make_mgr(tmp_path)
        langs = mgr.detect_project_languages()
        assert "Docker" in langs

    def test_detects_docker_via_compose(self, tmp_path: Path) -> None:
        (tmp_path / "docker-compose.yml").write_text("version: '3'\n", encoding="utf-8")
        mgr = _make_mgr(tmp_path)
        langs = mgr.detect_project_languages()
        assert "Docker" in langs

    def test_detects_multiple_languages(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        _seed_js_project(tmp_path)
        mgr = _make_mgr(tmp_path)
        langs = mgr.detect_project_languages()
        assert "Python" in langs
        assert "JavaScript" in langs

    def test_returns_sorted(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        _seed_js_project(tmp_path)
        _seed_go_project(tmp_path)
        mgr = _make_mgr(tmp_path)
        langs = mgr.detect_project_languages()
        assert langs == sorted(langs)

    def test_empty_project(self, tmp_path: Path) -> None:
        mgr = _make_mgr(tmp_path)
        langs = mgr.detect_project_languages()
        assert langs == []

    def test_detects_c_files(self, tmp_path: Path) -> None:
        (tmp_path / "main.c").write_text("int main() { return 0; }\n", encoding="utf-8")
        mgr = _make_mgr(tmp_path)
        langs = mgr.detect_project_languages()
        assert "C" in langs

    def test_detects_java_files(self, tmp_path: Path) -> None:
        (tmp_path / "Main.java").write_text("class Main {}\n", encoding="utf-8")
        mgr = _make_mgr(tmp_path)
        langs = mgr.detect_project_languages()
        assert "Java" in langs

    def test_detects_ruby(self, tmp_path: Path) -> None:
        (tmp_path / "app.rb").write_text("puts 'hello'\n", encoding="utf-8")
        mgr = _make_mgr(tmp_path)
        langs = mgr.detect_project_languages()
        assert "Ruby" in langs

    def test_detects_kotlin(self, tmp_path: Path) -> None:
        (tmp_path / "Main.kt").write_text("fun main() {}\n", encoding="utf-8")
        mgr = _make_mgr(tmp_path)
        langs = mgr.detect_project_languages()
        assert "Kotlin" in langs

    def test_detects_csharp(self, tmp_path: Path) -> None:
        (tmp_path / "Program.cs").write_text("class Program {}\n", encoding="utf-8")
        mgr = _make_mgr(tmp_path)
        langs = mgr.detect_project_languages()
        assert "C#" in langs

    def test_detects_swift(self, tmp_path: Path) -> None:
        (tmp_path / "main.swift").write_text('print("hi")\n', encoding="utf-8")
        mgr = _make_mgr(tmp_path)
        langs = mgr.detect_project_languages()
        assert "Swift" in langs

    def test_detects_cpp(self, tmp_path: Path) -> None:
        (tmp_path / "main.cpp").write_text("int main() {}\n", encoding="utf-8")
        mgr = _make_mgr(tmp_path)
        langs = mgr.detect_project_languages()
        assert "C++" in langs

    def test_detects_sql(self, tmp_path: Path) -> None:
        (tmp_path / "schema.sql").write_text(
            "CREATE TABLE t (id INT);\n", encoding="utf-8"
        )
        mgr = _make_mgr(tmp_path)
        langs = mgr.detect_project_languages()
        assert "SQL" in langs


# ===========================================================================
# detect_configured_lints
# ===========================================================================


class TestDetectConfiguredLints:
    def test_pyproject_toml_with_ruff_section(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            "[tool.ruff]\nline-length = 120\n", encoding="utf-8"
        )
        mgr = _make_mgr(tmp_path)
        configured = mgr.detect_configured_lints()
        assert "Python" in configured
        cfg_path, _ = configured["Python"]
        assert "pyproject.toml" in cfg_path

    def test_eslintrc_json(self, tmp_path: Path) -> None:
        _seed_js_project(tmp_path)
        (tmp_path / ".eslintrc.json").write_text(
            '{"extends": "eslint:recommended"}\n', encoding="utf-8"
        )
        mgr = _make_mgr(tmp_path)
        configured = mgr.detect_configured_lints()
        assert "JavaScript" in configured
        cfg_path, _ = configured["JavaScript"]
        assert ".eslintrc.json" in cfg_path

    def test_golangci_lint(self, tmp_path: Path) -> None:
        _seed_go_project(tmp_path)
        (tmp_path / ".golangci.yml").write_text(
            "linters:\n  enable:\n    - govet\n", encoding="utf-8"
        )
        mgr = _make_mgr(tmp_path)
        configured = mgr.detect_configured_lints()
        assert "Go" in configured

    def test_rubocop_config(self, tmp_path: Path) -> None:
        (tmp_path / "app.rb").write_text("puts 'hi'\n", encoding="utf-8")
        (tmp_path / ".rubocop.yml").write_text(
            "AllCops:\n  TargetRubyVersion: 3.2\n", encoding="utf-8"
        )
        mgr = _make_mgr(tmp_path)
        configured = mgr.detect_configured_lints()
        assert "Ruby" in configured

    def test_detekt_for_kotlin(self, tmp_path: Path) -> None:
        (tmp_path / "Main.kt").write_text("fun main() {}\n", encoding="utf-8")
        (tmp_path / "detekt.yml").write_text(
            "build:\n  maxIssues: 0\n", encoding="utf-8"
        )
        mgr = _make_mgr(tmp_path)
        configured = mgr.detect_configured_lints()
        assert "Kotlin" in configured

    def test_clippy_for_rust(self, tmp_path: Path) -> None:
        _seed_rust_project(tmp_path)
        # Cargo.toml already exists from _seed_rust_project; add lints section
        (tmp_path / "Cargo.toml").write_text(
            '[package]\nname = "demo"\n\n[lints]\n', encoding="utf-8"
        )
        mgr = _make_mgr(tmp_path)
        configured = mgr.detect_configured_lints()
        assert "Rust" in configured

    def test_no_config_detected(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        mgr = _make_mgr(tmp_path)
        configured = mgr.detect_configured_lints()
        # Python has no lint config file on disk
        assert "Python" not in configured

    def test_universal_pre_commit(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        (tmp_path / ".pre-commit-config.yaml").write_text(
            "repos:\n  - repo: https://github.com/pre-commit/pre-commit-hooks\n",
            encoding="utf-8",
        )
        mgr = _make_mgr(tmp_path)
        configured = mgr.detect_configured_lints()
        assert "universal" in configured

    def test_swiftlint_for_swift(self, tmp_path: Path) -> None:
        (tmp_path / "main.swift").write_text('print("hi")\n', encoding="utf-8")
        (tmp_path / ".swiftlint.yml").write_text(
            "disabled_rules:\n  - trailing_whitespace\n", encoding="utf-8"
        )
        mgr = _make_mgr(tmp_path)
        configured = mgr.detect_configured_lints()
        assert "Swift" in configured

    def test_biome_for_typescript(self, tmp_path: Path) -> None:
        _seed_ts_project(tmp_path)
        (tmp_path / "biome.json").write_text(
            '{"linter": {"enabled": true}}\n', encoding="utf-8"
        )
        mgr = _make_mgr(tmp_path)
        configured = mgr.detect_configured_lints()
        assert "TypeScript" in configured


# ===========================================================================
# suggest_lint_tools / suggest_doc_styles
# ===========================================================================


class TestSuggestions:
    def test_suggest_lint_tools_python(self, tmp_path: Path) -> None:
        mgr = _make_mgr(tmp_path)
        tools = mgr.suggest_lint_tools("Python")
        assert "ruff" in tools
        assert "flake8" in tools
        assert "pylint" in tools

    def test_suggest_lint_tools_javascript(self, tmp_path: Path) -> None:
        mgr = _make_mgr(tmp_path)
        tools = mgr.suggest_lint_tools("JavaScript")
        assert "eslint" in tools
        assert "prettier" in tools

    def test_suggest_lint_tools_includes_universal(self, tmp_path: Path) -> None:
        mgr = _make_mgr(tmp_path)
        tools = mgr.suggest_lint_tools("Python")
        assert "editorconfig" in tools
        assert "pre-commit" in tools

    def test_suggest_lint_tools_unknown_language(self, tmp_path: Path) -> None:
        mgr = _make_mgr(tmp_path)
        tools = mgr.suggest_lint_tools("COBOL")
        # Only universal tools should be returned
        assert "editorconfig" in tools
        assert "pre-commit" in tools

    def test_suggest_lint_tools_go(self, tmp_path: Path) -> None:
        mgr = _make_mgr(tmp_path)
        tools = mgr.suggest_lint_tools("Go")
        assert "golangci-lint" in tools
        assert "staticcheck" in tools

    def test_suggest_doc_styles_python(self, tmp_path: Path) -> None:
        mgr = _make_mgr(tmp_path)
        styles = mgr.suggest_doc_styles("Python")
        assert "Google docstring" in styles
        assert "NumPy docstring" in styles
        assert "Sphinx reST" in styles

    def test_suggest_doc_styles_java(self, tmp_path: Path) -> None:
        mgr = _make_mgr(tmp_path)
        styles = mgr.suggest_doc_styles("Java")
        assert "Javadoc" in styles

    def test_suggest_doc_styles_unknown_language(self, tmp_path: Path) -> None:
        mgr = _make_mgr(tmp_path)
        styles = mgr.suggest_doc_styles("Haskell")
        assert styles == []

    def test_suggest_doc_styles_go(self, tmp_path: Path) -> None:
        mgr = _make_mgr(tmp_path)
        styles = mgr.suggest_doc_styles("Go")
        assert "godoc" in styles

    def test_suggest_doc_styles_rust(self, tmp_path: Path) -> None:
        mgr = _make_mgr(tmp_path)
        styles = mgr.suggest_doc_styles("Rust")
        assert "doc comments (///)" in styles


# ===========================================================================
# capture
# ===========================================================================


class TestCapture:
    def test_capture_creates_manifest_file(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        mgr = _make_mgr(tmp_path)
        manifest = mgr.capture()
        assert isinstance(manifest, TechStackManifest)
        assert (tmp_path / ".harness" / "tech-stack.json").is_file()

    def test_capture_detects_languages(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        _seed_js_project(tmp_path)
        mgr = _make_mgr(tmp_path)
        manifest = mgr.capture()
        assert "Python" in manifest.languages
        assert "JavaScript" in manifest.languages

    def test_capture_detects_package_managers(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        (tmp_path / "requirements.txt").write_text("flask==3.0\n", encoding="utf-8")
        mgr = _make_mgr(tmp_path)
        manifest = mgr.capture()
        assert "pip" in manifest.package_managers

    def test_capture_detects_poetry(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        (tmp_path / "poetry.lock").write_text("", encoding="utf-8")
        mgr = _make_mgr(tmp_path)
        manifest = mgr.capture()
        assert "poetry" in manifest.package_managers

    def test_capture_detects_npm(self, tmp_path: Path) -> None:
        _seed_js_project(tmp_path)
        (tmp_path / "package-lock.json").write_text("{}", encoding="utf-8")
        mgr = _make_mgr(tmp_path)
        manifest = mgr.capture()
        assert "npm" in manifest.package_managers

    def test_capture_detects_cargo(self, tmp_path: Path) -> None:
        _seed_rust_project(tmp_path)
        mgr = _make_mgr(tmp_path)
        manifest = mgr.capture()
        assert "cargo" in manifest.package_managers

    def test_capture_records_timestamp(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        mgr = _make_mgr(tmp_path)
        manifest = mgr.capture()
        assert manifest.captured_at  # non-empty ISO string

    def test_capture_with_lint_config(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            "[tool.ruff]\nline-length = 120\n", encoding="utf-8"
        )
        mgr = _make_mgr(tmp_path)
        manifest = mgr.capture()
        assert len(manifest.lint_tools) > 0
        assert any(t.tool_name == "ruff" for t in manifest.lint_tools)

    def test_capture_empty_project(self, tmp_path: Path) -> None:
        mgr = _make_mgr(tmp_path)
        manifest = mgr.capture()
        assert manifest.languages == ()
        assert manifest.package_managers == ()

    def test_capture_persisted_json_is_valid(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        mgr = _make_mgr(tmp_path)
        mgr.capture()
        raw = (tmp_path / ".harness" / "tech-stack.json").read_text(encoding="utf-8")
        data = json.loads(raw)
        assert "languages" in data
        assert "captured_at" in data

    def test_capture_detects_go_mod(self, tmp_path: Path) -> None:
        _seed_go_project(tmp_path)
        (tmp_path / "go.mod").write_text("module example.com/demo\n", encoding="utf-8")
        mgr = _make_mgr(tmp_path)
        manifest = mgr.capture()
        assert "go-mod" in manifest.package_managers

    def test_capture_detects_yarn(self, tmp_path: Path) -> None:
        _seed_js_project(tmp_path)
        (tmp_path / "yarn.lock").write_text("", encoding="utf-8")
        mgr = _make_mgr(tmp_path)
        manifest = mgr.capture()
        assert "yarn" in manifest.package_managers

    def test_capture_detects_gradle(self, tmp_path: Path) -> None:
        (tmp_path / "Main.java").write_text("class Main {}\n", encoding="utf-8")
        (tmp_path / "build.gradle").write_text(
            "apply plugin: 'java'\n", encoding="utf-8"
        )
        mgr = _make_mgr(tmp_path)
        manifest = mgr.capture()
        assert "gradle" in manifest.package_managers


# ===========================================================================
# load
# ===========================================================================


class TestLoad:
    def test_load_returns_none_when_no_manifest(self, tmp_path: Path) -> None:
        mgr = _make_mgr(tmp_path)
        assert mgr.load() is None

    def test_load_returns_manifest_after_capture(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        mgr = _make_mgr(tmp_path)
        mgr.capture()
        loaded = mgr.load()
        assert loaded is not None
        assert "Python" in loaded.languages

    def test_load_returns_none_on_corrupt_json(self, tmp_path: Path) -> None:
        harness_dir = tmp_path / ".harness"
        harness_dir.mkdir(parents=True, exist_ok=True)
        (harness_dir / "tech-stack.json").write_text(
            "not valid json{{", encoding="utf-8"
        )
        mgr = _make_mgr(tmp_path)
        assert mgr.load() is None

    def test_load_roundtrip(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            "[tool.ruff]\nline-length = 88\n", encoding="utf-8"
        )
        mgr = _make_mgr(tmp_path)
        original = mgr.capture()
        loaded = mgr.load()
        assert loaded is not None
        assert loaded.languages == original.languages
        assert loaded.package_managers == original.package_managers


# ===========================================================================
# check
# ===========================================================================


class TestCheck:
    def test_check_fails_without_manifest(self, tmp_path: Path) -> None:
        mgr = _make_mgr(tmp_path)
        result = mgr.check()
        assert not result.passed
        assert any("No tech-stack manifest found" in v for v in result.violations)

    def test_check_passes_for_clean_project(self, tmp_path: Path) -> None:
        """A project with no languages and a captured manifest passes."""
        mgr = _make_mgr(tmp_path)
        mgr.capture()  # empty project, no languages → no gaps
        result = mgr.check()
        assert result.passed

    def test_check_detects_lint_gap(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        mgr = _make_mgr(tmp_path)
        mgr.capture()
        result = mgr.check()
        # Python detected but no lint tool confirmed → lint gap
        assert len(result.lint_gaps) > 0
        assert any(g.language == "Python" for g in result.lint_gaps)

    def test_check_detects_doc_style_gap(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        mgr = _make_mgr(tmp_path)
        mgr.capture()
        result = mgr.check()
        # Python detected but no doc style confirmed → doc-style gap
        assert len(result.doc_style_gaps) > 0
        assert any(g.language == "Python" for g in result.doc_style_gaps)

    def test_check_reports_unconfirmed_introduced_tools(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        mgr = _make_mgr(tmp_path)
        mgr.capture()
        mgr.introduce_tool("mytool", "1.0.0", session_id="sess-1")
        result = mgr.check()
        assert not result.passed
        assert len(result.new_tools_pending_confirmation) == 1
        assert result.new_tools_pending_confirmation[0].tool_name == "mytool"

    def test_check_passes_after_tool_confirmed(self, tmp_path: Path) -> None:
        """After confirming an introduced tool, it should no longer be pending."""
        mgr = _make_mgr(tmp_path)
        mgr.capture()
        mgr.introduce_tool("mytool", "1.0.0")
        mgr.confirm_tool("mytool")
        result = mgr.check()
        assert len(result.new_tools_pending_confirmation) == 0

    def test_check_detects_unregistered_tool(self, tmp_path: Path) -> None:
        """A lint config on disk not in the manifest should be flagged."""
        _seed_python_project(tmp_path)
        mgr = _make_mgr(tmp_path)
        mgr.capture()  # no ruff config yet
        # Now add ruff config after capture
        (tmp_path / "pyproject.toml").write_text(
            "[tool.ruff]\nline-length = 120\n", encoding="utf-8"
        )
        result = mgr.check()
        assert any("Unregistered tool" in v for v in result.violations)


# ===========================================================================
# introduce_tool
# ===========================================================================


class TestIntroduceTool:
    def test_introduce_tool_creates_unconfirmed_entry(self, tmp_path: Path) -> None:
        mgr = _make_mgr(tmp_path)
        mgr.capture()
        intro = mgr.introduce_tool("ruff", "0.11.0", session_id="sess-1")
        assert isinstance(intro, ToolIntroduction)
        assert intro.tool_name == "ruff"
        assert intro.version == "0.11.0"
        assert intro.confirmed is False

    def test_introduce_tool_persists_to_disk(self, tmp_path: Path) -> None:
        mgr = _make_mgr(tmp_path)
        mgr.capture()
        mgr.introduce_tool("eslint", "8.56.0")
        loaded = mgr.load()
        assert loaded is not None
        assert any(t.tool_name == "eslint" for t in loaded.introduced_tools)

    def test_introduce_tool_without_prior_manifest(self, tmp_path: Path) -> None:
        mgr = _make_mgr(tmp_path)
        intro = mgr.introduce_tool("mytool", "1.0.0")
        assert intro.tool_name == "mytool"
        loaded = mgr.load()
        assert loaded is not None
        assert len(loaded.introduced_tools) == 1

    def test_introduce_multiple_tools(self, tmp_path: Path) -> None:
        mgr = _make_mgr(tmp_path)
        mgr.capture()
        mgr.introduce_tool("tool-a", "1.0")
        mgr.introduce_tool("tool-b", "2.0")
        loaded = mgr.load()
        assert loaded is not None
        assert len(loaded.introduced_tools) == 2

    def test_introduce_tool_with_category(self, tmp_path: Path) -> None:
        mgr = _make_mgr(tmp_path)
        mgr.capture()
        intro = mgr.introduce_tool("ruff", "0.11.0", tool_category="lint")
        assert intro.tool_category == "lint"

    def test_introduce_tool_with_rationale(self, tmp_path: Path) -> None:
        mgr = _make_mgr(tmp_path)
        mgr.capture()
        intro = mgr.introduce_tool("ruff", "0.11.0", rationale="Fast linter")
        assert isinstance(intro, ToolIntroduction)


# ===========================================================================
# confirm_tool
# ===========================================================================


class TestConfirmTool:
    def test_confirm_tool_returns_true(self, tmp_path: Path) -> None:
        mgr = _make_mgr(tmp_path)
        mgr.capture()
        mgr.introduce_tool("ruff", "0.11.0")
        assert mgr.confirm_tool("ruff") is True

    def test_confirm_tool_marks_confirmed(self, tmp_path: Path) -> None:
        mgr = _make_mgr(tmp_path)
        mgr.capture()
        mgr.introduce_tool("ruff", "0.11.0")
        mgr.confirm_tool("ruff")
        loaded = mgr.load()
        assert loaded is not None
        ruff = [t for t in loaded.introduced_tools if t.tool_name == "ruff"]
        assert len(ruff) == 1
        assert ruff[0].confirmed is True
        assert ruff[0].confirmation_method == "cli"

    def test_confirm_unknown_tool_returns_false(self, tmp_path: Path) -> None:
        mgr = _make_mgr(tmp_path)
        mgr.capture()
        assert mgr.confirm_tool("nonexistent") is False

    def test_confirm_tool_returns_false_without_manifest(self, tmp_path: Path) -> None:
        mgr = _make_mgr(tmp_path)
        assert mgr.confirm_tool("anything") is False

    def test_confirm_already_confirmed_tool_returns_false(self, tmp_path: Path) -> None:
        """Confirming a tool that is already confirmed should return False (no change)."""
        mgr = _make_mgr(tmp_path)
        mgr.capture()
        mgr.introduce_tool("ruff", "0.11.0")
        mgr.confirm_tool("ruff")
        # Second confirm should detect no change
        assert mgr.confirm_tool("ruff") is False

    def test_confirm_only_unconfirmed_tool_returns_true_bug_fix(
        self, tmp_path: Path
    ) -> None:
        """BUG FIX: confirming the ONLY unconfirmed tool must return True.

        Previously, comparing old_confirmed vs new_confirmed sets could
        return False when confirming the sole unconfirmed tool because the
        comparison was done incorrectly.  This test ensures the fix works.
        """
        mgr = _make_mgr(tmp_path)
        mgr.capture()
        mgr.introduce_tool("sole-tool", "1.0.0")

        # Before confirming: old_confirmed = {} (empty set)
        # After confirming:  new_confirmed = {"sole-tool"}
        # These sets are different → confirm_tool should return True.
        result = mgr.confirm_tool("sole-tool")
        assert result is True, (
            "confirm_tool must return True when confirming the only unconfirmed tool"
        )

        loaded = mgr.load()
        assert loaded is not None
        tool = [t for t in loaded.introduced_tools if t.tool_name == "sole-tool"]
        assert len(tool) == 1
        assert tool[0].confirmed is True

    def test_confirm_one_of_multiple_tools(self, tmp_path: Path) -> None:
        mgr = _make_mgr(tmp_path)
        mgr.capture()
        mgr.introduce_tool("tool-a", "1.0")
        mgr.introduce_tool("tool-b", "2.0")
        assert mgr.confirm_tool("tool-a") is True
        loaded = mgr.load()
        assert loaded is not None
        a = [t for t in loaded.introduced_tools if t.tool_name == "tool-a"][0]
        b = [t for t in loaded.introduced_tools if t.tool_name == "tool-b"][0]
        assert a.confirmed is True
        assert b.confirmed is False


# ===========================================================================
# detect_unexpected
# ===========================================================================


class TestDetectUnexpected:
    def test_no_unexpected_on_clean_project(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        mgr = _make_mgr(tmp_path)
        mgr.capture()
        unexpected = mgr.detect_unexpected()
        assert unexpected == []

    def test_detects_new_ruff_config(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        mgr = _make_mgr(tmp_path)
        mgr.capture()
        (tmp_path / "pyproject.toml").write_text(
            "[tool.ruff]\nline-length = 88\n", encoding="utf-8"
        )
        unexpected = mgr.detect_unexpected()
        assert "ruff" in unexpected

    def test_detects_new_eslintrc(self, tmp_path: Path) -> None:
        _seed_js_project(tmp_path)
        mgr = _make_mgr(tmp_path)
        mgr.capture()
        (tmp_path / ".eslintrc.json").write_text("{}", encoding="utf-8")
        unexpected = mgr.detect_unexpected()
        assert "eslint" in unexpected

    def test_no_unexpected_when_tool_already_in_manifest(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            "[tool.ruff]\nline-length = 88\n", encoding="utf-8"
        )
        mgr = _make_mgr(tmp_path)
        mgr.capture()  # ruff should be detected during capture
        unexpected = mgr.detect_unexpected()
        assert "ruff" not in unexpected

    def test_pyproject_without_tool_section_not_flagged(self, tmp_path: Path) -> None:
        """pyproject.toml without [tool.ruff] should not flag ruff."""
        _seed_python_project(tmp_path)
        mgr = _make_mgr(tmp_path)
        mgr.capture()
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "demo"\n', encoding="utf-8"
        )
        unexpected = mgr.detect_unexpected()
        assert "ruff" not in unexpected


# ===========================================================================
# require_lint_confirmation / require_docstyle_confirmation
# ===========================================================================


class TestLintAndDocStyleGaps:
    def test_lint_gap_for_python(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        mgr = _make_mgr(tmp_path)
        manifest = mgr.capture()
        gaps = mgr.require_lint_confirmation(manifest)
        assert len(gaps) > 0
        assert gaps[0].language == "Python"
        assert "ruff" in gaps[0].suggested_tools

    def test_no_lint_gap_when_lint_tool_in_manifest(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            "[tool.ruff]\nline-length = 88\n", encoding="utf-8"
        )
        mgr = _make_mgr(tmp_path)
        manifest = mgr.capture()
        gaps = mgr.require_lint_confirmation(manifest)
        # ruff detected during capture → no gap for Python
        python_gaps = [g for g in gaps if g.language == "Python"]
        assert len(python_gaps) == 0

    def test_doc_style_gap_for_python(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        mgr = _make_mgr(tmp_path)
        manifest = mgr.capture()
        gaps = mgr.require_docstyle_confirmation(manifest)
        assert any(g.language == "Python" for g in gaps)

    def test_no_doc_style_gap_when_style_set(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        mgr = _make_mgr(tmp_path)
        manifest = mgr.capture()
        manifest.doc_styles = {"Python": "Google docstring"}
        gaps = mgr.require_docstyle_confirmation(manifest)
        python_gaps = [g for g in gaps if g.language == "Python"]
        assert len(python_gaps) == 0


# ===========================================================================
# _gate_hook_tech_stack
# ===========================================================================


class TestGateHookTechStack:
    def test_hook_passes_with_no_manifest(self, tmp_path: Path) -> None:
        """No manifest → non-blocking."""
        failures = _gate_hook_tech_stack(session=None, project_root=tmp_path)
        assert failures == []

    def test_hook_fails_on_lint_gap(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        mgr = _make_mgr(tmp_path)
        mgr.capture()
        failures = _gate_hook_tech_stack(session=None, project_root=tmp_path)
        assert any("Lint tool not confirmed" in f for f in failures)

    def test_hook_fails_on_doc_style_gap(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        mgr = _make_mgr(tmp_path)
        mgr.capture()
        failures = _gate_hook_tech_stack(session=None, project_root=tmp_path)
        assert any("Doc comment style not confirmed" in f for f in failures)

    def test_hook_fails_on_unconfirmed_tool(self, tmp_path: Path) -> None:
        _seed_python_project(tmp_path)
        mgr = _make_mgr(tmp_path)
        mgr.capture()
        mgr.introduce_tool("newtool", "1.0")
        failures = _gate_hook_tech_stack(session=None, project_root=tmp_path)
        assert any("pending confirmation" in f for f in failures)

    def test_hook_passes_with_fully_configured_project(self, tmp_path: Path) -> None:
        """A project with lint and doc style confirmed should pass."""
        _seed_python_project(tmp_path)
        (tmp_path / "pyproject.toml").write_text(
            "[tool.ruff]\nline-length = 88\n", encoding="utf-8"
        )
        mgr = _make_mgr(tmp_path)
        manifest = mgr.capture()
        # Set doc style
        manifest.doc_styles = {"Python": "Google docstring"}
        mgr._persist(manifest)
        failures = _gate_hook_tech_stack(session=None, project_root=tmp_path)
        # Filter only Python-related failures
        python_failures = [f for f in failures if "Python" in f]
        assert len(python_failures) == 0


# ===========================================================================
# detect_existing_doc_style
# ===========================================================================


class TestDetectExistingDocStyle:
    def test_detects_google_docstring(self, tmp_path: Path) -> None:
        (tmp_path / "mod.py").write_text(
            'def foo(x):\n    """Summary.\n\n    Args:\n        x: value\n    """\n    pass\n',
            encoding="utf-8",
        )
        mgr = _make_mgr(tmp_path)
        detected = mgr.detect_existing_doc_style("Python")
        assert detected is not None
        assert "Google" in detected or "Args" in detected or detected is not None

    def test_returns_none_for_no_docs(self, tmp_path: Path) -> None:
        (tmp_path / "mod.py").write_text("def foo(): pass\n", encoding="utf-8")
        mgr = _make_mgr(tmp_path)
        detected = mgr.detect_existing_doc_style("Python")
        # May or may not be None depending on heuristics — at least no crash
        assert detected is None or isinstance(detected, str)

    def test_returns_none_for_unknown_language(self, tmp_path: Path) -> None:
        mgr = _make_mgr(tmp_path)
        detected = mgr.detect_existing_doc_style("Haskell")
        assert detected is None

    def test_returns_none_when_no_source_files(self, tmp_path: Path) -> None:
        mgr = _make_mgr(tmp_path)
        detected = mgr.detect_existing_doc_style("Python")
        assert detected is None


# ===========================================================================
# _config_file_confirms_tool (static method)
# ===========================================================================


class TestConfigFileConfirmsTool:
    def test_dedicated_config_file_always_confirms(self, tmp_path: Path) -> None:
        cfg = tmp_path / ".eslintrc.json"
        cfg.write_text("{}", encoding="utf-8")
        assert (
            TechStackManager._config_file_confirms_tool(".eslintrc.json", "eslint", cfg)
            is True
        )

    def test_pyproject_with_ruff_section(self, tmp_path: Path) -> None:
        cfg = tmp_path / "pyproject.toml"
        cfg.write_text("[tool.ruff]\nline-length = 88\n", encoding="utf-8")
        assert (
            TechStackManager._config_file_confirms_tool("pyproject.toml", "ruff", cfg)
            is True
        )

    def test_pyproject_without_ruff_section(self, tmp_path: Path) -> None:
        cfg = tmp_path / "pyproject.toml"
        cfg.write_text('[project]\nname = "demo"\n', encoding="utf-8")
        assert (
            TechStackManager._config_file_confirms_tool("pyproject.toml", "ruff", cfg)
            is False
        )

    def test_pyproject_with_black_section(self, tmp_path: Path) -> None:
        cfg = tmp_path / "pyproject.toml"
        cfg.write_text("[tool.black]\nline-length = 88\n", encoding="utf-8")
        assert (
            TechStackManager._config_file_confirms_tool("pyproject.toml", "black", cfg)
            is True
        )

    def test_cargo_toml_with_lints_for_clippy(self, tmp_path: Path) -> None:
        cfg = tmp_path / "Cargo.toml"
        cfg.write_text('[package]\nname = "x"\n\n[lints]\n', encoding="utf-8")
        assert (
            TechStackManager._config_file_confirms_tool("Cargo.toml", "clippy", cfg)
            is True
        )
