# Superpowers Routing

## Rule

Do not assume `superpowers:*` skills exist in the target environment.

Before routing to a companion workflow, check the current skill list for matching local governance skills. Local governance skills own layer, boundary, role isolation, readiness, contract, verification, and review/next decisions. `superpowers:*` skills are companion execution workflows, not replacements for matching local governance skills.

## Entry Gate

For development, planning, implementation, verification, queue, or handoff requests, route through `harness-engineering` before any `superpowers:*` workflow. This includes empty projects, demos, small games, simple feature requests, and "continue" / "next" requests.

If `superpowers:using-superpowers` also appears to match because of a broad session-start rule, treat it as a companion check only. It may be loaded when required, but it does not own entry routing and must not trigger `superpowers:brainstorming`, `superpowers:writing-plans`, TDD, debugging, verification, or branch-finish workflows until harness has selected the current layer.

`superpowers:using-superpowers` is not exempt from harness entry even when its metadata says "starting any conversation" or "before ANY response". Project-level harness entry, `skill-use-transparency`, and local governance routing run first.

## Companion Capability Adapter

When the current harness layer allows a companion workflow, import only the companion techniques that produce the current layer's required output. Ignore companion terminal states, required sub-skills, default artifact paths, commits, and next-workflow transitions unless the harness layer map explicitly approves them.

Adapter rules:

1. Convert companion `MUST`, hard gate, terminal state, `REQUIRED SUB-SKILL`, or "invoke next skill" language into a harness next-layer candidate.
2. Keep ownership with the primary local governance skill for the current layer.
3. Use companion techniques only as helpers, for example one-question-at-a-time brainstorming, option comparison, visual companion, systematic debugging steps, TDD discipline, or verification discipline.
4. Do not create `docs/superpowers/...` artifacts, commits, worktrees, implementation plans, subagents, branch-finish flows, or PR steps solely because a companion workflow says to do so.
5. Resume the harness transition gate after the companion-supported output is produced.

Example: in `Layer: brainstorming`, `brainstorm-to-brief` remains the local owner. `superpowers:brainstorming` may supply context exploration, one-question-at-a-time questioning, option comparison, scope decomposition, visual companion, and design review techniques. Its terminal state to invoke `superpowers:writing-plans`, write `docs/superpowers/specs/...`, or commit is ignored unless harness has moved through Brief and approved the later layer.

## Companion-Only Containment

`superpowers:*` skills are never layer owners under harness governance. Loading a `superpowers:*` skill gives access to useful companion instructions, but it does not authorize following that skill's terminal state, hard gates, checklist, or next-skill transition when those would move the task outside the current harness layer.

Use this containment rule:

1. Name the current harness layer before applying the companion skill.
2. Name the local governance skill that owns that layer.
3. Apply only the companion instructions that support that layer's required output.
4. Stop before any companion instruction that would skip or replace Architecture, ADR, Contract, Readiness, Verification, or Review / Next.
5. If the companion workflow conflicts with the harness layer map, say so and continue with the local governance skill.

Example: after `superpowers:brainstorming` produces a design, do not follow it directly into `superpowers:writing-plans` when harness still requires Architecture, ADR, or Contract. First route through the local skills for those layers.

If a project-level instruction makes harness entry mandatory, that instruction takes precedence over broad companion-skill entry rules. In that case, disclose:

```text
Routing decision: harness-engineering owns entry routing; superpowers:* is companion-only until harness routing completes.
```

Do not hardcode a user's skill directory. Use the skill paths exposed in the current session or the active environment's skill discovery mechanism.

For each routed workflow:

1. Select and load any matching local governance skills first.
2. Check whether the named `superpowers:*` skill is available in the current skill list.
3. If available, use it as a companion workflow only for the current harness layer's allowed output.
4. If unavailable, say it is unavailable and use the local fallback.
5. Ignore companion terminal states or hard gates that would advance to a later harness layer before local governance approves that transition.
6. Stop only when the harness route, not the companion route, is explicitly marked `required`.

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

When a companion workflow overlaps local governance, report:

```text
Local governance skills: <selected local skills>
Companion workflow skills: <selected companion skills>
Loaded SKILL.md files: <success/failure list>
Routing decision: local governance owns <layer/boundary/readiness/etc.>; companion workflow executes <workflow>.
```
