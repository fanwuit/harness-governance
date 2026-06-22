# Tasks

## Owner Files

- [x] Remove platform/process executor code paths from governed runner core.
- [x] Add native handoff prepare/record/parse lifecycle commands.
- [x] Gate verification on complete native lifecycle records.
- [x] Add tests for request generation, spawn recording, parse correlation, role mismatch rejection, and gate lifecycle.

- `src/harness_governance/commands/runner.py`
- `src/harness_governance/runner/native_handoff.py`
- `src/harness_governance/hard_gates.py`
- `src/harness_governance/state_machine/gates.py`
- `tests/test_native_subagent_handoff.py`

## Allowed Scope

Native subagent handoff protocol, runner CLI lifecycle commands, native lifecycle gate integration, and matching tests/docs.

## Forbidden Scope

Unrelated platform UI behavior, unrelated verification subprocess helpers, and unrelated governance sessions.

## Verification Commands

`pytest -q`

## Done When

The runner no longer exposes platform/process executor paths for governed subagent dispatch, and native handoff prepare/record/parse/gate behavior is tested.
