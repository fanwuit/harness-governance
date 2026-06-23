# Architecture: Executor Removal and Native Subagent Handoff

## Boundary Diagram

```text
Queue item + tiers.json + change packet + role template
        |
        v
Harness core: prepare native handoff
  - resolve role/tier declaration
  - render prompt
  - write request JSON
  - write prompt file and prompt hash
        |
        v
Main agent / platform boundary
  - platform-native subagent spawn happens outside harness CLI
  - platform returns or exposes native agent id
        |
        v
Harness core: record native spawn
  - request id
  - native agent id
  - status
        |
        v
Native subagent result JSON
        |
        v
Harness core: parse result
  - correlate request, prompt hash, native agent id
  - record verdict and verification summary
        |
        v
Verification gate
  - render record exists
  - handoff request exists
  - spawn record exists
  - parse completion exists
  - verdict is acceptable or queue is explicitly blocked/returned
```

## Firm Boundaries

- Harness core does not execute platform agents or subagents.
- Harness core does not contain platform CLI executors.
- Native subagent spawn is owned by the main agent and the active platform.
- Harness core owns request preparation, spawn recording, result parsing, and gate validation.

## Negotiable Boundaries

- Whether native lifecycle records are stored in `.harness/skill-chains/*.ndjson`, a unified invocation log, or a dedicated native handoff log.
- Whether the adapter label remains `subagent` or is renamed to `native-subagent`.
- Whether `runner start` remains as a prompt/orchestrator entry or is deprecated in favor of explicit native handoff commands.

## Component Responsibilities

| Component | Responsibility |
|---|---|
| `tiers.json` declarations | Declare platform, role, required tier, adapter, and opaque model label. |
| Queue item / change packet | Provide role, session, queue id, scope, contracts, verification commands, forbidden scope, and done criteria. |
| Prompt renderer | Render role prompts from structured queue and packet inputs. |
| Native handoff preparation | Persist request JSON, prompt file, prompt hash, and prepared status. |
| Main agent / platform | Spawn the native subagent outside harness CLI and provide a native agent id. |
| Spawn recorder | Persist request id, role, session id, native agent id, and spawn status. |
| Result parser | Parse structured JSON result and correlate it with request, prompt hash, role, tier, model, and agent id. |
| Verification gate | Validate the full handoff lifecycle and reject unacceptable verdicts unless queue state records a block/return. |

## Ownership

| Area | Owner |
|---|---|
| Declaration parsing, prompt rendering, lifecycle records, parser, gate | harness core |
| Native subagent spawning and native agent id generation | main agent / platform |
| `tiers.json`, queue item, change packet content | derived project |
| Structured review/verification JSON result | reviewer/verifier subagent |

## Data Flow

1. Harness reads the queue item, `tiers.json`, role template, and change packet.
2. `prepare-native` renders the prompt, writes the prompt file, computes its hash, and writes a prepared handoff request.
3. The main agent reads the prompt file and spawns a platform-native subagent using platform capability outside harness CLI.
4. `record-native-spawn` records the native agent id, request id, role, session id, and status.
5. The native subagent writes or returns structured JSON.
6. `parse-result` parses the JSON and records completion metadata, verdict, verification status, findings count, prompt hash, role, tier, model label, request id, and native agent id.
7. `gate check verification` validates the complete lifecycle and acceptable verdict semantics.

## ADR Candidates

1. Native handoff lifecycle as the only core governed subagent dispatch path.
   - Rationale: this freezes the boundary that harness core prepares and validates native subagent work but does not execute platform agents.
2. Removal of core platform/process agent executors.
   - Rationale: this is a breaking long-lived public CLI boundary and should be explicit.
3. Native handoff record schema and persistence location.
   - Rationale: gate behavior and audit compatibility depend on stable lifecycle records.
4. Adapter naming: `subagent` versus `native-subagent`.
   - Rationale: naming affects `tiers.json` compatibility and whether the field clearly excludes subprocess semantics.
