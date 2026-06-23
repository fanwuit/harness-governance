# Brainstorming: Executor Removal and Native Subagent Handoff

## Option A: Remove Core Executors And Build Native Handoff

- Best when: harness core must remain platform-neutral and all governed subagent work should use platform-native delegation.
- Benefit: removes the semantic mismatch where `adapter: subagent` can become an external process; makes native handoff auditable and gateable.
- Cost: breaking change for users of `runner start --executor subprocess` and `--executor codex`.
- Risk: old CI or automation workflows must migrate instead of receiving a compatibility fallback.
- Evidence needed: updated CLI tests proving handoff request, spawn record, parse completion, and gate checks replace executor execution.

## Option B: Keep Subprocess As Compatibility Fallback

- Best when: preserving old CI/headless workflows is more important than a clean platform-neutral model.
- Benefit: lower migration burden for users who depend on external process runners.
- Cost: keeps two execution meanings in one system: native subagent and subprocess worker.
- Risk: future declarations can again route native subagent work through external processes.
- Evidence needed: strict policy and tests proving fallback can never be used for capability-tier subagent routing.

## Option C: Move Platform Executors To Plugins

- Best when: platform-specific external runners are still valuable, but should not live in harness core.
- Benefit: keeps core clean while leaving a possible extension path.
- Cost: requires plugin packaging and migration guidance outside this change.
- Risk: plugin semantics could still confuse native subagent handoff if exposed as a role adapter.
- Evidence needed: a plugin boundary contract and clear naming that separates external process runners from native handoff.

## Recommendation

Choose Option A for this change.

Option C may be deferred as a future extension only if there is real demand. Option B is excluded because it preserves the core architectural ambiguity this change is meant to remove.

## Must Do

- Remove core platform/process executor paths from governed runner dispatch.
- Remove `subprocess` and platform CLI adapters from capability-tier routing.
- Add native handoff request, spawn record, parse completion, and gate validation records.
- Update tests and docs to treat native subagent execution as an external platform action recorded by harness, not executed by harness.

## Deferred

- Plugin-based platform-specific external runners.
- Migration tooling for old CI jobs.

## Excluded

- Keeping `subprocess` as a fallback for governed subagent dispatch.
- Keeping Codex CLI or other platform CLIs in harness core under a different name.
- Treating brainstorming output as an implementation plan.
