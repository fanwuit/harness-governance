---
name: doc-comment-policy
description: Use when writing, reviewing, migrating, or auditing code documentation comments for classes, interfaces, methods, functions, parameters, return values, generated API docs, SDK docs, docfx/Javadoc/TypeDoc/JSDoc output, or when a project asks for custom templates such as "功能/入参/出参" that may break language-native doc generation.
---

## Harness Precondition

应用本 skill 前，先确认 `harness-engineering` 已经完成当前 layer 和本地治理义务判断。若尚未完成，停止本 skill，返回 `harness-engineering`；不要让本 skill 充当入口路由。

# Doc Comment Policy

## 目的

把代码注释写成语言和文档生成工具能识别的标准 doc comment。允许中文说明，但结构必须使用语言原生标签，避免用自定义标题破坏生成文档。

## 判断范围

优先给这些目标写标准文档注释：

- 会进入 API、SDK、OpenAPI、docfx、Javadoc、TypeDoc、JSDoc、文档站或用户可见 reference 的类、接口、公开方法和公开函数。
- 跨模块、跨服务、跨包调用边界。
- 入参、返回值、错误、空值、幂等性、权限、可见性或副作用不明显的关键边界。
- 用户明确要求补代码注释、修复 generated docs、整理 API 文档或迁移旧注释模板。

不要强制这些位置模板化：

- 私有小 helper。
- trivial getter/setter。
- 仅复写父类且没有新增语义的 override。
- 测试局部 helper。
- 名称已经足够清楚、没有边界语义的小函数。

## 语言格式

- C#：使用 XML doc comment，包含需要的 `<summary>`、`<param name="...">`、`<returns>`、`<exception>`。
- Java：使用 JavaDoc，包含需要的 `@param`、`@return`、`@throws`。
- JavaScript/TypeScript：使用 JSDoc/TypeDoc，包含需要的 `@param`、`@returns`、`@throws`、类型或泛型说明。
- Python：使用项目既有 docstring 风格，例如 Google、NumPy 或 reStructuredText；不要混用多套风格。
- Go/Rust：遵循语言生态的导出符号注释规则，例如 Go doc comment、Rust doc comment。

中文内容可以写在标准标签内部。例如 C# 里写中文 `<summary>` 内容，而不是另起“功能：”“入参：”“出参：”标题替代标准标签。

## 工作流

1. 先识别项目现有文档生成工具、语言和本地注释规则。
2. 如果项目规则要求“功能/入参/出参”这类自定义标题，优先把规则转换为语言原生 doc comment，而不是逐字照搬模板。
3. 只给应进入文档生成或边界语义不明显的目标补注释，避免全量噪音。
4. 注释说明行为、约束、参数语义、返回语义和失败语义；不要复述代码表面动作。
5. 保留必要英文术语，中文解释优先放在标准标签内。
6. 修改项目级规则时，建议同时新增或更新 repo-local check、lint、文档索引或 CI 入口，防止规则回退。

## 防忘落地

通用 skill 只提供规则和审计步骤，不能代替仓库门禁。需要长期生效时，在目标仓库落地至少一种机制：

- 在 `AGENTS.md`、`CONTRIBUTING.md` 或就近规则中写明标准 doc comment 要求。
- 新增轻量检查，确认规则、索引、验证入口和 wrapper 未漏登记。
- 接入现有 lint/doc 生成检查，例如 Checkstyle、StyleCop、ESLint JSDoc、TypeDoc、Javadoc、docfx。
- 对历史遗留先登记 baseline，不要一次性阻塞大量旧代码。

## 禁止

- 不要把“每个方法和类都必须写注释”作为默认全局规则。
- 不要用“功能/入参/出参”自定义标题替代语言标准标签。
- 不要为了满足模板写无信息量注释。
- 不要在没有项目门禁的情况下声称已经防止以后忘记。
