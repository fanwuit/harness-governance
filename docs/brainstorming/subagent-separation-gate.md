# Subagent Separation Gate Brainstorming

## Option A: Document-Level Markdown Gate

- Best when: The project needs a P0 first version that matches the existing `user-evidence` checker pattern.
- Benefit: Low implementation risk, no new dependencies, compatible with `CheckResult` and existing CLI output.
- Cost: Relies on structured Markdown and text triggers.
- Risk: False positives and incomplete ownership provenance until richer invocation fields are enforced.
- Evidence needed: Unit tests for missing role matrix, missing invocation evidence, waiver handling, ownership violations, closure authority, CLI output, and `check all` aggregation.

## Option B: Deep Invocation Provenance Gate

- Best when: Invocation logs already provide full role ownership, file ownership, and final verdict provenance.
- Benefit: Stronger machine-verifiable separation.
- Cost: Requires runner result schema hardening and migration of existing logs.
- Risk: Could block legitimate workflows before the runner has enough structured evidence.
- Evidence needed: Runner parse-result fixtures and role handoff tests.

## Option C: Automatic Subagent Dispatch

- Best when: Harness should actively enforce clean-worker execution rather than only validate evidence.
- Benefit: Strongest prevention of same-context self-approval.
- Cost: Much larger scope across runner orchestration, platform adapters, state machine gates, and role prompts.
- Risk: High compatibility and UX risk for existing local workflows.
- Evidence needed: End-to-end runner dispatch tests and platform-specific adapter coverage.

## Recommendation

Choose Option A for the P0 first version.

Rationale: `upgrade.md` explicitly says the first version should be evidence-check based and not require automatic subagent startup. Option A also follows the proven `user-evidence` document-level check pattern.

## Must Do

- Add `harness check subagent-separation`.
- Validate a `## Subagent Separation` Markdown section.
- Require role matrix fields when separation is required.
- Require waiver details when `Required: no`.
- Check distinguishable role evidence from invocation logs.
- Detect obvious ownership and closure-authority violations from document text.
- Add the check to `harness check all` and `harness ship`.
- Add focused tests.

## Deferred

- Stronger runner result schema enforcement.
- Automatic subagent dispatch.
- State-machine gate hooks for readiness / verification / review-next.
- Skill-chain role handoff enforcement.

## Non-Goals

- Do not auto-start subagents.
- Do not require new dependencies.
- Do not redesign runner orchestration.
- Do not make this first version an AST-level or git-diff ownership checker.

## Next Layer Candidate

Proceed to `brief`.

