# Local QA / Release / Monitor / Retro Absorption / 本地 QA / 发布 / 监控 / 回顾吸收

## Purpose / 目的

Borrow the useful engineering discipline of QA, release readiness, monitoring, and retro loops without adopting an external workflow owner, adapter, directory structure, CLI, or terminal state.

借鉴 QA、发布就绪、监控和回顾循环的有用工程纪律，而不采用外部工作流所有者、适配器、目录结构、CLI 或终端状态。

These practices are companion-only inputs. They provide evidence and next-layer candidates; they do not approve new product scope, implementation, shipping, deployment, commits, pushes, or release publication.

这些实践仅是伴随输入。它们提供证据和下一层候选；它们不批准新产品范围、实现、交付、部署、提交、推送或发布。

## Absorption Map / 吸收映射

| Practice | Local owner | Allowed technique | Stable evidence | Forbidden transition |
|---|---|---|---|---|
| QA | `review-next-governance`, with contract evidence from `contract-first-development` | Real app / CLI / TUI smoke checks, key-path regression checks, screenshot or command evidence, skipped-risk notes | Completion evidence, verification output, contract/check update, review-next state | Do not treat QA pass as permission to expand scope or skip readiness / implementation entry. |
| Release | `review-next-governance`, with release gate constraints from `implementation-readiness-gate` | Release readiness checklist: git status, tests/checks, docs updated, version/changelog, CI state, rollback/disable path, explicit user approval before push/deploy/publish | Review / Next summary, release readiness notes, changelog/version docs when in scope | Do not tag, publish, deploy, push, open PR, or create commits unless the user or project rule explicitly requested it. |
| Monitor | `observable-fact-discovery`, `harness-status-dashboard`, `harness-visualization`, `autonomous-ready-loop` | Read logs, errors, metrics, runner markers, status JSON, verification stale/failed signals, human-needed blockers | Fact record, status output, checkpoint, invocation log, blocked/not-now state | Do not silently mutate queues or call monitoring green as product-ready without matching verification. |
| Retro | `agent-mistake-guard`, `document-gardener`, `review-next-governance` | Identify repeated agent mistakes, stale docs, missing indexes, recurring failure modes, and follow-up checks | Guardrail entry, document-gardener finding, backlog/not-now item, mechanical check candidate | Do not create broad process rewrites, long failure logs, or new gates without repeated evidence and owner approval. |

## Boundaries / 边界

- No external adapter is introduced. / 不引入外部适配器。
- No external artifact path is canonical. / 没有外部制品路径是规范的。
- No external terminal state can bypass the harness layer map. / 没有外部终端状态可以绕过 harness 层级映射。
- QA / Release / Monitor / Retro records are evidence for local owners, not a new lifecycle that owns the repository. / QA / Release / Monitor / Retro 记录是本地所有者的证据，不是拥有仓库的新生命周期。
- If a practice reveals missing contract, readiness, implementation entry, verification, or review-next evidence, route back to the local owner layer. / 如果某个实践揭示缺失的契约、就绪、实现入口、验证或 review-next 证据，则路由回本地所有者层。

## Verification / 验证

When these practices are added or changed, use targeted governance checks first. Run `harness check all` only at phase closeout, before commit / PR / release, or when the change touches validation machinery or has unclear impact.

当这些实践被添加或更改时，首先使用定向治理检查。仅在阶段收尾、commit / PR / release 之前，或当变更涉及验证机制或影响不明确时，才运行 `harness check all`。
