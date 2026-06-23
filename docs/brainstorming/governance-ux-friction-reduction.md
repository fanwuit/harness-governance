# Brainstorming: Governance UX Friction Reduction

## Option A: Dependency-Free Prompt Improvements

- Best when: We want low-risk UX gains without changing terminal dependencies.
- Benefit: Works in CI and non-interactive shells, keeps tests simple, and avoids weakening gates.
- Cost: Does not provide arrow-key selection in the first pass.
- Risk: Users may still want richer interactive controls later.
- Evidence needed: CLI output tests showing explicit choices and reduced duplicate feedback.

## Option B: Full Interactive Selector

- Best when: The CLI is primarily used in an interactive terminal.
- Benefit: Supports arrow keys and richer guided flows.
- Cost: Adds dependency and TTY behavior complexity.
- Risk: Can break scripted usage or require extensive terminal test fixtures.
- Evidence needed: TTY integration tests across supported shells.

## Option C: Documentation-Only Guidance

- Best when: We only need to clarify how agents should ask questions.
- Benefit: Very low implementation cost.
- Cost: Does not fix duplicate prompts or confusing CLI output.
- Risk: Agents continue to produce inconsistent interactions.
- Evidence needed: Manual adherence only, which is weak for this project.

## Recommendation

Choose Option A for this pass. It addresses the first-order friction while preserving deterministic CLI behavior.

## Must Do

- Keep gate enforcement unchanged.
- Make critical confirmations explicit with clear choices.
- Reduce duplicate question or feedback rendering.
- Document deferred interactive selector behavior.

## Deferred

- Arrow-key terminal selector.
- Platform-specific slash-command UX.
- Full wizard-style rewrite of all layer flows.

## Non-Goals

- No relaxation of required layer questions.
- No new external dependency unless later justified.
- No automatic progression through gates.
