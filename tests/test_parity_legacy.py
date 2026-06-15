"""Smoke tests for the CLI command tree.

Legacy parity tests (comparing Python CLI output against the original
.mjs / .sh scripts) were removed after the legacy scripts were deleted.
The Python CLI's behavior is now fully covered by the dedicated unit
and integration tests in the rest of the test suite.
"""

from __future__ import annotations

from harness_governance.cli import cli


def test_cli_help_lists_all_subcommands() -> None:
    """Smoke test for the top-level command tree."""
    from click.testing import CliRunner

    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    for sub in (
        "init",
        "governed-start",
        "packet",
        "entry",
        "plan",
        "check",
        "status",
        "verify",
        "review",
        "config",
        "runner",
    ):
        assert sub in result.output, f"missing subcommand in --help: {sub}"
