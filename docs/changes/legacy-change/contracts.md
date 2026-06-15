# Contracts: legacy-change

## Current behavior

说明当前可观察行为、已有 schema / fixture / probe / check，或明确当前缺口。

## Proposed behavior / contract delta

说明本变更对行为契约的增量。这里吸收 spec delta 思路，但落到本项目 Contract 层，不引入 OpenSpec 目录或命令。

## Contract artifacts

- Artifact:
- Path:
- Type: schema | example | fixture | probe | check script | acceptance test | documentation invariant

如果当前无法给出 contract artifact，必须写明：

- Blocked reason:
- Missing evidence:
- Next contract task:

## Acceptance checks

- 

## Failure cases

- 

## Contract-first reminder

文档说明不能替代可执行 schema、fixture、probe、check 或 acceptance test。只有行为确实无法机械验证时，才把 documentation invariant 作为最小契约，并说明原因。

