"""Technology stack version management — Gap 4 of the v0.8.0 governance release.

Captures languages, package managers, frameworks, dev tools, lint tools,
formatters, and doc-comment styles.  Persists to ``.harness/tech-stack.json``
and integrates with the INTAKE_ORIENTATION gate.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..file_ops.ndjson_writer import NDJSONWriter
from ..models.schemas import (
    DocStyleGap,
    LintGap,
    TechStackCheckResult,
    TechStackManifest,
    ToolIntroduction,
    VersionConstraint,
)

logger = logging.getLogger("harness.tech_stack")

# ---------------------------------------------------------------------------
# Language → file extension mapping
# ---------------------------------------------------------------------------

_LANGUAGE_EXTS: dict[str, list[str]] = {
    "Python": [".py", ".pyi", ".pyx"],
    "JavaScript": [".js", ".mjs", ".cjs"],
    "TypeScript": [".ts", ".tsx", ".mts", ".cts"],
    "Java": [".java"],
    "Kotlin": [".kt", ".kts"],
    "C#": [".cs"],
    "Go": [".go"],
    "Rust": [".rs"],
    "Ruby": [".rb"],
    "Swift": [".swift"],
    "C": [".c", ".h"],
    "C++": [".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx"],
    "Shell": [".sh", ".bash"],
    "SQL": [".sql"],
    "Docker": [],  # detected via Dockerfile presence, not extension
}

# ---------------------------------------------------------------------------
# Lint tool catalog — one entry per supported language
# ---------------------------------------------------------------------------

LINT_TOOL_CATALOG: dict[str, list[dict[str, Any]]] = {
    "Python": [
        {"name": "ruff", "config_files": ["pyproject.toml", "ruff.toml", ".ruff.toml"], "description": "Fast Python linter & formatter"},
        {"name": "flake8", "config_files": [".flake8", "setup.cfg", "tox.ini"], "description": "Python style checker (pyflakes + pycodestyle + mccabe)"},
        {"name": "pylint", "config_files": [".pylintrc", "pyproject.toml"], "description": "Comprehensive Python static analysis"},
        {"name": "black", "config_files": ["pyproject.toml"], "description": "Uncompromising Python formatter"},
        {"name": "mypy", "config_files": ["pyproject.toml", "mypy.ini", ".mypy.ini"], "description": "Optional static type checker"},
    ],
    "JavaScript": [
        {"name": "eslint", "config_files": [".eslintrc.js", ".eslintrc.json", ".eslintrc.yaml", ".eslintrc", "eslint.config.js", "eslint.config.mjs"], "description": "Pluggable JS linter"},
        {"name": "prettier", "config_files": [".prettierrc", ".prettierrc.json", ".prettierrc.yaml", ".prettierrc.js", "prettier.config.js"], "description": "Opinionated code formatter"},
        {"name": "biome", "config_files": ["biome.json", "biome.jsonc"], "description": "Fast formatter & linter (Rust-based)"},
        {"name": "oxlint", "config_files": ["oxlintrc.json", ".oxlintrc.json"], "description": "Fast JS/TS linter (Rust-based)"},
    ],
    "TypeScript": [
        {"name": "eslint", "config_files": [".eslintrc.js", ".eslintrc.json", ".eslintrc.yaml", ".eslintrc", "eslint.config.js", "eslint.config.mjs"], "description": "Pluggable TS linter (via @typescript-eslint)"},
        {"name": "prettier", "config_files": [".prettierrc", ".prettierrc.json", ".prettierrc.yaml", ".prettierrc.js", "prettier.config.js"], "description": "Opinionated code formatter"},
        {"name": "biome", "config_files": ["biome.json", "biome.jsonc"], "description": "Fast formatter & linter (Rust-based)"},
        {"name": "oxlint", "config_files": ["oxlintrc.json", ".oxlintrc.json"], "description": "Fast JS/TS linter (Rust-based)"},
    ],
    "Java": [
        {"name": "checkstyle", "config_files": ["checkstyle.xml", "checkstyle-suppressions.xml"], "description": "Style checker for Java"},
        {"name": "spotbugs", "config_files": ["spotbugs-exclude.xml"], "description": "Bug pattern detector"},
        {"name": "pmd", "config_files": ["pmd-ruleset.xml"], "description": "Static analysis for Java"},
        {"name": "sonarlint", "config_files": ["sonarlint.json"], "description": "IDE-integrated lint (SonarSource)"},
    ],
    "Kotlin": [
        {"name": "detekt", "config_files": ["detekt.yml", "detekt.yaml"], "description": "Static analysis for Kotlin"},
        {"name": "ktlint", "config_files": [".editorconfig"], "description": "Kotlin linter & formatter"},
    ],
    "C#": [
        {"name": "StyleCop", "config_files": [".stylecop.json", ".stylecop"], "description": "Style enforcement for C#"},
        {"name": "Roslyn analyzers", "config_files": [".editorconfig", "Directory.Build.props"], "description": "Built-in .NET compiler analyzers"},
        {"name": "dotnet-format", "config_files": [".editorconfig"], "description": "Official .NET formatter"},
    ],
    "Go": [
        {"name": "golangci-lint", "config_files": [".golangci.yml", ".golangci.yaml", ".golangci.toml"], "description": "Fast Go linter aggregator"},
        {"name": "staticcheck", "config_files": ["staticcheck.conf"], "description": "Advanced Go static analysis"},
        {"name": "gofmt", "config_files": [], "description": "Standard Go formatter (built-in)"},
    ],
    "Rust": [
        {"name": "clippy", "config_files": ["Cargo.toml", "clippy.toml"], "description": "Official Rust linter"},
        {"name": "rustfmt", "config_files": ["rustfmt.toml", ".rustfmt.toml"], "description": "Official Rust formatter"},
    ],
    "Ruby": [
        {"name": "rubocop", "config_files": [".rubocop.yml", ".rubocop.yaml", ".rubocop.yml"], "description": "Ruby linter & formatter"},
        {"name": "standard", "config_files": [".standard.yml"], "description": "Ruby style guide, formatter, and linter"},
    ],
    "Swift": [
        {"name": "swiftlint", "config_files": [".swiftlint.yml"], "description": "Linter for Swift"},
    ],
    "C": [
        {"name": "clang-tidy", "config_files": [".clang-tidy"], "description": "Clang-based C/C++ linter"},
        {"name": "cppcheck", "config_files": ["cppcheck.cfg"], "description": "Static analysis for C/C++"},
        {"name": "clang-format", "config_files": [".clang-format"], "description": "Clang-based formatter"},
    ],
    "C++": [
        {"name": "clang-tidy", "config_files": [".clang-tidy"], "description": "Clang-based C/C++ linter"},
        {"name": "cppcheck", "config_files": ["cppcheck.cfg"], "description": "Static analysis for C/C++"},
        {"name": "clang-format", "config_files": [".clang-format"], "description": "Clang-based formatter"},
    ],
    "Shell": [
        {"name": "shellcheck", "config_files": [".shellcheckrc"], "description": "Shell script analysis"},
        {"name": "shfmt", "config_files": [], "description": "Shell script formatter"},
    ],
    "Docker": [
        {"name": "hadolint", "config_files": [".hadolint.yaml", ".hadolint.yml"], "description": "Dockerfile linter"},
    ],
}

#: Universal tools that apply across languages.
_UNIVERSAL_LINT_TOOLS: list[dict[str, Any]] = [
    {"name": "editorconfig", "config_files": [".editorconfig"], "description": "Cross-editor code style"},
    {"name": "pre-commit", "config_files": [".pre-commit-config.yaml"], "description": "Git hook framework"},
]

# ---------------------------------------------------------------------------
# Document comment style catalog
# ---------------------------------------------------------------------------

DOC_STYLE_CATALOG: dict[str, list[dict[str, Any]]] = {
    "Python": [
        {"name": "Google docstring", "format": '"""Summary.\n\nArgs:\n    name: description\nReturns:\n    type: description\n"""', "tools": ["pydocstyle", "interrogate", "sphinx"], "lint_rule": "pydocstyle (ruff D rules)"},
        {"name": "NumPy docstring", "format": '"""Summary.\n\nParameters\n----------\nname : type\n    description\n"""', "tools": ["pydocstyle", "numpydoc"], "lint_rule": "pydocstyle + numpydoc validation"},
        {"name": "Sphinx reST", "format": '"""Summary.\n\n:param name: description\n:type name: type\n:returns: description\n"""', "tools": ["sphinx", "pydocstyle"], "lint_rule": "pydocstyle (ruff D rules)"},
        {"name": "PEP 257 (plain)", "format": '"""Summary line.\n\nExtended description.\n"""', "tools": ["pydocstyle"], "lint_rule": "pydocstyle (basic D rules)"},
        {"name": "no-doc-required", "format": "", "tools": [], "lint_rule": "none"},
    ],
    "Java": [
        {"name": "Javadoc", "format": "/**\n * Summary.\n *\n * @param name description\n * @return description\n */", "tools": ["checkstyle (javadoc rules)", "spotbugs"], "lint_rule": "checkstyle JavadocMethod/JavadocType"},
        {"name": "no-doc-required", "format": "", "tools": [], "lint_rule": "none"},
    ],
    "JavaScript": [
        {"name": "JSDoc", "format": "/**\n * Summary.\n * @param {string} name - description\n * @returns {string} description\n */", "tools": ["eslint-plugin-jsdoc", "jsdoc"], "lint_rule": "eslint jsdoc rules"},
        {"name": "TSDoc", "format": "/**\n * Summary.\n * @param name - description\n * @returns description\n */", "tools": ["typedoc", "eslint-plugin-tsdoc"], "lint_rule": "eslint tsdoc rules"},
        {"name": "no-doc-required", "format": "", "tools": [], "lint_rule": "none"},
    ],
    "TypeScript": [
        {"name": "JSDoc", "format": "/**\n * Summary.\n * @param {string} name - description\n * @returns {string} description\n */", "tools": ["eslint-plugin-jsdoc", "typedoc"], "lint_rule": "eslint jsdoc rules"},
        {"name": "TSDoc", "format": "/**\n * Summary.\n * @param name - description\n * @returns description\n */", "tools": ["typedoc", "eslint-plugin-tsdoc"], "lint_rule": "eslint tsdoc rules"},
        {"name": "no-doc-required", "format": "", "tools": [], "lint_rule": "none"},
    ],
    "C#": [
        {"name": "XML doc comments", "format": "/// <summary>\n/// Description.\n/// </summary>\n/// <param name=\"x\">description</param>", "tools": ["StyleCop (SA16xx)", "DocFX"], "lint_rule": "StyleCop SA16xx rules"},
        {"name": "no-doc-required", "format": "", "tools": [], "lint_rule": "none"},
    ],
    "Go": [
        {"name": "godoc", "format": "// Package x provides ...\n//\n// FuncName does ...", "tools": ["golangci-lint (revive)", "go doc"], "lint_rule": "revive: exported, comment-format"},
        {"name": "no-doc-required", "format": "", "tools": [], "lint_rule": "none"},
    ],
    "Rust": [
        {"name": "doc comments (///)", "format": "/// Brief summary.\n///\n/// # Panics\n///\n/// # Examples\n///", "tools": ["clippy (missing_docs)", "rustdoc"], "lint_rule": "clippy::missing_docs_in_private_items"},
        {"name": "no-doc-required", "format": "", "tools": [], "lint_rule": "none"},
    ],
    "Ruby": [
        {"name": "YARD", "format": "# @param name [String] description\n# @return [String] description", "tools": ["yard", "rubocop (Documentation)"], "lint_rule": "rubocop Style/Documentation"},
        {"name": "RDoc", "format": "#\n# = Description\n#\n# == Parameters\n#", "tools": ["rdoc", "rubocop"], "lint_rule": "rubocop Style/Documentation"},
        {"name": "no-doc-required", "format": "", "tools": [], "lint_rule": "none"},
    ],
    "Kotlin": [
        {"name": "KDoc", "format": "/**\n * Summary.\n *\n * @param name description\n * @return description\n */", "tools": ["detekt (comments rules)", "dokka"], "lint_rule": "detekt comments rules"},
        {"name": "no-doc-required", "format": "", "tools": [], "lint_rule": "none"},
    ],
    "Swift": [
        {"name": "DocC markup", "format": "/// Brief summary.\n///\n/// - Parameter name: description\n/// - Returns: description", "tools": ["swiftlint (missing_docs)"], "lint_rule": "swiftlint missing_docs"},
        {"name": "no-doc-required", "format": "", "tools": [], "lint_rule": "none"},
    ],
    "C": [
        {"name": "Doxygen", "format": "/**\n * Brief summary.\n *\n * @param name description\n * @return description\n */", "tools": ["doxygen", "clang-tidy"], "lint_rule": "clang-tidy documentation checks"},
        {"name": "no-doc-required", "format": "", "tools": [], "lint_rule": "none"},
    ],
    "C++": [
        {"name": "Doxygen", "format": "/**\n * Brief summary.\n *\n * @param name description\n * @return description\n */", "tools": ["doxygen", "clang-tidy"], "lint_rule": "clang-tidy documentation checks"},
        {"name": "no-doc-required", "format": "", "tools": [], "lint_rule": "none"},
    ],
    "Shell": [
        {"name": "header-comment", "format": "# Usage: script.sh <arg>\n# Description: ...\n#", "tools": [], "lint_rule": "none (manual review)"},
        {"name": "no-doc-required", "format": "", "tools": [], "lint_rule": "none"},
    ],
    "SQL": [
        {"name": "header-comment", "format": "-- Purpose: ...\n-- Author: ...\n--", "tools": [], "lint_rule": "none (manual review)"},
        {"name": "no-doc-required", "format": "", "tools": [], "lint_rule": "none"},
    ],
    "Docker": [
        {"name": "header-comment", "format": "# Purpose: ...\n#", "tools": [], "lint_rule": "none (manual review)"},
        {"name": "no-doc-required", "format": "", "tools": [], "lint_rule": "none"},
    ],
}

#: Universal doc style options available for any language.
_UNIVERSAL_DOC_STYLES: list[str] = [
    "README-only",
    "inline-only",
    "strict-every-public",
]

# ---------------------------------------------------------------------------
# Package manager detection
# ---------------------------------------------------------------------------

_PACKAGE_MANAGER_SIGNATURES: dict[str, list[str]] = {
    "pip": ["requirements.txt", "requirements-dev.txt"],
    "poetry": ["poetry.lock"],
    "pyproject": ["pyproject.toml"],  # generic — resolved to pip/poetry downstream
    "pipenv": ["Pipfile", "Pipfile.lock"],
    "setuptools": ["setup.py", "setup.cfg"],
    "npm": ["package-lock.json"],
    "yarn": ["yarn.lock"],
    "pnpm": ["pnpm-lock.yaml"],
    "go-mod": ["go.mod", "go.sum"],
    "cargo": ["Cargo.toml", "Cargo.lock"],
    "bundler": ["Gemfile", "Gemfile.lock"],
    "maven": ["pom.xml"],
    "gradle": ["build.gradle", "build.gradle.kts", "settings.gradle"],
    "nuget": ["packages.config", "Directory.Packages.props"],
    "swift-pm": ["Package.swift"],
    "composer": ["composer.json", "composer.lock"],
    "cabal": ["*.cabal"],
    "stack": ["stack.yaml"],
    "mix": ["mix.exs"],
    "sbt": ["build.sbt"],
}


# ---------------------------------------------------------------------------
# TechStackManager
# ---------------------------------------------------------------------------


class TechStackManager:
    """Detect, capture, and validate a project's technology stack.

    Persists the manifest to ``.harness/tech-stack.json`` so that
    subsequent gate checks can detect drift, unconfirmed tools, and
    missing lint / doc-style choices.
    """

    MANIFEST_PATH = Path(".harness/tech-stack.json")

    def __init__(self, project_root: Path) -> None:
        self._project_root = project_root

    # -- Public API -----------------------------------------------------------

    def capture(self) -> TechStackManifest:
        """Scan the project and build a new manifest.

        Persists the result to ``.harness/tech-stack.json``.
        """
        languages = self.detect_project_languages()
        package_managers = self._detect_package_managers()
        lint_tools = self._capture_lint_tools(languages)
        formatters = self._capture_formatters(languages)
        doc_styles = self._capture_doc_styles(languages)

        manifest = TechStackManifest(
            languages=tuple(languages),
            package_managers=tuple(package_managers),
            frameworks=(),  # v0.8.0: framework detection deferred
            dev_tools=(),
            lint_tools=tuple(lint_tools),
            formatters=tuple(formatters),
            doc_styles=doc_styles,
            introduced_tools=(),
            captured_at=datetime.now(timezone.utc).isoformat(),
        )

        self._persist(manifest)
        return manifest

    def load(self) -> TechStackManifest | None:
        """Load a previously persisted manifest, or None."""
        path = self._project_root / self.MANIFEST_PATH
        if not path.is_file():
            return None
        try:
            return TechStackManifest.model_validate_json(path.read_text(encoding="utf-8"))
        except Exception:
            logger.warning("Failed to parse tech-stack manifest", exc_info=True)
            return None

    def check(self) -> TechStackCheckResult:
        """Validate the current environment against the persisted manifest."""
        manifest = self.load()
        if manifest is None:
            return TechStackCheckResult(
                passed=False,
                violations=("No tech-stack manifest found — run 'harness tech-stack capture' first.",),
            )

        violations: list[str] = []
        unchecked_tools: list[str] = []

        # Detect unexpected tools not yet registered.
        unexpected = self.detect_unexpected()
        for tool in unexpected:
            violations.append(f"Unregistered tool detected: {tool}")

        # Check for lint gaps.
        lint_gaps = self.require_lint_confirmation(manifest)
        for gap in lint_gaps:
            violations.append(
                f"Lint tool not confirmed for {gap.language}: "
                f"suggested {', '.join(gap.suggested_tools)}"
            )

        # Check for doc-style gaps.
        doc_gaps = self.require_docstyle_confirmation(manifest)
        for gap in doc_gaps:
            violations.append(
                f"Doc comment style not confirmed for {gap.language}: "
                f"suggested {', '.join(gap.suggested_styles)}"
            )

        # Check for unconfirmed introduced tools.
        pending = tuple(
            t for t in manifest.introduced_tools if not t.confirmed
        )

        return TechStackCheckResult(
            passed=len(violations) == 0 and len(pending) == 0,
            violations=tuple(violations),
            new_tools_pending_confirmation=pending,
            unchecked_tools=tuple(unchecked_tools),
            lint_gaps=tuple(lint_gaps),
            doc_style_gaps=tuple(doc_gaps),
        )

    def introduce_tool(
        self,
        tool_name: str,
        version: str,
        rationale: str = "",
        session_id: str = "",
        tool_category: str = "dev_tool",
    ) -> ToolIntroduction:
        """Record a new tool as unconfirmed and persist the manifest."""
        manifest = self.load()
        if manifest is None:
            manifest = TechStackManifest(captured_at=datetime.now(timezone.utc).isoformat())

        intro = ToolIntroduction(
            tool_name=tool_name,
            version=version,
            introduced_by=session_id,
            confirmed=False,
            confirmation_method="",
            tool_category=tool_category,
        )

        manifest.introduced_tools = (*manifest.introduced_tools, intro)
        self._persist(manifest)
        return intro

    def confirm_tool(self, tool_name: str) -> bool:
        """Mark an introduced tool as confirmed.  Returns True if found."""
        manifest = self.load()
        if manifest is None:
            return False

        updated = tuple(
            ToolIntroduction(
                tool_name=t.tool_name,
                version=t.version,
                introduced_by=t.introduced_by,
                confirmed=True if t.tool_name == tool_name else t.confirmed,
                confirmation_method="cli" if t.tool_name == tool_name else t.confirmation_method,
                tool_category=t.tool_category,
            )
            for t in manifest.introduced_tools
        )

        old_confirmed = {t.tool_name for t in manifest.introduced_tools if t.confirmed}
        new_confirmed = {t.tool_name for t in updated if t.confirmed}

        if old_confirmed == new_confirmed:
            # No change — tool_name not found or already confirmed.
            return False

        manifest.introduced_tools = updated
        self._persist(manifest)
        return True

    def detect_unexpected(self) -> list[str]:
        """Scan for tools present on the project that are not in the manifest.

        v0.8.0 uses a lightweight heuristic: checks for common tool
        config files that are not reflected in the manifest.
        """
        manifest = self.load()
        known_tool_names: set[str] = set()
        if manifest is not None:
            for t in manifest.lint_tools:
                known_tool_names.add(t.tool_name)
            for t in manifest.formatters:
                known_tool_names.add(t.tool_name)
            for t in manifest.introduced_tools:
                known_tool_names.add(t.tool_name)

        unexpected: list[str] = []
        root = self._project_root

        for lang_tools in LINT_TOOL_CATALOG.values():
            for tool_info in lang_tools:
                if tool_info["name"] in known_tool_names:
                    continue
                for cfg_pattern in tool_info["config_files"]:
                    matches = list(root.glob(cfg_pattern))
                    if matches:
                        # For shared config files (pyproject.toml), verify
                        # the tool section actually exists inside.
                        if self._config_file_confirms_tool(
                            cfg_pattern, tool_info["name"], matches[0]
                        ):
                            unexpected.append(tool_info["name"])
                        break

        for universal in _UNIVERSAL_LINT_TOOLS:
            if universal["name"] not in known_tool_names:
                for cfg_pattern in universal["config_files"]:
                    matches = list(root.glob(cfg_pattern))
                    if matches:
                        if self._config_file_confirms_tool(
                            cfg_pattern, universal["name"], matches[0]
                        ):
                            unexpected.append(universal["name"])
                        break

        return unexpected

    @staticmethod
    def _config_file_confirms_tool(
        cfg_pattern: str, tool_name: str, config_path: Path
    ) -> bool:
        """Check whether *config_path* actually enables *tool_name*.

        For generic config files like ``pyproject.toml``, a file-match
        alone is not enough — the tool's section must be present.
        """
        if config_path.name not in ("pyproject.toml", "setup.cfg", "Cargo.toml"):
            return True  # file name alone is a strong enough signal

        try:
            content = config_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return False

        # pyproject.toml: look for [tool.<name>]
        if config_path.name == "pyproject.toml":
            section = re.search(
                rf'\[tool\.{re.escape(tool_name)}\]',
                content,
            )
            if section:
                return True
            # ruff can be configured under [tool.ruff] or [tool.ruff.*]
            # black under [tool.black], mypy under [tool.mypy]
            return False

        # Cargo.toml: look for [lints] section for clippy
        if config_path.name == "Cargo.toml" and tool_name in ("clippy", "rustfmt"):
            return bool(re.search(r'\[lints', content)) or tool_name in content

        return True

    # -- Language detection ---------------------------------------------------

    def detect_project_languages(self) -> list[str]:
        """Scan the project for programming languages by file extension.

        Returns a sorted list of unique language names.
        """
        found: set[str] = set()
        root = self._project_root

        for lang, exts in _LANGUAGE_EXTS.items():
            if lang == "Docker":
                continue
            for ext in exts:
                try:
                    # Use a bounded glob — check up to 3 levels deep.
                    matches = list(root.glob(f"**/*{ext}"))
                    if matches:
                        # Still sample to avoid huge repos.
                        found.add(lang)
                        break
                except Exception:
                    pass

        # Docker detection by file presence.
        if (root / "Dockerfile").exists() or list(root.glob("**/Dockerfile*")):
            found.add("Docker")
        if (root / "docker-compose.yml").exists() or (root / "docker-compose.yaml").exists():
            found.add("Docker")

        # Shell detection — always add if .sh files exist, plus common CI scripts.
        if list(root.glob("**/*.sh")):
            found.add("Shell")

        return sorted(found)

    # -- Lint tool helpers ----------------------------------------------------

    def suggest_lint_tools(self, language: str) -> list[str]:
        """Return recommended lint tools for *language*."""
        tools = [t["name"] for t in LINT_TOOL_CATALOG.get(language, [])]
        tools.extend(u["name"] for u in _UNIVERSAL_LINT_TOOLS)
        return tools

    def detect_configured_lints(self) -> dict[str, tuple[str, str | None]]:
        """Scan for lint configuration files on disk.

        Returns ``{language: (config_path, detected_version)}``.
        ``detected_version`` is ``None`` when it cannot be inferred from
        the config file alone.
        """
        result: dict[str, tuple[str, str | None]] = {}
        root = self._project_root

        for language in self.detect_project_languages():
            tools = LINT_TOOL_CATALOG.get(language, [])
            for tool_info in tools:
                for cfg_pattern in tool_info["config_files"]:
                    matches = list(root.glob(cfg_pattern))
                    if matches:
                        config_path = str(matches[0].relative_to(root))
                        version = self._infer_version_from_config(
                            tool_info["name"], matches[0]
                        )
                        result[language] = (config_path, version)
                        break
                if language in result:
                    break

        # Universal tools.
        for universal in _UNIVERSAL_LINT_TOOLS:
            for cfg_pattern in universal["config_files"]:
                if list(root.glob(cfg_pattern)):
                    # Don't override language-specific results.
                    if "universal" not in result:
                        result["universal"] = (cfg_pattern, None)
                    break

        return result

    def require_lint_confirmation(
        self, manifest: TechStackManifest
    ) -> list[LintGap]:
        """Return lint gaps for each language that lacks a confirmed tool.

        A language is considered "covered" when either:
        * a lint tool for that language is already recorded in
          ``manifest.lint_tools`` (matched by name against
          :data:`LINT_TOOL_CATALOG`), or
        * a lint config file for that language is detected on disk by
          :meth:`detect_configured_lints`.
        """
        gaps: list[LintGap] = []
        configured = self.detect_configured_lints()

        # Pre-compute, per language, the set of tool names that count as
        # lint coverage for that language (so a Python lint tool does
        # NOT cover Java, etc.).
        confirmed_by_lang: dict[str, set[str]] = {lang: set() for lang in manifest.languages}
        for lang in manifest.languages:
            catalog_names = {
                entry["name"] for entry in LINT_TOOL_CATALOG.get(lang, [])
            }
            for t in manifest.lint_tools:
                if t.tool_category == "lint" and t.tool_name in catalog_names:
                    confirmed_by_lang[lang].add(t.tool_name)

        for language in manifest.languages:
            if confirmed_by_lang.get(language):
                continue
            if language in configured:
                continue

            existing = configured.get(language)
            gap = LintGap(
                language=language,
                suggested_tools=tuple(self.suggest_lint_tools(language)),
                detected_config=existing[0] if existing else None,
                detected_version=existing[1] if existing else None,
                selected_tool="",
                confirmed=False,
            )
            gaps.append(gap)

        return gaps

    def require_docstyle_confirmation(
        self, manifest: TechStackManifest
    ) -> list[DocStyleGap]:
        """Return doc-style gaps for each language that lacks a confirmed style."""
        gaps: list[DocStyleGap] = []

        for language in manifest.languages:
            if language in manifest.doc_styles:
                continue

            styles = self.suggest_doc_styles(language)
            detected = self.detect_existing_doc_style(language)

            gap = DocStyleGap(
                language=language,
                suggested_styles=tuple(styles),
                selected_style="",
                detected_style=detected,
                confirmed=False,
            )
            gaps.append(gap)

        return gaps

    # -- Doc style helpers ----------------------------------------------------

    def suggest_doc_styles(self, language: str) -> list[str]:
        """Return recommended doc comment styles for *language*."""
        styles = [s["name"] for s in DOC_STYLE_CATALOG.get(language, [])]
        return styles

    def detect_existing_doc_style(self, language: str) -> str | None:
        """Heuristically detect the doc-comment style used in source files.

        Scans a sample of source files for the given *language* and
        looks for signature patterns of known styles.  Returns the
        style name, or ``None`` if no clear signal is found.
        """
        exts = _LANGUAGE_EXTS.get(language, [])
        if not exts:
            return None

        root = self._project_root

        # Collect a sample of source files (up to 20).
        sample_files: list[Path] = []
        for ext in exts:
            for p in root.glob(f"**/*{ext}"):
                sample_files.append(p)
                if len(sample_files) >= 20:
                    break
            if len(sample_files) >= 20:
                break

        if not sample_files:
            return None

        styles = DOC_STYLE_CATALOG.get(language, [])
        scores: dict[str, int] = {}

        for fp in sample_files[:20]:
            try:
                content = fp.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue

            for style_info in styles:
                name = style_info["name"]
                if name == "no-doc-required":
                    continue
                fmt = style_info.get("format", "")
                if not fmt:
                    continue

                # Extract the first "significant" line from the format example
                # (not the opening comment marker) and look for it in source.
                signature_keywords = self._extract_signature(fmt)
                for kw in signature_keywords:
                    if kw in content:
                        scores[name] = scores.get(name, 0) + 1

        if not scores:
            return None
        return max(scores, key=scores.get)

    @staticmethod
    def _extract_signature(format_example: str) -> list[str]:
        """Extract distinctive keywords from a doc-comment format example."""
        keywords: list[str] = []
        # Look for @param, :param, Args:, etc.
        for pattern in [r"@param\b", r":param\b", r"Args:", r"Parameters",
                        r"@return\b", r":returns?", r"Returns:", r"<param\b",
                        r"<summary>", r"/// ", r"@throws\b"]:
            if re.search(pattern, format_example):
                keywords.append(pattern.replace(r"\b", ""))
        return keywords if keywords else [format_example[:20].strip()]

    # -- Internal helpers -----------------------------------------------------

    def _persist(self, manifest: TechStackManifest) -> None:
        """Write the manifest to ``.harness/tech-stack.json``."""
        path = self._project_root / self.MANIFEST_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            manifest.model_dump_json(indent=2, exclude_none=True),
            encoding="utf-8",
        )

    def _detect_package_managers(self) -> list[str]:
        """Detect package managers from lock/config files."""
        found: list[str] = []
        root = self._project_root
        for pm_name, signatures in _PACKAGE_MANAGER_SIGNATURES.items():
            for sig in signatures:
                matches = list(root.glob(sig))
                if matches:
                    found.append(pm_name)
                    break
        return found

    def _capture_lint_tools(self, languages: list[str]) -> list[VersionConstraint]:
        """Build VersionConstraint entries for detected lint configurations."""
        constraints: list[VersionConstraint] = []
        configured = self.detect_configured_lints()

        for language, (config_path, version) in configured.items():
            # Map config path back to tool name.
            tool_name = self._config_path_to_tool(language, config_path)
            constraints.append(
                VersionConstraint(
                    tool_name=tool_name,
                    declared_version=version or "",
                    detected_version=version,
                    constraint_type="exact" if version else "unpinned",
                    is_satisfied=True,
                    tool_category="lint",
                )
            )
        return constraints

    def _capture_formatters(self, languages: list[str]) -> list[VersionConstraint]:
        """Detect formatter tools (subset of lint tools that format)."""
        # v0.8.0: formatters are a subset of lint tools with formatting capability.
        formatter_names = {"black", "prettier", "biome", "rustfmt", "gofmt",
                           "shfmt", "clang-format", "dotnet-format", "ktlint"}
        constraints: list[VersionConstraint] = []
        configured = self.detect_configured_lints()

        for language, (config_path, version) in configured.items():
            tool_name = self._config_path_to_tool(language, config_path)
            if tool_name in formatter_names:
                constraints.append(
                    VersionConstraint(
                        tool_name=tool_name,
                        declared_version=version or "",
                        detected_version=version,
                        constraint_type="exact" if version else "unpinned",
                        is_satisfied=True,
                        tool_category="formatter",
                    )
                )
        return constraints

    def _capture_doc_styles(self, languages: list[str]) -> dict[str, str]:
        """Detect or default doc comment styles for each language."""
        styles: dict[str, str] = {}
        for language in languages:
            detected = self.detect_existing_doc_style(language)
            if detected:
                styles[language] = detected
        return styles

    def _config_path_to_tool(self, language: str, config_path: str) -> str:
        """Infer the tool name from a language + config file path."""
        if language == "universal":
            for u in _UNIVERSAL_LINT_TOOLS:
                if any(config_path.endswith(cf.replace(".", "").replace("/", "").replace("\\", ""))
                       or cf in config_path
                       for cf in u["config_files"]):
                    return u["name"]
            return "unknown"

        tools = LINT_TOOL_CATALOG.get(language, [])
        for tool_info in tools:
            for cf in tool_info["config_files"]:
                if cf in config_path or config_path.endswith(cf):
                    return tool_info["name"]
        # Fallback: use file stem.
        return Path(config_path).stem

    def _infer_version_from_config(
        self, tool_name: str, config_path: Path
    ) -> str | None:
        """Try to read a tool version from its config file.

        v0.8.0 supports: pyproject.toml (tool.ruff, tool.black, mypy),
        package.json (devDependencies), .pre-commit-config.yaml (rev).
        """
        try:
            content = config_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return None

        # pyproject.toml: [tool.ruff], [tool.black], [tool.mypy]
        if config_path.name in ("pyproject.toml", "ruff.toml", ".ruff.toml"):
            match = re.search(
                rf'(?:ruff|black|mypy).*?version\s*=\s*"([^"]+)"',
                content,
                re.DOTALL,
            )
            if match:
                return match.group(1)

        # package.json: devDependencies / dependencies
        if config_path.name == "package.json":
            try:
                data = json.loads(content)
                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                search_names = {
                    "eslint": ["eslint"],
                    "prettier": ["prettier"],
                    "biome": ["@biomejs/biome"],
                    "oxlint": ["oxlint"],
                }
                for name in search_names.get(tool_name, [tool_name]):
                    if name in deps:
                        return deps[name].lstrip("^~>= ")
            except json.JSONDecodeError:
                pass

        # .pre-commit-config.yaml: rev
        if config_path.name == ".pre-commit-config.yaml":
            match = re.search(rf'{re.escape(tool_name)}.*?\n\s+rev:\s*(\S+)', content)
            if match:
                return match.group(1)

        return None


# ---------------------------------------------------------------------------
# Gate hook registration — called at import time
# ---------------------------------------------------------------------------


def _gate_hook_tech_stack(
    session,  # SessionState
    project_root: Path,
) -> list[str]:
    """INTAKE_ORIENTATION hook: ensure lint + doc style are confirmed.

    Returns a list of failure message strings (empty = all passed).
    """
    failures: list[str] = []
    mgr = TechStackManager(project_root)
    manifest = mgr.load()

    # If no manifest exists yet, the hook is non-blocking (capture
    # happens during init or governed-start before the gate runs).
    if manifest is None:
        return failures

    # Pre-compute, per language, the set of tool names that count as
    # lint coverage for that language (so a Python lint tool does NOT
    # cover Java, etc.). Mirrors require_lint_confirmation.
    configured = mgr.detect_configured_lints()
    confirmed_by_lang: dict[str, set[str]] = {lang: set() for lang in manifest.languages}
    for lang in manifest.languages:
        catalog_names = {
            entry["name"] for entry in LINT_TOOL_CATALOG.get(lang, [])
        }
        for t in manifest.lint_tools:
            if t.tool_category == "lint" and t.tool_name in catalog_names:
                confirmed_by_lang[lang].add(t.tool_name)

    for lang in manifest.languages:
        # Check lint tool confirmation (per-language).
        if not confirmed_by_lang.get(lang) and lang not in configured:
            failures.append(
                f"Lint tool not confirmed for {lang}. "
                f"Run 'harness tech-stack lint {lang} --tool <name>' to confirm."
            )

        # Check doc style confirmation.
        if lang not in manifest.doc_styles:
            failures.append(
                f"Doc comment style not confirmed for {lang}. "
                f"Run 'harness tech-stack docstyle {lang} --style <name>' to confirm."
            )

    # Check for unconfirmed introduced tools.
    for t in manifest.introduced_tools:
        if not t.confirmed:
            failures.append(
                f"Tool '{t.tool_name}' @ {t.version} is pending confirmation. "
                f"Run 'harness tech-stack add {t.tool_name} --version {t.version}' to confirm."
            )

    return failures


# Module-level registration — fires when tech_stack is imported.
try:
    from .gates import HarnessLayer, register_gate_hook

    register_gate_hook(HarnessLayer.INTAKE_ORIENTATION, _gate_hook_tech_stack)
except ImportError:
    pass
