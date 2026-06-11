---
name: observable-fact-discovery
description: Use when a concrete unknown about existing behavior, external capability, third-party integration, logs, fixtures, probes, runtime evidence, or real samples must be investigated and recorded as reviewable facts before it can guide later layers.
---

## Harness Precondition

应用本 skill 前，先确认 `harness-engineering` 已经完成当前 layer 和本地治理义务判断。若尚未完成，停止本 skill，返回 `harness-engineering`；不要让本 skill 充当入口路由。

# Observable Fact Discovery

## 概览

把未知行为先变成可复查的事实记录，再进入 Brief、Architecture、ADR、Contract 或 Implementation。这个 skill 适用于 harness engineering 中的事实发现层，尤其是外部项目能力、既有系统行为、日志、fixture、probe 和第三方集成边界。

核心原则：事实、假设和推断必须分开写；没有出处的结论不能当作事实使用。

## 何时使用

- 需要理解既有代码、外部项目、第三方能力或运行时行为。
- 当前任务依赖日志、fixture、probe、schema、导出文件或真实样本。
- 用户问“这到底怎么工作”“先查一下”“先验证行为”“别凭感觉”。
- 进入架构、ADR、契约或实现前，关键行为仍有未知项。
- PoC 跑通过，但结论还没有被文档、示例、schema 或检查固定。

不要用于纯粹的创意发散；那应进入 Brainstorming。不要用于已经有稳定契约和机械检查覆盖的普通实现任务。

## 工作流程

1. 定义问题：用一句话写清要确认的行为或边界。
2. 列出已知和未知：把聊天里的说法、文档里的约束、代码中的线索分开。
3. 找证据源：优先读取本地文档、代码、测试、schema、fixture、日志和最小 probe 输出。
4. 最小化验证：只运行能回答问题的最小命令或 probe，避免扩大到产品实现。
5. 记录事实：每条事实必须带来源，例如文件路径、命令输出、日志片段或样本名。
6. 区分假设和推断：假设是未验证前提；推断是基于事实的解释，不能写成事实。
7. 标注置信度：高表示有机械证据或多源交叉验证；中表示有单一直接证据；低表示只有间接线索。
8. 决定下一层：事实足够后，明确进入 Brief、Architecture、ADR、Contract、Implementation 或 Review / Next。

## Debugging Fact Workflow

遇到 bug、测试失败或运行时异常，且需要主动排障时，读取 `references/debugging-fact-workflow.md`。该 workflow 把排障拆成：

- Reproduce：记录稳定复现或无法复现的证据。
- Observe：记录错误、日志、输入输出和环境。
- Isolate：缩小最小失败边界并找工作对照样例。
- Hypothesis：一次只验证一个假设。
- Fix / Verify：修复后回到 verification 和 Review / Next。

不要先猜修；如果事实不足，停在 Fact Discovery 或标记 blocked。

## Fact Record 模板

```markdown
# Fact Record: <主题>

## Question
<要确认的问题>

## Evidence Sources
- <路径、命令、日志、fixture、probe 或外部来源>

## Observed Facts
- [High|Medium|Low] <事实> — Source: <出处>

## Assumptions
- <仍未验证但当前需要暂用的前提>

## Inferences
- <基于事实得到的解释，说明依据>

## Reproduction / Probe
- Command: `<命令>`
- Result: <关键结果>

## Unknowns
- <还缺什么证据>

## Next Layer
<Brief | Architecture | ADR | Contract | Implementation | Review / Next，并说明原因>
```

## 禁止捷径

- 不要把推断写成事实。
- 不要只靠记忆、命名或注释判断运行时行为。
- 不要修改外部项目或第三方系统来获得证据，除非用户明确要求。
- 不要把一次成功路径当作完整行为覆盖。
- 不要把证据只留在聊天里；需要沉淀时应写入文档、fixture、schema、检查或队列。
- 不要在事实不足时直接进入产品功能编码。

## 输出格式

- 如果用户只是要求探索：输出事实、假设、推断、未知项和建议下一层。
- 如果用户要求沉淀：写入一个 Fact Record 或更新项目已有事实文档。
- 如果证据不足：明确说明缺哪类证据，并给出最小可验证动作。
