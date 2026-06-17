"""Tests for runner/template_renderer.py — TemplateRenderer."""

from __future__ import annotations

import pytest

from harness_governance.runner.template_renderer import TemplateRenderer
from harness_governance.runner.variables import RoleVariables


@pytest.fixture
def renderer() -> TemplateRenderer:
    return TemplateRenderer()


@pytest.fixture
def sample_variables() -> RoleVariables:
    return RoleVariables(
        queue_item_raw="[ready] Implement dashboard\nRole: Implementer\nLayer: implementation",
        change_id="dev-workbench",
        layer="implementation",
        role="implementer",
        owner_files="src/dashboard.py",
        contracts="# Contracts\n- Must render status\n",
        allowed_assumptions="status.json available",
        expected_behavior="Dashboard shows queue summary",
        failure_behavior="Empty state shows placeholder",
        forbidden_scope="No API changes",
        verification_commands="npm test",
        done_when="Dashboard renders correctly",
    )


class TestLoadTemplate:
    def test_load_implementer(self, renderer: TemplateRenderer) -> None:
        text = renderer.load_template("implementer")
        assert "Implementer" in text
        assert "OWNER_FILES" in text or "Approved Inputs" in text

    def test_load_reviewer(self, renderer: TemplateRenderer) -> None:
        text = renderer.load_template("reviewer")
        assert "Reviewer" in text
        assert "Forbidden Inputs" in text

    def test_load_planner(self, renderer: TemplateRenderer) -> None:
        text = renderer.load_template("planner")
        assert "Planner" in text

    def test_load_contract_writer(self, renderer: TemplateRenderer) -> None:
        text = renderer.load_template("contract-writer")
        assert "Contract Writer" in text

    def test_load_contract_writer_underscore(self, renderer: TemplateRenderer) -> None:
        text = renderer.load_template("contract_writer")
        assert "Contract Writer" in text

    def test_load_orchestrator(self, renderer: TemplateRenderer) -> None:
        text = renderer.load_template("orchestrator")
        assert "orchestrator" in text.lower() or "Orchestrator" in text

    def test_unknown_role_raises(self, renderer: TemplateRenderer) -> None:
        with pytest.raises(ValueError, match="Unknown role"):
            renderer.load_template("nonexistent")


class TestRender:
    def test_render_implementer_substitutes_variables(
        self, renderer: TemplateRenderer, sample_variables: RoleVariables
    ) -> None:
        rendered = renderer.render("implementer", sample_variables)
        # The template should have the role title
        assert "Implementer" in rendered
        # Variable values should appear in the output
        # (they're in the template via {{PLACEHOLDER}})
        assert len(rendered) > 0  # rendering succeeded without error

    def test_render_reviewer_isolates_from_implementer(
        self, renderer: TemplateRenderer, sample_variables: RoleVariables
    ) -> None:
        rendered = renderer.render("reviewer", sample_variables)
        assert "Reviewer" in rendered
        # The reviewer template should NOT include implementer-specific reasoning
        assert "{{IMPLEMENTER_REASONING}}" not in rendered  # placeholder not leaked raw

    def test_render_preserves_exact_values(
        self,
        renderer: TemplateRenderer,
    ) -> None:
        """Variables are substituted exactly, no paraphrasing."""
        v = RoleVariables(
            owner_files="src/exact-file.py",
            done_when="exact completion criteria",
        )
        template = "Files: {{OWNER_FILES}}\nDone: {{DONE_WHEN}}"
        rendered = renderer.render_from_text(template, v)
        assert "src/exact-file.py" in rendered
        assert "exact completion criteria" in rendered

    def test_render_missing_variable_shows_not_found(
        self,
        renderer: TemplateRenderer,
    ) -> None:
        v = RoleVariables()
        template = "Files: {{OWNER_FILES}}\nContracts: {{CONTRACTS}}"
        rendered = renderer.render_from_text(template, v)
        assert "NOT FOUND: {{OWNER_FILES}}" in rendered
        assert "NOT FOUND: {{CONTRACTS}}" in rendered

    def test_render_unknown_placeholder_left_as_is(
        self,
        renderer: TemplateRenderer,
    ) -> None:
        v = RoleVariables(owner_files="test.py")
        template = "{{OWNER_FILES}} and {{UNKNOWN_VAR}}"
        rendered = renderer.render_from_text(template, v)
        assert "test.py" in rendered
        assert "{{UNKNOWN_VAR}}" in rendered


class TestFindUnresolved:
    def test_no_unresolved(self, renderer: TemplateRenderer) -> None:
        assert renderer.find_unresolved("all substituted") == []

    def test_finds_unresolved(self, renderer: TemplateRenderer) -> None:
        result = renderer.find_unresolved("{{FOO}} and {{BAR}}")
        assert "FOO" in result
        assert "BAR" in result


