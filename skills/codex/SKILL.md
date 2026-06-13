# Harness Governance (Codex)

Use the `harness` CLI for all engineering work in this project. It encodes the local 12-layer governance state machine.

## Entry

Before any work, classify and disclose:

```bash
harness governed-start "<task description>" [--files a.py,b.py] [--contracts] [--external] [--unclear]
```

The command returns the routing decision plus the canonical disclosure block. Cite it in your reply before doing anything else.

## Change packets

```bash
harness packet init <change-id>
harness packet check
```

A change packet is a durable carrier, not a gate. Implementation still requires readiness plus an Implementation Entry Record.

## Planning

```bash
harness plan init [slug]
harness plan attest
harness plan complete
```

## Status / verification / close

```bash
harness status
harness verify <preset>
harness review close <task-id> --evidence "..."
```

## Rules

- Do not enter `implementation` before `readiness` unless the user explicitly asks for a throwaway prototype.
- Persisted data, external side effects, public contracts, or production runtime behavior exclude the prototype exception.
- Always enter `review-next` when work finishes or pauses.
- Promote durable findings into ADR / schema / fixture / queue; chat-only conclusions are not durable state.

Run `harness --help` for the full command tree.