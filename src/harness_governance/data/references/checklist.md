# Implementation Readiness Checklist

在写产品实现代码前，对任何 implementation target 使用这份清单。

## 必需结果

只有每一项都有稳定证据和 verification command 时，目标才算 ready。

## 清单

- 已识别 target path。
- 已记录 target owner/responsibility。
- 已记录 architecture boundary。
- 已记录 forbidden paths。
- 已记录 ADR 或 decision state。
- intended behavior 已有 contract evidence。
- lint command 存在且可运行。
- formatter command 存在，或 formatting 已由 lint 覆盖。
- unit test framework 存在。
- unit test command 存在且可运行。
- boundary behavior 已有 integration、contract、fixture 或 harness check。
- target verification command 已记录。
- 适合时，target verification command 已注册到标准项目检查。
- 本地 `AGENTS.md` 或等价 target-local rules 存在。
- commit/review behavior 已清楚。

## 停止条件

以下情况必须在 implementation 前停止：

- target 只有仓库级 lint/test rules。
- target 没有 local rules。
- target 有 unit tests，但没有 boundary/contract test。
- target 有 contracts，但没有 test/lint baseline。
- target 会在明确允许前引入 HTTP、storage、auth、worker executable 或 UI workflow code。

## 最小输出

汇报：

- Target。
- Pass/fail。
- Missing items。
- 下一步 readiness artifact 或 implementation slice。
- 已运行的 verification commands。
