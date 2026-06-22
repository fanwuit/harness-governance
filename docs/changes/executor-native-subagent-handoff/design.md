# Design

## Components

- `runner/native_handoff.py`: request, prompt hash, spawn, completion, and lifecycle persistence.
- `commands/runner.py`: CLI commands for `prepare-native`, `record-native-spawn`, and native-aware `parse-result`.
- `hard_gates.py` and `state_machine/gates.py`: verification gate checks for render, prepare, spawn, completion, and verdict handling.

## Lifecycle

1. Render prompt from a queue item and role.
2. Write `.harness/subagent-requests/<session>/<request-id>.json`.
3. Write `.harness/tmp/<role>-prompt.md`.
4. Host agent spawns the platform-native subagent.
5. `record-native-spawn` records the native agent id.
6. `parse-result` records completion and validates role/request/spawn correlation.
7. Verification gate validates the full lifecycle.
