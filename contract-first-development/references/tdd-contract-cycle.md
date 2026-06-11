# TDD Contract Cycle

用于把 red / green / refactor 纪律落到本项目的 Contract -> Implementation -> Verification 链路。

## Local Owner

- Owner skill: `contract-first-development`
- Supporting skills: `agent-role-isolation`, `governed-implementation-entry`, `implementation-readiness-gate`, `review-next-governance`
- Stable evidence: schema、example、fixture、probe、check、acceptance test、verification command

## Mapping

| TDD step | Harness meaning | Required evidence |
|---|---|---|
| Red | 先固定会失败的契约或测试，证明当前行为未满足目标。 | failing schema/check/test output，或明确的 blocked reason |
| Green | 进入最小 implementation slice，只写足够让契约通过的代码。 | Implementation Entry Record、最小 diff、passing targeted check |
| Refactor | 在验证通过后做局部整理，不扩大行为范围。 | rerun verification，说明没有 contract delta |

## Red

先写或更新最小 contract artifact：

- schema / type / OpenAPI / protobuf
- example / fixture
- probe / check script
- acceptance test
- documentation invariant + 不能机械验证的理由

Red 阶段输出：

```markdown
## Red Evidence
- Contract artifact:
- Expected failure:
- Command:
- Observed result:
- Failure path covered:
```

如果不能先得到失败输出，必须说明原因，例如全新文件格式、外部系统不可用、或只能先写 documentation invariant。

## Green

Green 只允许实现让 Red 证据通过所需的最小切片：

```markdown
## Green Boundary
- Owner files:
- Allowed changes:
- Forbidden changes:
- Contract evidence:
- Verification command:
```

进入产品实现前仍必须满足本项目实现入口规则；测试存在不等于 readiness 通过。

## Refactor

Refactor 只允许：

- 删除重复或明显局部噪声。
- 保持 public contract、fixture、schema、CLI、API 和失败行为不变。
- 重新运行与 Red/Green 相同或更完整的 verification。

Refactor 禁止：

- 顺手扩展功能。
- 改 contract 但不更新 contract delta。
- 把测试放宽成适配实现。

## Completion Evidence

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

