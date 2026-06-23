# User-Perceived Integration Evidence Template

Use this file as a starting point for changes that claim MVP, closed-loop,
save, publish, import/export, login, payment, upload, run, preview,
generate, sync, or other user-perceived functionality.

## Results
- Summary: <overall verification result and timestamp>

## Evidence
- Summary: <commands, artifacts, and user-visible evidence used to close this change>

## User-Perceived Integration Evidence
- Evidence level: real-user acceptance
- Real User Entry: <visible product entry point used by the test>
- User-Visible State: <state/result the user can actually see>
- Persistence/External State: <backend, persisted, or external state checked>
- Anti-Self-Proof Assertion: <UI value, request payload, readback, and reopened UI agree>
- Forbidden Test Shortcuts: none
- Command: <verification command>
- Result: <pass/fail result and timestamp>

## Unit Evidence
- Command: <unit test command>
- Behaviour under test: <public behaviour>
- Boundary/negative cases: <covered boundaries>
- Mock boundary: <what is mocked>
- Why mocks do not hide product risk: <reason>

## Integration Evidence
- Command: <integration test command>
- Real modules crossed: <modules crossed>
- Writer: <writer>
- Consumer: <consumer>
- Persisted/readback state: <state checked>
- External systems mocked: <mocked systems>
- Why acceptable: <reason>

## User-Perceived Integration Not Applicable
- Reason: <why this change has no user-perceived path>
- Replacement verification: <what evidence closes the change instead>
- Residual risk: <remaining risk>
