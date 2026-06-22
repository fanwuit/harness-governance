"""Template renderer for role-prompt templates.

Loads a role template from ``data/role-prompts/`` and substitutes
``{{VARIABLE_NAME}}`` placeholders with exact values from
:class:`~harness_governance.runner.variables.RoleVariables`.

The renderer is a pure string-replacement engine — no LLM reasoning,
no paraphrasing, no commentary.  Missing variables are replaced with
``NOT FOUND: {{VARIABLE_NAME}}`` so the agent can see what was expected
but not provided.
"""

from __future__ import annotations

import re
from dataclasses import fields as dataclass_fields
from importlib import resources
from typing import Mapping

from .variables import RoleVariables, fill_missing

_TEMPLATES_PACKAGE = "harness_governance.data.role-prompts"

# Maps RoleVariables field names → template placeholder names.
# Template placeholders use UPPER_SNAKE_CASE.
_FIELD_TO_PLACEHOLDER: dict[str, str] = {
    "queue_item_raw": "QUEUE_ITEM",
    "owner_files": "OWNER_FILES",
    "contracts": "CONTRACTS",
    "test_plan": "TEST_PLAN",
    "scope": "SCOPE",
    "allowed_assumptions": "ALLOWED_ASSUMPTIONS",
    "allowed_scope": "ALLOWED_SCOPE",
    "expected_behavior": "EXPECTED_BEHAVIOR",
    "failure_behavior": "FAILURE_BEHAVIOR",
    "forbidden_scope": "FORBIDDEN_SCOPE",
    "verification_commands": "VERIFICATION_COMMANDS",
    "done_when": "DONE_WHEN",
    "git_diff": "GIT_DIFF",
    "project_context": "PROJECT_CONTEXT",
    "success_criteria": "SUCCESS_CRITERIA",
    "non_goals": "NON_GOALS",
    "stop_conditions": "STOP_CONDITIONS",
    "worker_results": "WORKER_RESULTS",
}

# Known role names → template file stems.
# Each key is an accepted role name (including aliases and display forms);
# the value is the template file stem (without .md suffix).
_ROLE_TO_TEMPLATE: dict[str, str] = {
    # Orchestrator (dispatcher, not dispatched)
    "orchestrator": "orchestrator",
    # Core pipeline roles
    "planner": "planner",
    "spec-writer": "spec-writer",
    "spec_writer": "spec-writer",
    "spec writer": "spec-writer",
    "contract-writer": "contract-writer",
    "contract_writer": "contract-writer",
    "contract/test writer": "contract-writer",
    "contract test writer": "contract-writer",
    "test-writer": "test-writer",
    "test_writer": "test-writer",
    "test writer": "test-writer",
    "implementer": "implementer",
    "product-implementer": "product-implementer",
    "product_implementer": "product-implementer",
    "product implementer": "product-implementer",
    "reviewer": "reviewer",
    "reviewer/verifier": "reviewer",
    "reviewer verifier": "reviewer",
    # Governance roles
    "adr-writer": "adr-writer",
    "adr_writer": "adr-writer",
    "adr writer": "adr-writer",
    "fact-finder-reviewer": "fact-finder-reviewer",
    "fact_finder_reviewer": "fact-finder-reviewer",
    "fact finder reviewer": "fact-finder-reviewer",
    "fact finder": "fact-finder-reviewer",
    "fact-finder": "fact-finder-reviewer",
    "readiness-gate-writer": "readiness-gate-writer",
    "readiness_gate_writer": "readiness-gate-writer",
    "readiness gate writer": "readiness-gate-writer",
    "readiness": "readiness-gate-writer",
    "document-gardener": "document-gardener",
    "document_gardener": "document-gardener",
    "document gardener": "document-gardener",
    "integrator": "integrator",
}

# Regex for {{PLACEHOLDER}} tokens.
_PLACEHOLDER_RE = re.compile(r"\{\{([A-Z_]+)\}\}")


class TemplateRenderer:
    """Load and render role-prompt templates."""

    def load_template(self, role: str) -> str:
        """Load the raw template text for ``role``.

        Accepts role names like ``"implementer"``, ``"reviewer"``,
        ``"planner"``, ``"contract-writer"`` (or ``"contract_writer"``).
        """
        stem = _ROLE_TO_TEMPLATE.get(role)
        if stem is None:
            raise ValueError(
                f"Unknown role: {role!r}. Known roles: {sorted(_ROLE_TO_TEMPLATE)}"
            )

        resource = resources.files(_TEMPLATES_PACKAGE).joinpath(f"{stem}.md")
        if not resource.is_file():
            raise FileNotFoundError(f"Template not found in package data: {stem}.md")
        return resource.read_text(encoding="utf-8")

    def render(self, role: str, variables: RoleVariables) -> str:
        """Render a role template with variable substitution.

        1. Load the template for ``role``.
        2. Build a substitution map from ``variables``.
        3. Replace every ``{{PLACEHOLDER}}`` with the exact value.
        4. Any unresolved placeholder becomes ``NOT FOUND: {{NAME}}``.
        """
        template = self.load_template(role)
        substitution = _build_substitution(variables)
        return _substitute(template, substitution)

    def render_from_text(self, template_text: str, variables: RoleVariables) -> str:
        """Render an arbitrary template text (not loaded from package data).

        Useful for testing or when the template comes from a custom path.
        """
        substitution = _build_substitution(variables)
        return _substitute(template_text, substitution)

    def list_roles(self) -> list[str]:
        """Return all role names that have templates in package data."""
        return sorted(_ROLE_TO_TEMPLATE.keys())

    def find_unresolved(self, rendered: str) -> list[str]:
        """Return placeholder names still unresolved in rendered text."""
        return _PLACEHOLDER_RE.findall(rendered)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_substitution(variables: RoleVariables) -> dict[str, str]:
    """Build a ``{PLACEHOLDER: value}`` map from a RoleVariables instance."""
    # Fill missing fields with NOT FOUND sentinels.
    filled = fill_missing(variables)

    substitution: dict[str, str] = {}
    for field in dataclass_fields(filled):
        placeholder = _FIELD_TO_PLACEHOLDER.get(field.name)
        if placeholder is None:
            continue  # Not a template variable (e.g. change_id, layer, role)
        value = getattr(filled, field.name)
        substitution[placeholder] = value

    return substitution


def _substitute(template: str, substitution: Mapping[str, str]) -> str:
    """Replace ``{{KEY}}`` tokens in ``template`` with values from ``substitution``.

    Unknown placeholders are left as-is (they become ``NOT FOUND`` if
    the value was already filled with the sentinel).
    """

    def replacer(match: re.Match) -> str:
        key = match.group(1)
        return substitution.get(key, match.group(0))

    return _PLACEHOLDER_RE.sub(replacer, template)


__all__ = ["TemplateRenderer"]
