# Local QA / Release / Monitor / Retro Absorption

## Purpose

Borrow the useful engineering discipline of QA, release readiness, monitoring, and retro loops without adopting an external workflow owner, adapter, directory structure, CLI, or terminal state.

These practices are companion-only inputs. They provide evidence and next-layer candidates; they do not approve new product scope, implementation, shipping, deployment, commits, pushes, or release publication.

## Absorption Map

| Practice | Local owner | Allowed technique | Stable evidence | Forbidden transition |
|---|---|---|---|---|
| QA | `review-next-governance`, with contract evidence from `contract-first-development` | Real app / CLI / TUI smoke checks, key-path regression checks, screenshot or command evidence, skipped-risk notes | Completion evidence, verification output, contract/check update, review-next state | Do not treat QA pass as permission to expand scope or skip readiness / implementation entry. |
| Release | `review-next-governance`, with release gate constraints from `implementation-readiness-gate` | Release readiness checklist: git status, tests/checks, docs updated, version/changelog, CI state, rollback/disable path, explicit user approval before push/deploy/publish | Review / Next summary, release readiness notes, changelog/version docs when in scope | Do not tag, publish, deploy, push, open PR, or create commits unless the user or project rule explicitly requested it. |
| Monitor | `observable-fact-discovery`, `harness-status-dashboard`, `harness-visualization`, `autonomous-ready-loop` | Read logs, errors, metrics, runner markers, status JSON, verification stale/failed signals, human-needed blockers | Fact record, status output, checkpoint, invocation log, blocked/not-now state | Do not silently mutate queues or call monitoring green as product-ready without matching verification. |
| Retro | `agent-mistake-guard`, `document-gardener`, `review-next-governance` | Identify repeated agent mistakes, stale docs, missing indexes, recurring failure modes, and follow-up checks | Guardrail entry, document-gardener finding, backlog/not-now item, mechanical check candidate | Do not create broad process rewrites, long failure logs, or new gates without repeated evidence and owner approval. |

## Boundaries

- No external adapter is introduced.
- No external artifact path is canonical.
- No external terminal state can bypass the harness layer map.
- QA / Release / Monitor / Retro records are evidence for local owners, not a new lifecycle that owns the repository.
- If a practice reveals missing contract, readiness, implementation entry, verification, or review-next evidence, route back to the local owner layer.

## Verification

When these practices are added or changed, use targeted governance checks first. Run `npm run check:all` only at phase closeout, before commit / PR / release, or when the change touches validation machinery or has unclear impact.
