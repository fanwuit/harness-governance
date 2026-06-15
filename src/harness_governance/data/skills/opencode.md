# Harness Governance (OpenCode)

Use `harness` CLI commands to govern engineering work in this project. Invoke these commands via the terminal instead of editing governance files directly.

## Entry

Before any work, classify and disclose:

```bash
harness governed-start "<task description>" [--files a.py,b.py] [--contracts] [--external] [--unclear]
```

Do not skip this step. Fast path returns briefly; trivial / governed must output the disclosure block.

## Change packets

```bash
harness packet init <change-id>
harness packet init <change-id> --force   # fill missing files without overwriting
harness packet check                       # validate all docs/changes/<id>/
harness packet check <id-or-path>          # validate one packet
```

A change packet is a durable carrier, not a gate; it cannot approve implementation.

## Implementation entry

`harness-governance` does not embed Implementation Entry Record parsing. Use the `governed-implementation-entry` skill's 9-field format; once the `harness entry check` command is published (Phase B), validation will wire in automatically.

## Planning

```bash
harness plan init [slug]
harness plan attest
harness plan complete
```

## Status & checks

```bash
harness status                 # Markdown view
harness status --json          # JSON view
harness check --all            # routing + packets + entry + inventory
```

## Verification

```bash
harness verify <preset>
```

## Close

```bash
harness review close <task-id> --evidence "..." --risks "..."
```

## Rules

- Do not skip `readiness` before `implementation` unless the user explicitly scopes the work as a throwaway prototype.
- Persisted data, external side effects, public contracts, and production runtime behavior exclude the prototype exception.
- Always enter `review-next` when work finishes or pauses.
- Promote important state into durable artifacts (ADR, schema, fixture, queue) instead of leaving it in chat.

Run `harness --help` for the full command tree.
