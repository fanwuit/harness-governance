## Skill 入口优先级

每次开始处理用户请求时，先选择并读取：

- `skill-use-transparency`
- `harness-engineering`

对新项目、开发、规划、实现、调试、验证、review、继续、下一步、队列、handoff、skill 更新等请求：

- `harness-engineering` 拥有最高入口路由权。
- 在 `harness-engineering` 完成当前 layer 判断前，不得执行任何 `superpowers:*` 或其他 companion workflow。
- `superpowers:*` 只能作为 companion workflow，必须等 harness 选定本地治理 layer 后再决定是否使用。
- 如果 companion skill 的描述包含 MUST、before any creative work、TDD、verification 等强触发词，也不能越过 harness 入口路由。
- 路由说明必须区分：
  - Local governance skills
  - Companion workflow skills
  - Routing decision

Routing decision 模板：

```text
Local governance skills: skill-use-transparency, harness-engineering, <other local governance skills>
Companion workflow skills: <optional companion skills, or none>
Loaded SKILL.md files: <success/failure list>
Routing decision: harness-engineering owns entry routing; companion workflows run only after harness selects the current layer.
```

## Skill 使用透明度

当 agent 判断是否使用 skill 时，必须显式说明选择结果。

在应用任何 skill 之前，先说明：
- 选择了哪个 skill
- 为什么它适用于当前请求
- 这是用户明确要求的，还是 agent 根据任务推断的

尝试加载 skill 文件之后，说明对应的 `SKILL.md` 是否读取成功。

如果读取 `SKILL.md` 失败：
- 简短说明失败原因
- 使用最佳 fallback 继续
- 不要声称已经完整执行该 skill 的工作流

如果用户询问某个 skill 是否被触发，必须直接回答：
- 是否选择了该 skill
- 触发原因是什么
- 是否读取了 `SKILL.md`
- 是完整执行了该 workflow，还是只是近似处理

不要静默应用 skill。skill 使用必须在对话中可见。

读中文 skill / docs 时优先加 -Encoding UTF8

中文友好：
- 自定义skill，除保留必要英文外，必须中文友好

## Skill 文档同步

当新增、删除、启用、禁用、重命名或修改任何非 `.system` skill 时，必须同步更新根目录 `README.md`。

同步范围至少包括：
- skill 数量和启用/禁用状态
- skill 功能分类和说明
- 新增或删除的脚本、模板、assets、references 等重要资产
- 当前覆盖重点与缺口（如有变化）

如果本轮只修改 `.system` skill，应说明 `README.md` 是否不需要同步以及理由。
