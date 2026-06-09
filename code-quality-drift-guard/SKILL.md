---
name: code-quality-drift-guard
description: Use when a project needs lightweight guardrails for code quality drift, unused files, orphan scripts, duplicate helpers, naming drift, file-size growth, or implementation sprawl during autonomous coding.
---

## Harness Precondition

应用本 skill 前，先确认 `harness-engineering` 已经完成当前 layer 和本地治理义务判断。若尚未完成，停止本 skill，返回 `harness-engineering`；不要让本 skill 充当入口路由。

# Code Quality Drift Guard

## 目的

在正式 lint/test 之外，给长时间代码编辑增加轻量漂移护栏。第一版只做候选报警，不把启发式结论说成确定 bug。

## 适用场景

- 用户担心无人值守写代码时出现死代码、重复造轮子、命名漂移或文件膨胀。
- 项目还没有完整语言级静态分析工具。
- 需要先用 repo-local 检查补最小机械拦截。

## 检查优先级

1. 孤儿脚本：有 `check-*.mjs` 没有 wrapper、README 注册或 current-phase 注册。
2. 孤儿 wrapper：有 wrapper 但没有对应脚本。
3. 文件大小：超过项目阈值的源码、检查脚本、agent 规则或 Markdown。
4. 命名漂移：同一目录下文件命名风格混杂，或 check/wrapper 命名不配对。
5. 重复实现候选：相同导出名、相同函数名、相似 check 前缀或重复 helper 名称。
6. 未引用文件候选：源码文件没有入口、测试、检查或文档引用。

## 落地原则

- 优先使用现有工具，例如 ESLint、dependency-cruiser、ts-prune、ArchUnit、NetArchTest、ruff、go vet。
- 没有成熟工具时，先写项目内轻量 `check-code-quality-drift`。
- 对启发式项使用 `candidate` / `warning` 命名；只有确定规则才 fail。
- 每条 fail 信息必须指出文件、规则和修复方向。
- 接入标准 verification，但不要一次性阻塞大量历史遗留，必要时先登记 baseline。

## 禁止

- 不要用一次性全文相似度替代可解释规则。
- 不要把候选死代码直接删除。
- 不要在未固定 target-local 命名规则前强行检查业务命名。
