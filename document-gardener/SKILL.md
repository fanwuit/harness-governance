---
name: document-gardener
description: Use when repository documentation, plans, ADRs, queues, indexes, generated docs, checks, skill inventories, skill routing docs, or agent instructions may be stale, conflicting, missing from navigation, or drifting from current code and verified project state.
---

# Document Gardener

## Overview

Keep repository knowledge legible for future agents. Treat versioned documents, queues, ADRs, schemas, examples, and checks as the system of record; repair drift in small, reviewable changes without entering product implementation.

## Trigger Scan

Use this workflow when any of these appear:

- Entry documents disagree about current phase, scope, architecture, or status.
- New, moved, or deleted Markdown files are not reflected in the document map or navigation.
- New schemas, examples, fixtures, probes, checks, or wrappers are not registered in the expected index or standard check entry.
- New, disabled, renamed, or materially changed skills are not reflected in skill inventory docs, routing references, or `agents/openai.yaml` expectations.
- ADRs, briefs, readiness gates, local agent rules, and queue files conflict.
- A queue says work is done, ready, blocked, or not-now in a way that no stable artifact supports.
- Documentation still repeats a conclusion that later code, checks, ADRs, or fixtures have disproved.

## Workflow

1. Read the repository's agent entry file first, usually `AGENTS.md`, `CLAUDE.md`, or the nearest local equivalent.
2. Identify the current system-of-record files: queue/backlog, doc map, architecture docs, ADRs, phase gates, generated docs, and standard verification commands.
3. Run existing documentation or structure checks before editing when they are available.
4. Search for drift with targeted queries: old phase names, deleted paths, stale feature names, missing cross-links, obsolete decisions, and unchecked generated artifacts.
5. For each drift point, decide which source is current and which document is stale. Prefer verified artifacts over chat history or memory.
6. Make minimal edits to navigation, indexes, queue state, or governance text. Do not perform unrelated rewrites.
7. Run the matching documentation, structure, and standard entry checks after editing.
8. If a new follow-up is discovered, record it in the project's stable queue or backlog instead of leaving it only in chat.

## Boundaries

Document gardening may update:

- Documentation navigation and indexes.
- Queue, backlog, blocked, and not-now records.
- ADR links, phase-gate references, readiness references, and agent instructions.
- Check registration or wrapper lists when the check already exists or the task is explicitly to wire governance checks.

Document gardening must not:

- Implement product features under the cover of "fixing docs."
- Promote harness, probe, or exploratory behavior into production architecture.
- Delete useful negative examples, blocked records, failure fixtures, or not-now scope just to make docs look clean.
- Treat screenshots, demos, or chat conclusions as stronger evidence than versioned checks, ADRs, schemas, fixtures, or tests.

## Recurring Runner Pattern

This skill defines the workflow; scheduling belongs to the repository or CI environment.

A recurring document-gardener runner should:

- Start a fresh agent session, for example with `codex exec`, on a daily or weekly cadence.
- Prompt the worker to use `$document-gardener`, read repository-local instructions, and modify only documentation/governance scope.
- Record each run in a stable log such as `.harness/document-gardener-runs.jsonl`.
- Open a small PR or commit only when drift is found and checks pass.
- Stop and report blocked status when the fix would require product implementation, external credentials, or human judgment.

## Output

Report:

- Drift found and the current source of truth.
- Files changed.
- Checks run and their result.
- Remaining drift, blocked items, or queued follow-up.

If no drift is found, say that explicitly and include the checks or searches used as evidence.
