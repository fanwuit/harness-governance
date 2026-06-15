"""Tests for ``harness config {show, set, validate}`` subcommands."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from harness_governance.cli import cli


# -- helpers -----------------------------------------------------------------


def _init_config(runner: CliRunner, tmp_repo: Path) -> None:
    """Run ``harness config init`` to create a baseline config."""
    result = runner.invoke(
        cli, ["--project-root", str(tmp_repo), "config", "init"]
    )
    assert result.exit_code == 0, result.output


# -- config show -------------------------------------------------------------


class TestConfigShow:
    def test_show_displays_fields(self, tmp_repo: Path) -> None:
        runner = CliRunner()
        _init_config(runner, tmp_repo)
        result = runner.invoke(
            cli, ["--project-root", str(tmp_repo), "config", "show"]
        )
        assert result.exit_code == 0, result.output
        assert "agent_platform" in result.output
        assert "queue_file" in result.output
        assert "check_frequency" in result.output

    def test_show_json_output(self, tmp_repo: Path) -> None:
        runner = CliRunner()
        _init_config(runner, tmp_repo)
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_repo), "--json", "config", "show"],
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert "agent_platform" in data
        assert "queue_file" in data

    def test_show_uses_defaults_when_no_file(self, tmp_repo: Path) -> None:
        """show should work even without a config file (using defaults)."""
        runner = CliRunner()
        result = runner.invoke(
            cli, ["--project-root", str(tmp_repo), "config", "show"]
        )
        assert result.exit_code == 0, result.output
        # Defaults should still show agent_platform
        assert "agent_platform" in result.output


# -- config set --------------------------------------------------------------


class TestConfigSet:
    def test_set_single_field(self, tmp_repo: Path) -> None:
        runner = CliRunner()
        _init_config(runner, tmp_repo)
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_repo), "config", "set", "check_frequency=always"],
        )
        assert result.exit_code == 0, result.output
        assert "check_frequency" in result.output

        # Verify the file was updated.
        text = (tmp_repo / ".harness" / "config.toml").read_text(encoding="utf-8")
        assert 'check_frequency = "always"' in text

    def test_set_multiple_fields(self, tmp_repo: Path) -> None:
        runner = CliRunner()
        _init_config(runner, tmp_repo)
        result = runner.invoke(
            cli,
            [
                "--project-root", str(tmp_repo),
                "config", "set",
                "check_frequency=phase-closeout",
                "queue_file=TODO.md",
            ],
        )
        assert result.exit_code == 0, result.output

    def test_set_unknown_field_rejected(self, tmp_repo: Path) -> None:
        runner = CliRunner()
        _init_config(runner, tmp_repo)
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_repo), "config", "set", "bogus_field=xyz"],
        )
        assert result.exit_code != 0

    def test_set_bad_format_rejected(self, tmp_repo: Path) -> None:
        runner = CliRunner()
        _init_config(runner, tmp_repo)
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_repo), "config", "set", "no_equals_sign"],
        )
        assert result.exit_code != 0

    def test_set_without_config_file_fails(self, tmp_repo: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_repo), "config", "set", "check_frequency=always"],
        )
        assert result.exit_code != 0

    def test_set_json_output(self, tmp_repo: Path) -> None:
        runner = CliRunner()
        _init_config(runner, tmp_repo)
        result = runner.invoke(
            cli,
            [
                "--project-root", str(tmp_repo),
                "--json", "config", "set",
                "check_frequency=always",
            ],
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["valid"] is True
        assert "check_frequency" in data["updated"]


# -- config validate ---------------------------------------------------------


class TestConfigValidate:
    def test_validate_passes_with_valid_config(self, tmp_repo: Path) -> None:
        runner = CliRunner()
        _init_config(runner, tmp_repo)
        result = runner.invoke(
            cli, ["--project-root", str(tmp_repo), "config", "validate"]
        )
        assert result.exit_code == 0, result.output

    def test_validate_fails_with_bad_config(self, tmp_repo: Path) -> None:
        runner = CliRunner()
        # Write an invalid config (unknown field).
        harness_dir = tmp_repo / ".harness"
        harness_dir.mkdir(parents=True)
        (harness_dir / "config.toml").write_text(
            'unknown_field = "oops"\n', encoding="utf-8"
        )
        result = runner.invoke(
            cli, ["--project-root", str(tmp_repo), "config", "validate"]
        )
        assert result.exit_code != 0

    def test_validate_without_config_file_fails(self, tmp_repo: Path) -> None:
        runner = CliRunner()
        result = runner.invoke(
            cli, ["--project-root", str(tmp_repo), "config", "validate"]
        )
        assert result.exit_code != 0

    def test_validate_json_output_valid(self, tmp_repo: Path) -> None:
        runner = CliRunner()
        _init_config(runner, tmp_repo)
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_repo), "--json", "config", "validate"],
        )
        assert result.exit_code == 0, result.output
        data = json.loads(result.output)
        assert data["valid"] is True

    def test_validate_json_output_invalid(self, tmp_repo: Path) -> None:
        runner = CliRunner()
        harness_dir = tmp_repo / ".harness"
        harness_dir.mkdir(parents=True)
        (harness_dir / "config.toml").write_text(
            'bogus = "x"\n', encoding="utf-8"
        )
        result = runner.invoke(
            cli,
            ["--project-root", str(tmp_repo), "--json", "config", "validate"],
        )
        assert result.exit_code != 0
        data = json.loads(result.output)
        assert data["valid"] is False
