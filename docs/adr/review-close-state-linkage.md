# ADR: Review Close Updates Matching Session

## Status

Accepted

## Context

`harness review close` already writes checkpoint state and marks matching `NEXT.md` queue items as `[done]`. A completed task can still appear active when the matching session remains open.

## Decision

`harness review close <task-id>` will attempt to close a governance session whose session id exactly equals `<task-id>`.

Missing sessions remain a no-op. Queue item closure keeps the existing `mark_queue_item_done` behavior.

## Alternatives

- Add a separate state sync command.
- Rewrite closeout around a shared service.
- Fuzzy-match sessions by task title or queue title.

## Consequences

- The normal closeout command becomes the single path for checkpoint, queue, and same-id session closure.
- `commands/review.py` gains a small dependency on session persistence.
- Exact matching avoids closing unrelated sessions.

## Validation

Focused CLI tests must prove checkpoint, queue, and session state close together, and that missing sessions do not fail `review close`.