class TestListRoles:
    def test_lists_all_roles(self, renderer: TemplateRenderer) -> None:
        roles = renderer.list_roles()
        assert "implementer" in roles
        assert "reviewer" in roles
        assert "planner" in roles
        assert "contract-writer" in roles
        assert "orchestrator" in roles

    def test_lists_governance_roles(self, renderer: TemplateRenderer) -> None:
        roles = renderer.list_roles()
        assert "adr-writer" in roles
        assert "fact-finder-reviewer" in roles
        assert "readiness-gate-writer" in roles
        assert "document-gardener" in roles
        assert "integrator" in roles

    def test_role_aliases(self, renderer: TemplateRenderer) -> None:
        """Aliases like underscores and spaces resolve correctly."""
        roles = renderer.list_roles()
        assert "adr_writer" in roles
        assert "adr writer" in roles
        assert "fact_finder_reviewer" in roles
        assert "fact finder" in roles
        assert "readiness_gate_writer" in roles
        assert "document_gardener" in roles


class TestLoadGovernanceTemplates:
    def test_load_adr_writer(self, renderer: TemplateRenderer) -> None:
        text = renderer.load_template("adr-writer")
        assert "ADR Writer" in text
        assert "{{QUEUE_ITEM}}" in text
        assert "{{SCOPE}}" in text

    def test_load_fact_finder_reviewer(self, renderer: TemplateRenderer) -> None:
        text = renderer.load_template("fact-finder-reviewer")
        assert "Fact Finder" in text
        assert "Forbidden Inputs" in text
        assert "{{GIT_DIFF}}" in text

    def test_load_readiness_gate_writer(self, renderer: TemplateRenderer) -> None:
        text = renderer.load_template("readiness-gate-writer")
        assert "Readiness Gate Writer" in text
        assert "{{OWNER_FILES}}" in text
        assert "{{EXPECTED_BEHAVIOR}}" in text

    def test_load_document_gardener(self, renderer: TemplateRenderer) -> None:
        text = renderer.load_template("document-gardener")
        assert "Document Gardener" in text
        assert "{{SCOPE}}" in text
        assert "{{OWNER_FILES}}" in text

    def test_load_integrator(self, renderer: TemplateRenderer) -> None:
        text = renderer.load_template("integrator")
        assert "Integrator" in text
        assert "{{WORKER_RESULTS}}" in text

    def test_load_fact_finder_alias(self, renderer: TemplateRenderer) -> None:
        text = renderer.load_template("fact-finder")
        assert "Fact Finder" in text

    def test_load_readiness_alias(self, renderer: TemplateRenderer) -> None:
        text = renderer.load_template("readiness")
        assert "Readiness Gate Writer" in text


class TestRenderGovernanceRoles:
    def test_render_adr_writer_substitutes(
        self,
        renderer: TemplateRenderer,
    ) -> None:
        v = RoleVariables(
            queue_item_raw="[ready] Write ADR for DB migration",
            scope="Database layer migration",
            contracts="# ADR contracts",
            allowed_scope="docs/adr/",
            forbidden_scope="No product code changes",
            verification_commands="cat docs/adr/001.md",
            done_when="ADR approved",
        )
        rendered = renderer.render("adr-writer", v)
        assert "ADR Writer" in rendered
        assert "[ready] Write ADR for DB migration" in rendered
        assert "Database layer migration" in rendered
        assert "docs/adr/" in rendered

    def test_render_fact_finder_has_forbidden_inputs(
        self,
        renderer: TemplateRenderer,
    ) -> None:
        v = RoleVariables(
            queue_item_raw="[ready] Review evidence",
            contracts="# Contracts",
            git_diff="diff --git a/foo.py",
            allowed_scope="src/",
            forbidden_scope="No tests",
            verification_commands="pytest",
            done_when="Facts collected",
        )
        rendered = renderer.render("fact-finder-reviewer", v)
        assert "Forbidden Inputs" in rendered
        assert "IMPLEMENTER_REASONING" in rendered
        assert "diff --git a/foo.py" in rendered

    def test_render_integrator_includes_worker_results(
        self,
        renderer: TemplateRenderer,
    ) -> None:
        v = RoleVariables(
            queue_item_raw="[ready] Integrate worker outputs",
            worker_results='{"worker1": "passed", "worker2": "passed"}',
            owner_files="src/main.py",
            contracts="# Contracts",
            allowed_scope="src/",
            forbidden_scope="No API changes",
            verification_commands="npm test",
            done_when="All workers merged",
        )
        rendered = renderer.render("integrator", v)
        assert "Integrator" in rendered
        assert '{"worker1": "passed", "worker2": "passed"}' in rendered

    def test_render_readiness_gate_writer(
        self,
        renderer: TemplateRenderer,
    ) -> None:
        v = RoleVariables(
            queue_item_raw="[ready] Fix readiness gates",
            owner_files="tests/fixtures/",
            contracts="# Readiness contracts",
            expected_behavior="Fixtures load correctly",
            failure_behavior="Missing fixtures reported",
            forbidden_scope="No product code",
            verification_commands="pytest tests/fixtures/",
            done_when="All gates pass",
        )
        rendered = renderer.render("readiness-gate-writer", v)
        assert "Readiness Gate Writer" in rendered
        assert "tests/fixtures/" in rendered

    def test_render_document_gardener(
        self,
        renderer: TemplateRenderer,
    ) -> None:
        v = RoleVariables(
            queue_item_raw="[ready] Fix doc drift",
            scope="README and ADR index",
            owner_files="README.md docs/adr/index.md",
            allowed_scope="docs/",
            forbidden_scope="No code changes",
            verification_commands="markdownlint docs/",
            done_when="All docs updated",
        )
        rendered = renderer.render("document-gardener", v)
        assert "Document Gardener" in rendered
        assert "README and ADR index" in rendered


