# Harness Governance (Cline)

Use `harness` CLI commands instead of in-line editing when the user asks for engineering work in this project.

## Workflow

1. **Classify the task** with `harness governed-start "<description>" [--files ...] [--contracts] [--external] [--unclear]`.
2. **Create a change packet** if the work spans more than one layer:
   ```bash
   harness packet init <change-id>
   harness packet check
   ```
3. **Run targeted checks** before claiming completion:
   ```bash
   harness check --all
   harness status
   ```
4. **Close the task** with `harness review close <task-id> --evidence "..."`.

## Rules

- Never skip `readiness` before `implementation` unless the user explicitly scopes the work as a throwaway prototype.
- Persisted data, external side effects, public contracts, and production runtime behavior exclude the prototype exception.
- Always enter `review-next` when work finishes or pauses.
- Promote important state into durable artifacts (ADR, schema, fixture, queue) instead of leaving it in chat.