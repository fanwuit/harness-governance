# Contract: Native Subagent Handoff Runner

## Behaviour

1. **Core executor removal**
   - System MUST remove core public runner execution paths for platform/process agent executors.
   - System MUST NOT expose governed runner dispatch through Codex CLI, subprocess, or an executor registry.
   - Verified by: focused grep assertions and runner CLI tests.

2. **Native handoff preparation**
   - System MUST provide `harness runner prepare-native --role <role> --queue <queue-id> --session-id <session-id>`.
   - System MUST render the role prompt from structured queue/change-packet inputs.
   - System MUST write a handoff request JSON and prompt file.
   - Request JSON MUST include `sessionId`, `queueId`, `role`, `requiredTier`, `actualTier`, `platform`, `adapter`, `modelLabel`, `promptPath`, `promptSha256`, and `status: prepared`.
   - Verified by: runner CLI tests.

3. **Native adapter semantics**
   - `adapter=subagent` MUST mean platform-native subagent handoff.
   - `adapter=subagent` MUST NOT instantiate or execute a subprocess.
   - Adapter values such as `subprocess`, `codex-cli`, or unknown executor names MUST be rejected for governed native handoff.
   - Verified by: declaration/runner tests.

4. **Native spawn recording**
   - System MUST provide `harness runner record-native-spawn --session-id <session-id> --role <role> --agent-id <agent-id> --request-id <request-id> --status spawned`.
   - System MUST persist a spawn record correlated by session id, request id, role, and native agent id.
   - System MUST fail when the referenced prepared handoff request does not exist.
   - Verified by: runner CLI tests.

5. **Result parsing and completion record**
   - `harness runner parse-result` MUST accept `--session-id`, `--agent-id`, and `--request-id`.
   - Completion records MUST include prompt hash, native agent id, request id, role, tier, model label, platform, adapter, verdict, `verificationPassed`, `findingsCount`, and completed status.
   - System MUST fail when the request or spawn record cannot be correlated.
   - Verified by: parser and runner CLI tests.

6. **Verification gate lifecycle**
   - Verification gate MUST require a complete lifecycle: render record, native handoff request, native spawn record, parse-result completion record, and acceptable verdict.
   - Verdict `reject` or `insufficient_evidence` MUST NOT pass verification unless queue state explicitly records a block or return-to-implementer.
   - Verified by: gate tests.

7. **Prompt completeness**
   - Reviewer/verifier render or prepare MUST fail if `FORBIDDEN_SCOPE`, `VERIFICATION_COMMANDS`, or `DONE_WHEN` would render as `NOT FOUND`.
   - Verified by: render and prepare tests.

8. **Role isolation**
   - Implementation, review, and verification records MUST remain distinguishable by role, request id, and native agent id.
   - Reviewer/verifier prompts MUST NOT receive implementer reasoning, implementer self-checks, main-window opinion, or chat-history summaries.
   - Verified by: prompt isolation tests and handoff lifecycle records.

## Alignment Anchor Fields

| Field | Type | Required | Description |
|---|---|---|---|
| `role` | str | yes | Role being handed off or completed. |
| `platform` | str | yes | Declared agent platform. |
| `adapter` | str | yes | Native adapter label. |
| `model_label` | str | no | Opaque model label from declaration. |

## Record Fields

Native handoff request fields:

- `sessionId`: string, required, governance session id.
- `queueId`: string, required, queue item id or stable queue key.
- `requestId`: string, required, unique native handoff request id.
- `role`: string, required, role being handed off.
- `requiredTier`: string, required, required capability tier.
- `actualTier`: string, required, actual capability tier selected for the role.
- `platform`: string, required, declared agent platform.
- `adapter`: string, required, native adapter label.
- `modelLabel`: string, optional, opaque model label from declaration.
- `promptPath`: string, required, workspace-relative prompt path.
- `promptSha256`: string, required, SHA-256 of the exact prompt file contents.
- `status`: string, required, initially `prepared`.

Native spawn record fields:

- `sessionId`: string, required, governance session id.
- `requestId`: string, required, prepared handoff request id.
- `role`: string, required, spawned role.
- `agentId`: string, required, platform-native subagent id.
- `status`: string, required, normally `spawned`.
- `recordedAt`: string, required, ISO timestamp.

Native completion record fields:

- `sessionId`: string, required, governance session id.
- `requestId`: string, required, prepared handoff request id.
- `agentId`: string, required, platform-native subagent id.
- `role`: string, required, completed role.
- `requiredTier`: string, required, required capability tier.
- `actualTier`: string, required, actual capability tier.
- `platform`: string, required, declared agent platform.
- `adapter`: string, required, native adapter label.
- `modelLabel`: string, optional, opaque model label from declaration.
- `promptSha256`: string, required, SHA-256 copied from the prepared request.
- `verdict`: string, optional, parsed reviewer/verifier verdict.
- `verificationPassed`: boolean, required, parsed verification status.
- `findingsCount`: integer, required, count of parsed findings.
- `status`: string, required, normally `completed`.
- `completedAt`: string, required, ISO timestamp.

## Failure Cases

- No queue item matches `--queue`: command fails without writing prepared request.
- Session id is missing or mismatched: command fails without writing lifecycle records.
- Role cannot be resolved: command fails.
- Declaration uses `subprocess`, `codex-cli`, or unknown executor adapter: native handoff preparation fails.
- Reviewer/verifier required field is missing: render/prepare fails.
- Spawn record references unknown request id: `record-native-spawn` fails.
- Parse references unknown request or missing spawn: `parse-result` fails.
- Completion verdict is `reject` or `insufficient_evidence`: verification gate fails unless queue is blocked/returned.

## Scope Out Of Bounds

- Keeping old external worker runner compatibility paths.
- Implementing platform-specific executor plugins.
- Removing unrelated `subprocess` usage for git/status/verification helpers.
- Having harness CLI directly spawn platform-native subagents.
- Expanding this change beyond runner/native handoff governance.