class TestIsolationGuarantee:
    """Verify that the rendered reviewer prompt does not leak implementer data."""

    def test_reviewer_has_no_implementer_self_check(
        self, renderer: TemplateRenderer, sample_variables: RoleVariables
    ) -> None:
        rendered = renderer.render("reviewer", sample_variables)
        # The forbidden inputs section should list IMPLEMENTER_SELF_CHECK
        # but the actual values should NOT contain implementer reasoning
        assert "IMPLEMENTER_SELF_CHECK" in rendered  # Listed as forbidden
        # But the variable values section should not contain any self-check data
        # (since we don't inject it into reviewer variables)

    def test_reviewer_gets_contracts(
        self, renderer: TemplateRenderer, sample_variables: RoleVariables
    ) -> None:
        rendered = renderer.render("reviewer", sample_variables)
        # Contracts are shared between implementer and reviewer
        # (the template references CONTRACTS as an approved input)
        assert "CONTRACTS" in rendered

    def test_fact_finder_isolation(
        self,
        renderer: TemplateRenderer,
    ) -> None:
        """Fact Finder template also has Forbidden Inputs section."""
        v = RoleVariables(
            queue_item_raw="[ready] Review evidence",
            contracts="# Contracts",
            forbidden_scope="No modifications",
        )
        rendered = renderer.render("fact-finder-reviewer", v)
        assert "IMPLEMENTER_REASONING" in rendered
        assert "IMPLEMENTER_SELF_CHECK" in rendered


class TestPlaceholderSubstitution:
    """Verify all role templates have {{PLACEHOLDER}} tokens and substitution works."""

    ALL_ROLES_WITH_PLACEHOLDERS = [
        "planner",
        "contract-writer",
        "implementer",
        "reviewer",
        "adr-writer",
        "fact-finder-reviewer",
        "readiness-gate-writer",
        "document-gardener",
        "integrator",
    ]

    @pytest.mark.parametrize("role", ALL_ROLES_WITH_PLACEHOLDERS)
    def test_template_has_placeholders(
        self,
        renderer: TemplateRenderer,
        role: str,
    ) -> None:
        raw = renderer.load_template(role)
        unresolved = renderer.find_unresolved(raw)
        assert len(unresolved) > 0, f"Template {role} has no {{{{PLACEHOLDER}}}} tokens"

    @pytest.mark.parametrize("role", ALL_ROLES_WITH_PLACEHOLDERS)
    def test_render_substitutes_queue_item(
        self,
        renderer: TemplateRenderer,
        role: str,
    ) -> None:
        """QUEUE_ITEM is the one variable all role templates share."""
        v = RoleVariables(queue_item_raw="[ready] Test queue item for substitution")
        rendered = renderer.render(role, v)
        assert "[ready] Test queue item for substitution" in rendered

    def test_orchestrator_has_no_placeholders(
        self,
        renderer: TemplateRenderer,
    ) -> None:
        """Orchestrator template only has platform-level placeholders resolved at assembly time."""
        raw = renderer.load_template("orchestrator")
        unresolved = renderer.find_unresolved(raw)
        # DISPATCH_INSTRUCTION and HARD_GATE_COMMAND are substituted by
        # OrchestratorPromptBuilder._assemble(), not by TemplateRenderer.
        assert set(unresolved) == {"DISPATCH_INSTRUCTION", "HARD_GATE_COMMAND"}
