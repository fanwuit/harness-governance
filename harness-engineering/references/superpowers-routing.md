# Superpowers Routing

## Rule

Do not assume `superpowers:*` skills exist in the target environment.

For each routed workflow:

1. Check whether the named `superpowers:*` skill is available in the current skill list.
2. If available, use it as the preferred companion workflow.
3. If unavailable, say it is unavailable and use the local fallback.
4. Stop only when the route is explicitly marked `required`.

## Routing Matrix

| Situation | Preferred companion | Local fallback | Requirement |
|---|---|---|---|
| Creative product, feature, or design work | `superpowers:brainstorming` | `brainstorm-to-brief` | preferred |
| Multi-step implementation planning | `superpowers:writing-plans` | `planning-with-files` or project queue | preferred |
| Executing a written plan | `superpowers:executing-plans` | `harness-engineering` queue plus checkpoints | preferred |
| Independent parallel tasks | `superpowers:dispatching-parallel-agents` | Execute serially and record handoff state | optional |
| Bug, test failure, or unexpected behavior | `superpowers:systematic-debugging` | Reproduce, observe, isolate, fix, verify; use `debugging-checklist` only for human handoff | preferred |
| Feature or bugfix implementation | `superpowers:test-driven-development` | `contract-first-development` plus target-local tests | preferred |
| Before claiming completion, fixed, or passing | `superpowers:verification-before-completion` | Run explicit verification commands and report evidence | preferred |
| Receiving review feedback | `superpowers:receiving-code-review` | Default code-review stance: verify, challenge unclear feedback, then patch | preferred |
| Requesting review before merge | `superpowers:requesting-code-review` | Run local review checklist and verification | optional |
| Finishing a branch | `superpowers:finishing-a-development-branch` | `review-next-governance` plus git status, commit, and push workflow | optional |
| Creating or updating skills | `superpowers:writing-skills` | `skill-creator` when available; otherwise keep frontmatter concise and validate | preferred |
| Starting isolated feature work | `superpowers:using-git-worktrees` | Use current workspace unless user or project rules require isolation | optional |

## Disclosure Template

When a preferred companion is unavailable, say:

```text
Preferred companion skill <skill-name> is unavailable in this environment. Continuing with <local-fallback>.
```

Do not claim the companion workflow was executed unless its `SKILL.md` was actually loaded.
