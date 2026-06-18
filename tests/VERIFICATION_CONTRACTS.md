# Verification Evidence Contracts

## User-Perceived Integration Evidence

Any change that claims MVP, closed-loop, save, publish, import/export, login,
payment, upload, run, preview, generate, sync, or similar user-visible
functionality must provide one of these sections in `docs/verification/*.md`
or `docs/changes/<change-id>/verification.md`:

- `## User-Perceived Integration Evidence`
- `## User-Perceived Integration Not Applicable`

For real-user acceptance, the evidence must identify the real user entry,
user-visible state, persistence or external state, anti-self-proof assertion,
command, and result. Smoke and contract checks can support the evidence, but
cannot close MVP or closed-loop claims by themselves.

## Anti-Self-Proof Rule

The checker must reject evidence that proves only a test-created internal path.
For save-like flows, evidence must tie together the visible UI value, request
payload, readback response, and reopened UI state.
