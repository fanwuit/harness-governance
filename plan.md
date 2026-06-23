# Governance UX Load Reduction Plan

## Problem

Harness already has three entry routes:

- `fast-path`
- `trivial-safe-change`
- `governed-path`

However, the actual interaction cost is still too close to the full 12-layer governance flow. In practice, users can experience the routes as labels rather than meaningful workload reductions.

The product problem is: route classification exists, but route-specific interaction budgets are not enforced clearly enough.

## Goal

Make route selection directly control interaction load.

`governed-path` should mean "this task needs governance", not "this task must run the full 12-layer Q&A flow". Full 12-layer governance should be reserved for strict or high-risk work.

## Target Behavior

### fast-path

- No governed session.
- No layer Q&A.
- No change packet.
- 0 required questions unless the agent is genuinely blocked.
- Final response can carry verification evidence.

### trivial-safe-change

- No逐层 gate flow.
- Maximum 1-3 focused questions.
- Merge intake, orientation, and readiness into one compact judgment.
- No required change packet.
- Entry record is optional or lightweight.

### governed-path + light

- Compact 6-layer path:
  - `intake-orientation`
  - `brief`
  - `readiness`
  - `implementation`
  - `verification`
  - `review-next`
- Maximum 1 key question per active layer.
- No full 12-layer Q&A.
- No full change packet unless another risk signal requires it.

### governed-path + standard

- Governed workflow remains active, but layers can be merged.
- Maximum 3-5 total user-facing questions before implementation unless blocked.
- Use targeted gates, not default exhaustive questioning.

### governed-path + strict

- Full 12-layer governance.
- Per-layer gate checks.
- Full author-question requirements.
- Change packet expected where applicable.
- Used only for high-risk, unclear, public contract, external side-effect, architecture, security, auth, persistence, deployment, or similar work.

## Rule Changes

### 1. Make interaction budget explicit

Add a route/rigor interaction budget concept:

```text
fast-path -> none
trivial-safe-change -> trivial
governed-path + light -> compact
governed-path + standard -> bounded
governed-path + strict -> full
```

This budget should be visible in CLI output and available in JSON output.

### 2. Stop defaulting ordinary governed-path work to strict

Current risk:

- `state_machine/rigor.py` defaults to `STRICT`.
- That makes many ordinary governed tasks feel like full 12-layer tasks.

New rule:

```text
high risk / unclear / contracts / external -> strict
medium risk governed work -> light or standard
low risk governed work -> light
explicit --rigor still wins
strict keywords still force strict
```

### 3. Decouple governed-path from full governance

`governed-path` should create governance state when needed, but it should not imply full-depth interaction by itself.

The effective depth should come from `rigor_tier` plus the interaction budget.

### 4. Update CLI disclosure

`harness governed-start` should print the interaction budget for non-fast routes.

Example:

```text
Routing: governed-path
Rigor tier: light
Interaction budget: compact, up to 1 key question per active layer
Layer path: intake-orientation -> brief -> readiness -> implementation -> verification -> review-next
```

For `trivial-safe-change`:

```text
Routing: trivial-safe-change
Interaction budget: trivial, max 1-3 focused questions
```

### 5. Update agent skill instructions

Skill templates should stop saying or implying that standard work normally requires 20-30 Q&A rounds.

New instruction:

```text
Route controls interaction budget.
Do not ask layer questions unless missing information blocks safe progress.
Complete 12-layer Q&A only when rigor=strict.
For light governed-path, merge intake/orientation/brief/readiness into one compact decision.
```

## Likely Files To Change

- `src/harness_governance/state_machine/rigor.py`
  - Change default rigor behavior.
  - Clarify tier semantics in comments/docstrings.

- `src/harness_governance/state_machine/classification.py`
  - Ensure agent risk and route produce the right rigor/budget semantics.
  - Keep `governed-path` separate from strict governance.

- `src/harness_governance/commands/governed_start.py`
  - Add interaction budget to text output.
  - Add interaction budget to JSON output.
  - Avoid wording that implies all governed tasks require full layer progression.

- `src/harness_governance/messages.py`
  - Add bilingual message strings for interaction budget output.

- `src/harness_governance/data/skills/light/*`
  - Ensure light instructions describe compact governance.

- `src/harness_governance/data/skills/standard/*`
  - Remove default 20-30 Q&A expectation.
  - Emphasize bounded questions and merged layers.

- `.agents/skills/harness-governance-standard/SKILL.md`
  - Regenerate or update after template changes.

- `tests/test_commands/test_governed_start.py`
  - Add CLI and JSON output coverage.

- `tests/test_state_machine/test_rigor.py`
  - Add rigor default and strict override coverage.

## Acceptance Criteria

- Pure Q&A routes to `fast-path` and does not show disclosure-heavy output.
- Low-risk local edits route to `trivial-safe-change` and show a trivial interaction budget.
- Medium-risk governed work does not default to full 12-layer strict flow.
- High-risk, unclear, public contract, external side-effect, auth, persistence, deployment, or architecture work still reaches strict governance.
- `governed-start --json` includes an interaction budget field.
- Skill text clearly states that full 12-layer Q&A is strict-only.
- Tests prove that route selection changes user-facing workload, not just labels.

## Implementation Order

1. Add interaction budget model and tests.
2. Adjust rigor default/resolution rules.
3. Update `governed-start` text and JSON output.
4. Update skill templates and regenerate installed skill docs if needed.
5. Run focused tests for classification, rigor, and governed-start.
6. Run broader test suite if focused tests pass.

