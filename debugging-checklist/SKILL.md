---
name: debugging-checklist
description: Use when a junior developer, human handoff, or lightweight fallback output needs a concise debugging checklist. Do not use as the primary active bug-fixing workflow; when superpowers:systematic-debugging is unavailable, active agents should follow a separate reproduce/observe/isolate/fix/verify fallback.
---

## Harness Precondition

应用本 skill 前，先确认 `harness-engineering` 已经完成当前 layer 和本地治理义务判断。若尚未完成，停止本 skill，返回 `harness-engineering`；不要让本 skill 充当入口路由。

# Debugging Checklist

## Purpose
Provide a systematic debugging checklist for a human reader, junior developer, or handoff note. This is not the primary active bug-fixing workflow. When `superpowers:systematic-debugging` is unavailable, active agents should follow the routing fallback in `harness-engineering/references/superpowers-routing.md`: reproduce, observe, isolate, fix, and verify; use this skill only to produce lightweight checklist or handoff output.

## Inputs to request
- Repro steps and frequency.
- Environment details and recent changes.
- Logs, stack traces, or screenshots.

## Workflow
1. Reproduce the issue and isolate the scope.
2. Check inputs, environment, and recent changes.
3. Add targeted logs or breakpoints.
4. Hand off clear next checks instead of executing a full agent debugging loop.

## Output
- Checklist ordered by likelihood.

## Quality bar
- Start with reversible, low-risk checks.
- Prefer minimal probes over broad logging.
