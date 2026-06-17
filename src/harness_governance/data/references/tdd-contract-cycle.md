# TDD Contract Cycle / TDD 契约循环

Used to apply red / green / refactor discipline to this project's Contract -> Implementation -> Verification chain.

用于把 red / green / refactor 纪律落到本项目的 Contract -> Implementation -> Verification 链路。

## Local Owner / 本地所有者

- Owner skill: `contract-first-development`
  所有者技能：`contract-first-development`
- Supporting skills: `agent-role-isolation`, `governed-implementation-entry`, `implementation-readiness-gate`, `review-next-governance`
  支撑技能：`agent-role-isolation`、`governed-implementation-entry`、`implementation-readiness-gate`、`review-next-governance`
- Stable evidence: schema, example, fixture, probe, check, acceptance test, verification command
  稳定证据：schema、example、fixture、probe、check、acceptance test、verification command

## Mapping / 映射

| TDD step | Harness meaning | Required evidence |
|---|---|---|
| Red | Pin a contract or test that will fail first, proving current behavior does not satisfy the target. 先固定会失败的契约或测试，证明当前行为未满足目标。 | failing schema/check/test output, or explicit blocked reason. failing schema/check/test output，或明确的 blocked reason |
| Green | Enter the minimal implementation slice, writing only enough code to make the contract pass. 进入最小 implementation slice，只写足够让契约通过的代码。 | Implementation Entry Record, minimal diff, passing targeted check. Implementation Entry Record、最小 diff、passing targeted check |
| Refactor | Perform local cleanup after verification passes, without expanding behavioral scope. 在验证通过后做局部整理，不扩大行为范围。 | rerun verification, state no contract delta. rerun verification，说明没有 contract delta |

## Red / 红

Write or update the minimal contract artifact first:

先写或更新最小 contract artifact：

- schema / type / OpenAPI / protobuf
- example / fixture
- probe / check script
- acceptance test
- documentation invariant + reason it cannot be mechanically verified
  documentation invariant + 不能机械验证的理由

Red stage output:

Red 阶段输出：

```markdown
## Red Evidence
- Contract artifact:
- Expected failure:
- Command:
- Observed result:
- Failure path covered:
```

If a failing output cannot be obtained first, the reason must be stated — for example, a brand-new file format, an unavailable external system, or a documentation invariant that can only be written first.

如果不能先得到失败输出，必须说明原因，例如全新文件格式、外部系统不可用、或只能先写 documentation invariant。

## Green / 绿

Green only allows implementing the minimal slice needed to make the Red evidence pass:

Green 只允许实现让 Red 证据通过所需的最小切片：

```markdown
## Green Boundary
- Owner files:
- Allowed changes:
- Forbidden changes:
- Contract evidence:
- Verification command:
```

Before entering product implementation, this project's implementation entry rules must still be satisfied; test existence does not equal readiness pass.

进入产品实现前仍必须满足本项目实现入口规则；测试存在不等于 readiness 通过。

## Refactor / 重构

Refactor only allows:

Refactor 只允许：

- Removing duplication or obvious local noise.
  删除重复或明显局部噪声。
- Keeping public contract, fixture, schema, CLI, API, and failure behavior unchanged.
  保持 public contract、fixture、schema、CLI、API 和失败行为不变。
- Re-running the same or more complete verification as Red/Green.
  重新运行与 Red/Green 相同或更完整的 verification。

Refactor prohibits:

Refactor 禁止：

- Casually extending functionality.
  顺手扩展功能。
- Changing contract without updating contract delta.
  改 contract 但不更新 contract delta。
- Loosening tests to fit the implementation.
  把测试放宽成适配实现。

## Completion Evidence / 完成证据

Record upon completion:

完成时记录：

```markdown
## TDD Contract Cycle
- Red:
- Green:
- Refactor:
- Commands run:
- Result:
- Residual risk:
```
