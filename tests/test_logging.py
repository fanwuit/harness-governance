"""Tests for the logging_setup module and CLI --verbose/--debug flags."""

from __future__ import annotations

import logging

import pytest
from click.testing import CliRunner

from harness_governance.cli import cli
from harness_governance.logging_setup import LOGGER_NAME, get_logger, setup_logging


# -- setup_logging -----------------------------------------------------------


class TestSetupLogging:
    def test_normal_mode_sets_warning_level(self) -> None:
        setup_logging()
        logger = logging.getLogger(LOGGER_NAME)
        assert logger.level == logging.WARNING

    def test_verbose_mode_sets_info_level(self) -> None:
        setup_logging(verbose=True)
        logger = logging.getLogger(LOGGER_NAME)
        assert logger.level == logging.INFO

    def test_debug_mode_sets_debug_level(self) -> None:
        setup_logging(debug=True)
        logger = logging.getLogger(LOGGER_NAME)
        assert logger.level == logging.DEBUG

    def test_mutually_exclusive_raises(self) -> None:
        with pytest.raises(ValueError, match="mutually exclusive"):
            setup_logging(verbose=True, debug=True)

    def test_handler_count_stable_after_repeated_calls(self) -> None:
        setup_logging()
        setup_logging(verbose=True)
        setup_logging(debug=True)
        logger = logging.getLogger(LOGGER_NAME)
        assert len(logger.handlers) == 1

    def test_propagate_is_false(self) -> None:
        setup_logging()
        logger = logging.getLogger(LOGGER_NAME)
        assert logger.propagate is False


# -- get_logger --------------------------------------------------------------


class TestGetLogger:
    def test_returns_harness_logger(self) -> None:
        lg = get_logger()
        assert lg.name == LOGGER_NAME

    def test_child_logger(self) -> None:
        lg = get_logger("config")
        assert lg.name == f"{LOGGER_NAME}.config"


# -- CLI flags ---------------------------------------------------------------


class TestCLIVerbosityFlags:
    def test_verbose_flag_accepted(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["--verbose", "--help"])
        assert result.exit_code == 0

    def test_debug_flag_accepted(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["--debug", "--help"])
        assert result.exit_code == 0

    def test_verbose_and_debug_rejected(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["--verbose", "--debug", "status"])
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower()

    def test_verbose_short_flag(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["-v", "--help"])
        assert result.exit_code == 0

    def test_debug_short_flag(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["-d", "--help"])
        assert result.exit_code == 0

    def test_help_shows_verbose_and_debug_options(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert "--verbose" in result.output
        assert "--debug" in result.output
