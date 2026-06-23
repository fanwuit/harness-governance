# Proposal

Replace governed platform/process executor dispatch with a platform-neutral native subagent handoff protocol.

Harness core prepares request and prompt artifacts, records the host platform's native spawn, parses result JSON, and gates the complete lifecycle. It does not directly execute platform CLIs or subprocess agent workers.
