# Proposal: capability-tier-routing

Status: done

## Goal

Implement a first version of platform-neutral capability-tiered subagent routing.

## Motivation

Subagent Separation can verify that independent role evidence exists, but it does
not decide which capability level each role requires. Harness needs a
platform-neutral routing layer so cheaper or weaker execution agents can work
inside explicit boundaries while strong agents retain planning, contract, and
verification authority.

## Scope

- In scope:
  - Define `strong`, `execution`, and `mechanical` capability tiers.
  - Define default role policy and per-project overrides.
  - Discover agent directory `tiers.json` declarations.
  - Record invocation tier provenance.
  - Require independent strong verification for lower-tier work.
- Out of scope:
  - Provider-specific model ranking in harness core.
  - A separate capability inspection CLI.
  - Runtime execution changes beyond existing runner/orchestrator integration.

## Affected Users Or Systems

- Agent platform maintainers declaring model candidates.
- Harness runner/orchestrator users dispatching role-specific subagents.
- Review/Next closeout checks that enforce verifier independence.

## Harness Layer

- Current layer: review-next
- Next candidate layer: none for this first version
- Packetization note: this packet records the completed first version and its verification evidence.
