# Change Packet Model

## Purpose

Use a change packet as a temporary, durable work folder for complex changes. It keeps proposal, design, tasks, contracts, and verification context together while the harness layer model remains the authority.

The packet is a carrier, not a gate. Harness layers still decide what can move next.

## When To Use

Create or request a packet when at least one condition is true:

- The work spans two or more harness layers.
- The work touches multiple modules, services, repositories, tools, or runtimes.
- The work will likely continue across multiple agent sessions.
- The work needs ADR, contract, readiness, implementation, and verification context linked together.
- NEXT, TODO, backlog, or checkpoint text would become too large if it held all context.
- The user asks for OpenSpec-like proposal, design, task, spec delta, or archive behavior.

Do not use a packet for:

- A single command or direct factual answer.
- A narrow one-file documentation edit.
- A small bugfix whose contract and verification path are already obvious.
- Work already fully captured by an existing ADR, contract, issue, or checkpoint.

## Suggested Shape

Prefer a project-local convention over importing a tool-specific layout:

```text
docs/changes/
  <change-id>/
    proposal.md
    design.md
    tasks.md
    contracts.md
    verification.md
  archive/
    <YYYY-MM-DD>-<change-id>/
      proposal.md
      design.md
      tasks.md
      contracts.md
      verification.md
```

If the project already has another durable task packet convention, adapt this model to that convention instead of creating a competing source of truth.

OpenSpec is only a reference source for artifact discipline. Do not create or read `openspec/changes/*`, do not require OpenSpec installation, and do not expose `openspec init/update/apply/archive` as this harness model.

## Native Templates

Use the bundled templates when a complex task needs a packet:

```text
harness-engineering/templates/change-packet/
  proposal.md
  design.md
  tasks.md
  contracts.md
  verification.md
```

Initialize a packet with:

```text
node harness-engineering/scripts/init-change-packet.mjs <change-id>
```

The script writes `docs/changes/<change-id>/` using the native templates. It does not create `openspec/`, does not apply changes, and does not archive completed work.

## File Responsibilities

| File | Responsibility |
|---|---|
| `proposal.md` | Goal, motivation, scope, non-goals, affected users or systems. |
| `design.md` | Boundaries, responsibilities, data/control flow, alternatives, ADR candidates. |
| `tasks.md` | Layered task list with current blocking layer and ready/blocked state. |
| `contracts.md` | Schemas, fixtures, examples, API shapes, probes, checks, and acceptance criteria. |
| `verification.md` | Commands, evidence, failures, freshness, screenshots, traces, and remaining risk. |

Keep each file short. Move stable conclusions into the long-lived project sources instead of letting the packet become permanent documentation.

## Contract Delta Shape

In `contracts.md`, use these sections:

- `Current behavior`
- `Proposed behavior / contract delta`
- `Contract artifacts`
- `Acceptance checks`
- `Failure cases`

This borrows the useful part of spec delta thinking while keeping the output in the Contract layer. `contracts.md` can describe the delta, but it does not replace executable schema, fixture, probe, check script, acceptance test, or an explicitly justified documentation invariant.

## Layer Relationship

| Harness layer | Packet use |
|---|---|
| Idea / Brainstorming | Capture intent, options, risks, and non-goals. |
| Brief | Fix goal, success criteria, and current exclusions. |
| Architecture | Record boundaries, data flow, ownership, and ADR candidates. |
| ADR | Link to accepted decisions; do not replace ADRs with packet prose. |
| Contract | Link to schemas, fixtures, examples, probes, and checks. |
| Readiness | Confirm target-local rules, verification commands, and scope limits. |
| Implementation | Track only approved implementation slices. Do not expand scope from tasks alone. |
| Verification | Record fresh evidence and unresolved failures. |
| Review / Next | Archive stable conclusions back to official project state. |

## Status Rules

Use simple status words:

```text
draft
ready
active
blocked
done
archived
```

Rules:

- `ready` means the current layer has enough durable evidence to proceed.
- `active` means work is in progress at the stated layer.
- `blocked` must state the missing evidence, decision, contract, or external condition.
- `done` means the packet goal is satisfied, but archive may still be pending.
- `archived` means stable conclusions were copied or linked back to official project sources and the packet has moved under `docs/changes/archive/<YYYY-MM-DD>-<change-id>/` or the project's equivalent archive.

## Mechanical Packet Check

Run:

```text
node harness-engineering/scripts/check-change-packet.mjs [packet-path-or-id ...]
```

or through the root wrapper:

```text
npm run check:packets
```

The checker enforces only mechanical packet hygiene:

- required files exist: `proposal.md`, `design.md`, `tasks.md`, `contracts.md`, `verification.md`;
- `tasks.md` contains a checkbox checklist;
- `contracts.md` declares a contract artifact or an explicit blocked reason;
- `verification.md` records a command, result, or unable-to-verify reason;
- every `Status:` value is one of `draft`, `ready`, `active`, `blocked`, `done`, `archived`;
- archived packets link stable conclusions back to ADR, README, contract, verification, queue, or project index.

Passing the checker does not approve implementation. Readiness and the Implementation Entry Record still decide whether implementation can proceed.

## Archive Rules

Before marking a packet archived, check whether stable conclusions need to be reflected in:

- ADR or decision notes.
- Schemas, fixtures, examples, probes, or checks.
- Verification documentation or verification records.
- NEXT, TODO, backlog, or checkpoint state.
- Documentation maps, README navigation, or agent instructions.

If a conclusion stays only inside the packet, the packet is not archived.

Keep the scheduler queue lean during archive:

- Remove completed `[done]` items from `NEXT.md`; do not use the scheduler as a history log.
- Keep only executable `[ready]` items in `NEXT.md`, with at most a short-lived `[active]` item while a runner owns work.
- Preserve completed history in the archive directory or in the project's official issue/done record before deleting or moving old queue text.

## Queue Integration

Queue items may point to a packet instead of repeating context:

```text
[ready] Implement public projection contract fixture
Layer: contract
Change: docs/changes/public-projection-contract/
Evidence: contracts.md#fixtures
```

The queue remains the scheduler. The packet remains the context holder. Completed packets leave the scheduler and move to the archive; historical done facts must not be dropped during that move.

## Common Mistakes

| Mistake | Correction |
|---|---|
| Treating packet tasks as implementation approval. | Readiness and contract gates still decide implementation. |
| Creating packets for every small task. | Use packets only when context would otherwise fragment. |
| Letting packets become permanent docs. | Archive stable conclusions back to official sources. |
| Replacing ADRs with `design.md`. | Use `design.md` to identify ADR candidates, then write ADRs. |
| Replacing checks with `contracts.md`. | Use `contracts.md` to link or specify executable checks. |
| Hiding blocked scope inside a packet. | Mirror blocked state to the project queue or checkpoint. |

## Minimal Decision Check

Before creating a packet, answer:

```text
Will a future agent need more than the queue item, ADR, and contract files to resume safely?
```

If yes, create or request a packet. If no, keep the existing harness artifacts lean.
