# Check Frequency Guidance

## Purpose

降低治理链路的日常开销，同时保持完成声明、阶段收口和对外交付前的验证可信。检查频率按影响范围分层，而不是每次小改都跑全量。

## Default Rule

- During iteration: run targeted checks that match the files or behavior changed.
- At phase closeout: run `npm run check:all`.
- Before commit, PR, push, release, publish, or handoff: run `npm run check:all`.
- When verification machinery changed or impact scope is unclear: run `npm run check:all`.

## Targeted Checks

Use targeted checks while still editing:

- Script behavior changed: run the script's focused test file.
- README skill inventory or important asset list changed: run `npm run check:inventory`.
- Implementation Entry Record checker or remediation records changed: run `npm run check:entry-record` and its tests.
- Change packets changed: run `npm run check:packets`.
- Routing, layer, companion, or governance wording changed: run `npm run check:routing` and governance docs tests.
- Harness visualization output or status parsing changed: run harness visualization tests.

If a targeted check is failing, fix that failure before spending time on `check:all`.

## Full Check Triggers

Run `npm run check:all` when any of these are true:

- A remediation item or implementation phase is about to be marked done.
- A batch of related governance changes is being closed out.
- You are about to commit, open a PR, push, release, publish, or hand off to another person/agent.
- `package.json` scripts, test globs, checker scripts, or `check:all` itself changed.
- Multiple governance owners were touched, or the blast radius is not obvious.
- A long-running or multi-agent task has completed and the final worktree needs one trusted readout.

## Recurring Jobs

Recurring jobs should not amplify verification cost by default:

- Nightly `document-gardener` should default to scan-only and lightweight structure checks.
- Repair mode or stable-state edits may run targeted checks first.
- `check:all` belongs to repair closeout, phase closeout, or explicit release/commit readiness, not every nightly scan.

## Output Expectation

Final reports should name the checks that actually ran and their result. If `check:all` was intentionally skipped, say why and name the targeted checks that were sufficient for the current scope.
