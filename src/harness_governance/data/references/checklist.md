# Implementation Readiness Checklist / 实现就绪清单

Before writing product implementation code, apply this checklist to any implementation target.

在写产品实现代码前，对任何 implementation target 使用这份清单。

## Required Outcomes / 必需结果

A target is ready only when every item has stable evidence and a verification command.

只有每一项都有稳定证据和 verification command 时，目标才算 ready。

## Checklist / 清单

- Target path identified.
- 已识别 target path。
- Target owner/responsibility recorded.
- 已记录 target owner/responsibility。
- Architecture boundary recorded.
- 已记录 architecture boundary。
- Forbidden paths recorded.
- 已记录 forbidden paths。
- ADR or decision state recorded.
- 已记录 ADR 或 decision state。
- Intended behavior has contract evidence.
- intended behavior 已有 contract evidence。
- Lint command exists and is runnable.
- lint command 存在且可运行。
- Formatter command exists, or formatting is covered by lint.
- formatter command 存在，或 formatting 已由 lint 覆盖。
- Unit test framework exists.
- unit test framework 存在。
- Unit test command exists and is runnable.
- unit test command 存在且可运行。
- Boundary behavior has integration, contract, fixture, or harness check.
- boundary behavior 已有 integration、contract、fixture 或 harness check。
- Target verification command recorded.
- target verification command 已记录。
- Where appropriate, target verification command registered to standard project checks.
- 适合时，target verification command 已注册到标准项目检查。
- Local `AGENTS.md` or equivalent target-local rules exist.
- 本地 `AGENTS.md` 或等价 target-local rules 存在。
- Commit/review behavior is clear.
- commit/review behavior 已清楚。

## Stop Conditions / 停止条件

The following conditions require stopping before implementation:

以下情况必须在 implementation 前停止：

- Target only has repository-level lint/test rules.
- target 只有仓库级 lint/test rules。
- Target has no local rules.
- target 没有 local rules。
- Target has unit tests but no boundary/contract test.
- target 有 unit tests，但没有 boundary/contract test。
- Target has contracts but no test/lint baseline.
- target 有 contracts，但没有 test/lint baseline。
- Target would introduce HTTP, storage, auth, worker executable, or UI workflow code before explicit permission.
- target 会在明确允许前引入 HTTP、storage、auth、worker executable 或 UI workflow code。

## Minimum Output / 最小输出

Report:

汇报：

- Target.
- Target。
- Pass/fail.
- Pass/fail。
- Missing items.
- Missing items。
- Next readiness artifact or implementation slice.
- 下一步 readiness artifact 或 implementation slice。
- Verification commands that were run.
- 已运行的 verification commands。
