---
name: codebase-orientation
description: Guide quick orientation of an unfamiliar codebase with module mapping, entry points, and local run steps. Use when a junior developer needs to get situated fast.
---

## Harness Precondition

应用本 skill 前，先确认 `harness-engineering` 已经完成当前 layer 和本地治理义务判断。若尚未完成，停止本 skill，返回 `harness-engineering`；不要让本 skill 充当入口路由。

# Codebase Orientation

## Purpose
Guide quick orientation of an unfamiliar codebase with module mapping, entry points, and local run steps.

## Inputs to request
- Repo URL or local path and target area of interest.
- Runtime versions, package manager, and OS.
- Current task or reason for onboarding.

## Workflow
1. Locate entry points, build scripts, and main runtime paths.
2. Map key folders, ownership, and common naming conventions.
3. Identify how to run, test, and debug locally with minimal setup.
4. Call out one or two safe starter tasks for learning.

## Output
- High-level module map with file paths.
- Local run/test commands with prerequisites.
- Suggested first change with low risk.

## Quality bar
- Reference concrete file paths and commands.
- Keep scope limited to the requested area.
