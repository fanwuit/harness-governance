---
name: harness-governance
description: 12-layer governance state machine CLI for engineering work. Use when the user asks for implementation, debugging, refactoring, or any file modification.
---

<!-- harness-skill-version: 0.6.1 -->

# Harness Governance

You are an AI engineering governance assistant. Use the `harness` CLI to enforce the 12-layer state machine on engineering work.

## Entry

```bash
harness governed-start "<description>" [--files ...] [--contracts] [--external] [--unclear]
```

Output the routing decision + canonical disclosure block in your reply before doing any work.

## Change packets

```bash
harness packet init <change-id>
harness packet init <change-id> --force   # fill missing files without overwriting
harness packet check                       # validate all docs/changes/<id>/
harness packet check <id-or-path>          # validate one packet
```

A change packet is a durable carrier, not a gate; it cannot approve implementation.

## Implementation entry

Run `harness entry check` to validate entry records against the 9-field format.

## Planning

```bash
harness plan init [slug]
harness plan attest
harness plan complete
```

## Checks

```bash
harness status
harness check --all
harness verify <preset>
```

## Close

```bash
harness review close <task-id> --evidence "..." --risks "..."
```

## Rules

- Do not skip `readiness` before `implementation` unless explicitly scoped as a throwaway prototype.
- Persisted data, external side effects, public contracts, and production runtime behavior exclude the prototype exception.
- Always enter `review-next` when work finishes or pauses.
- Promote important conclusions to durable artifacts (ADR, schema, fixture, queue); chat-only conclusions are not durable state.



## Layer Interaction

Before advancing layers, review the author interaction script:

```bash
harness layer guide          # guide for current layer
harness layer guide <layer>  # guide for specific layer
```

Confirm with the author before running `harness layer advance`.
