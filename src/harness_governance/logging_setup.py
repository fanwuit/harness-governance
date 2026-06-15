"""Logging configuration for ``harness-governance``.

All diagnostic output goes through Python's :mod:`logging` module to
**stderr** so that command stdout stays clean for machine-readable or
user-facing results.

Three verbosity tiers are supported via the ``--verbose`` / ``--debug``
global CLI flags:

* *normal*  — WARNING and above (silent on success).
* *verbose* — INFO and above  (one-line summaries of key actions).
* *debug*   — DEBUG and above (detailed traces for troubleshooting).

Call :func:`setup_logging` once from the top-level ``cli`` group before
any sub-command runs.
"""

from __future__ import annotations

import logging
import sys

#: Canonical logger name used throughout the package.
LOGGER_NAME = "harness"

_NORMAL_FMT = "%(message)s"
_VERBOSE_FMT = "%(levelname)-8s %(message)s"
_DEBUG_FMT = "%(asctime)s %(levelname)-8s [%(name)s] %(message)s"
_DATE_FMT = "%H:%M:%S"


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a child of the ``harness`` logger.

    Parameters
    ----------
    name:
        Optional sub-logger name.  ``get_logger("config")`` returns
        ``logging.getLogger("harness.config")``.
    """
    base = logging.getLogger(LOGGER_NAME)
    if name:
        return base.getChild(name)
    return base


def setup_logging(*, verbose: bool = False, debug: bool = False) -> None:
    """Configure the ``harness`` logger for the current invocation.

    Parameters
    ----------
    verbose:
        Enable INFO-level output.
    debug:
        Enable DEBUG-level output (implies verbose formatting).

    Raises
    ------
    ValueError
        If both *verbose* and *debug* are ``True``.
    """
    if verbose and debug:
        raise ValueError("--verbose and --debug are mutually exclusive")

    logger = logging.getLogger(LOGGER_NAME)

    # Remove handlers from previous invocations (e.g. test runs).
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

    handler = logging.StreamHandler(sys.stderr)

    if debug:
        logger.setLevel(logging.DEBUG)
        handler.setFormatter(logging.Formatter(_DEBUG_FMT, datefmt=_DATE_FMT))
    elif verbose:
        logger.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter(_VERBOSE_FMT))
    else:
        logger.setLevel(logging.WARNING)
        handler.setFormatter(logging.Formatter(_NORMAL_FMT))

    logger.addHandler(handler)

    # Prevent messages from propagating to the root logger, which may
    # have its own handlers in some embedding scenarios.
    logger.propagate = False


__all__ = ["LOGGER_NAME", "get_logger", "setup_logging"]
