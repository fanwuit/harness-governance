# Facts: Executor Removal and Native Subagent Handoff

## Confirmed Facts

- The task continues prior capability-tier/subagent routing work.
- The intended change is a breaking refactor: harness runner should move from an in-core platform/process executor model to a platform-neutral native subagent handoff protocol.
- The current scope includes deleting the old autonomous external worker loop public CLI execution path, not only deleting capability dispatch registry behavior.
- `docs/contracts/capability-tier-routing.md` states adapter dispatch/execution is out of scope for the P0 capability-tier routing contract.
- Current code contains in-core execution abstractions and platform/process executors:
  - `src/harness_governance/runner/adapters/registry.py`
  - `src/harness_governance/runner/adapters/codex_cli.py`
  - `src/harness_governance/runner/adapters/generic.py`
  - `src/harness_governance/runner/base.py`
  - `src/harness_governance/runner/loop.py`
- Current CLI code imports and exposes these execution paths through `src/harness_governance/commands/runner.py`.
- Current tests and docs reference executor behavior, including subprocess, Codex CLI, `AgentExecutor`, and `AutonomousReadyLoop`.

## Assumptions And Risks

Assumption: All supported downstream platform use cases should dispatch via native subagent capability outside harness CLI execution.

Risk: If a downstream user depends on `harness runner start --executor subprocess` or `--executor codex`, this refactor will remove that workflow and require migration to native handoff.

Assumption: Harness core should keep platform-neutral declaration parsing, prompt rendering, provenance recording, result parsing, and gate validation.

Risk: If platform-specific CLI execution remains in core, future adapter declarations can again collapse native subagent semantics into subprocess semantics.

Assumption: Existing `subprocess` usage for git/status/verification helpers is not in scope unless it participates in agent execution.

Risk: Over-broad removal of all Python `subprocess` imports would break unrelated git and verification checks.

## Evidence To Recheck During Implementation

- Runner command public options and help text.
- Tests under `tests/test_subagent_runner/`, `tests/test_commands/test_runner_cmd.py`, and `tests/test_runner.py`.
- Documentation references in `README.md`, `QUICKSTART.md`, `CHANGELOG.md`, and `src/harness_governance/data/references/runner-contract.md`.
- Capability-tier provenance examples that currently mention `codex-cli` or `subprocess`.
