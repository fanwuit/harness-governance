"""Tests for the CLI shell itself."""

from __future__ import annotations

from click.testing import CliRunner

from harness_governance.cli import cli, main


def test_help_lists_all_subcommands() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    for sub in ("init", "governed-start", "packet"):
        assert sub in result.output


def test_version_is_reported() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "0.5.1" in result.output


def test_packet_help_lists_subcommands() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["packet", "--help"])
    assert result.exit_code == 0
    assert "init" in result.output
    assert "check" in result.output


def test_main_propagates_failure_exit_code(tmp_repo) -> None:
    """``main()`` must return non-zero when a subcommand exits non-zero."""
    from harness_governance.cli import main as cli_main
    from tests.conftest import seed_session

    seed_session(tmp_repo)
    rc = cli_main(["--project-root", str(tmp_repo), "packet", "init", "demo"])
    assert rc == 0
    rc = cli_main(["--project-root", str(tmp_repo), "packet", "check"])
    # Fresh packet must fail until contracts/verification are filled.
    assert rc == 1