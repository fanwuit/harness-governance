---
name: agent-mistake-guard
description: Use when creating, updating, or applying a concise project guardrail that prevents AI agents from repeating known mistakes; 当用户要求维护 AI 不重复犯错文档、anti-repeat rules、经验教训、prompt/context 膨胀控制，或把重复 agent 错误沉淀为项目规则/检查脚本时使用。
---

## Harness Precondition

应用本 skill 前，先确认 `harness-engineering` 已经完成当前 layer 和本地治理义务判断。若尚未完成，停止本 skill，返回 `harness-engineering`；不要让本 skill 充当入口路由。

# Agent Mistake Guard

使用本 skill，把重复出现的 agent 错误从聊天记忆迁移到项目内稳定、短小、可复用的护栏文档中。

## 核心规则

不要创建长篇失败日志。创建按触发条件组织的短规则，让后续 agent 能快速扫描，并且只读取命中的条目。

## 工作流

1. 找到项目规则入口。
   - 检查 `AGENTS.md`、`.cursorrules`、`CLAUDE.md`、`docs/`、`agents/`、`CONTRIBUTING.md` 或已有 mistakes / pitfalls 文档。
   - 优先沿用项目现有约定。没有约定时，使用 `agents/known-agent-mistakes.md` 记录 agent 行为错误。

2. 区分 agent 错误和技术 API 坑。
   - agent 错误放在 `known-agent-mistakes` 类文档：漏读规则、误报完成、上下文滥用、范围膨胀、不安全编辑、缺少验证等。
   - 技术 API 坑放到子系统文档，例如 `docs/api-pitfalls/frontend/`、`docs/api-pitfalls/backend/`、`docs/api-pitfalls/worker/`，或项目已有等价目录。

3. 每条规则保持短小。
   - 使用这个结构：

```markdown
## 简短错误标题

Trigger:
- 什么时候需要检查这条规则。

Mistake:
- 已经重复出现或高度可能重复出现的错误行为。

Correct behavior:
- 正确做法。

Guardrail:
- 防止复发的检查、命令、review 步骤或文件入口。
```

4. 控制上下文大小。
   - 在项目导航里只放文档链接，不复制全文。
   - 在全局规则里要求 agent 只读取命中的 Trigger 条目。
   - 不要把完整 mistakes 文档塞进每次 prompt。
   - 某条规则变成子系统细节后，移动到就近 `AGENTS.md` 或对应 `api-pitfalls` 专题。

5. 把高频规则升级成机械检查。
   - 如果某个错误客观可检测，并且已经重复出现，优先新增或更新项目现有检查脚本。
   - 文档保留人工可读的原因和入口，检查脚本负责稳定执行。

6. 更新索引和队列。
   - 项目有 doc map 时，登记新增或更新的文档。
   - 项目有 NEXT / backlog / queue 时，记录该护栏是 done、active、blocked 还是 not-now。
   - 如果未来需要前端/后端 API pitfalls，但当前不是范围，先记录为后期事项，不要一次性扩成完整知识库。

7. 验证。
   - 运行项目匹配的文档地图、结构、lint、队列或治理检查。
   - 如果项目没有对应检查，说明验证仅限文件审阅。

## 条目选择

优先记录已经发生过，或当前项目高度可能发生的错误：

- 静默使用 skill / tool，没有说明为什么触发。
- 文件读取失败、乱码或缺字后，仍声称完整执行 workflow。
- 让 companion skill（例如 `superpowers:*`）的完整 workflow 取代 harness layer map、local governance skill、readiness gate 或 review/next。
- 用户说“继续/下一步”时，没有先读项目队列。
- 把 probe / PoC 跑通误报为 product-ready。
- 参考外部项目代码前，没有记录事实、假设、推断和所有权边界。
- 借一个小实现切片扩大到 auth、storage、database、production infrastructure 等当前范围外工作。
- 重要结论只留在聊天里，没有落到文档、fixture、schema、检查脚本或队列。
- 没有新鲜验证证据就声明完成。

## 输出要求

收口时说明：

- 创建或更新了哪个护栏文档。
- 如何控制上下文膨胀。
- 技术 API pitfalls 是本轮处理还是延后处理。
- 更新了哪些索引、项目规则、队列或检查脚本。
- 运行了哪些验证命令，结果如何。
