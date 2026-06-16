"""harness-governance: AI engineering governance CLI.

Public entry points are the ``harness`` console script (see ``cli.main``)
and the :class:`harness_governance.state_machine.engine.StateMachineEngine`.

The package is organized into the following submodules:

* :mod:`harness_governance.state_machine` — 12-layer enum, 9 transition rules,
  state engine, Fast/Trivial/Governed classification.
* :mod:`harness_governance.models` — Pydantic schemas for all CLI I/O.
* :mod:`harness_governance.commands` — one module per CLI subcommand.
* :mod:`harness_governance.config` — ``.harness/config.toml`` loader and
  default-path constants.
* :mod:`harness_governance.file_ops` — Markdown file read/write helpers.
* :mod:`harness_governance.runner` — autonomous runner (added in Phase B).
* :mod:`harness_governance.session` — governance session state and storage.
* :mod:`harness_governance.data` — packaged templates, references, fixtures.
"""

__version__ = "0.4.0"