---
name: implementation-detail-timing
description: Use before fixing implementation details such as class names, file names, package/module names, function names, DTO/schema fields, database tables, migrations, entities, member variables, or layer dependency enforcement. Use when moving from Architecture, Contract, or Readiness into Implementation, auditing existing code that may have fixed details too early, or selecting architecture/layer validation tools such as ArchUnit, ESLint boundaries, dependency-cruiser, NetArchTest, Semgrep, or CodeQL.
---

## Harness Precondition

应用本 skill 前，先确认 `harness-engineering` 已经完成当前 layer 和本地治理义务判断。若尚未完成，停止本 skill，返回 `harness-engineering`；不要让本 skill 充当入口路由。

# Implementation Detail Timing

## 目的

判断哪些实现细节可以在当前 harness 层级固定，哪些必须推迟到 ADR、Contract、readiness gate 或 implementation slice。

本 skill 还要求：项目内代码层级依赖必须用工具或机械检查约束，不能只靠 agent 记忆或文字提醒。

配合使用：

- `harness-engineering`：判断当前工程层级。
- `architecture-boundary-design`：定组件职责、数据流和运行时边界。
- `contract-first-development`：定 public contract（公共契约）。
- `implementation-readiness-gate`：进入目标子系统实现前做 target-local 准入。

## 命名时机

原则：越会影响外部消费者、长期迁移或跨组件协作的名字，越早固定；越偏内部实现的名字，越晚固定。

| 细节 | 固定时机 | 稳定产物 |
|---|---|---|
| 组件 / target 归属 | Architecture | 架构 brief、边界文档、ADR 候选 |
| 跨组件数据流 / 控制流 | Architecture / ADR | 架构文档或 ADR |
| runtime、部署、持久化、存储、权限、所有权等长期选择 | ADR 先于 Contract | ADR 或 decision note |
| API、DTO、schema、event、CLI 参数、artifact 文件名、诊断码 | Contract | schema、example、fixture、check |
| 数据库表、migration、持久化实体、索引、关系 | 先有 persistence/data ownership gate，再进入 ADR + Contract | ADR、migration contract、schema/example/check |
| target-local 包目录、模块分层、允许/禁止依赖 | Implementation readiness gate | 局部 `AGENTS.md`、readiness 文档、lint/test/check |
| 类名、源码文件名、target 内 public method | Implementation slice 开始前 | 实现计划、测试、代码 |
| private helper、成员变量、局部数据结构 | Implementation slice 内 | 聚焦测试和代码审查 |

## 层级依赖约束

项目内层级依赖不是“风格建议”，而是 implementation readiness evidence（实现准入证据）。

不要在 skill 里写死一种通用分层模型。先识别 target 技术栈，再选择原生或成熟工具，把规则接入本地验证和 CI。

常见工具：

| Target | 优先工具 |
|---|---|
| Java / JVM | ArchUnit、Spring Modulith checks、Checkstyle/PMD 自定义规则、Semgrep、package-level tests |
| .NET | NetArchTest、ArchUnitNET、NDepend、Roslyn analyzers、Semgrep |
| TypeScript / JavaScript | ESLint `no-restricted-imports`、eslint-plugin-boundaries、eslint-plugin-import、dependency-cruiser、自定义 ESLint rule |
| Python | import-linter、pytest architecture tests、Semgrep |
| Go | 自定义 `go test` analyzer、staticcheck/custom analyzer、依赖检查 |
| 跨语言 / 生成代码边界 | Semgrep、CodeQL、仓库自定义 check script |

简单仓库可以用 repo-specific check script（仓库自定义检查脚本），但必须确定性解析 import/package/path，并输出可定位的失败信息。

成熟技术栈优先使用生态工具，让规则能在本地命令和 CI/CD 中重复执行。

## 规则落地

进入某个 target 的 implementation 前，稳定位置必须记录：

- 选用的层级依赖工具。
- 规则文件位置。
- 本地验证命令。
- CI/CD 接入位置，或为什么当前只做本地检查。
- 禁止依赖示例和失败语义。

示例规则只用于说明，不代表所有项目都应使用同一分层：

```text
Controller -> Service -> Repository/Mapper
Controller 不得直接调用 Mapper。
Service 不得依赖 Web/UI 类。
Repository/Mapper 不得反向依赖 Controller 或 Service。
```

真正完成标准不是写下这几句话，而是 ArchUnit、ESLint、dependency-cruiser、NetArchTest、Semgrep、CodeQL 或自定义 check 能拦住违反规则的代码。

## 已有代码审计

本 skill 后引入时，不自动回滚已有代码。先分类：

- `authorized implementation`：已有 readiness、contract、测试和验证支撑。保留。
- `harness-only or skeleton`：有用但不是产品 runtime。保留，并标清边界。
- `over-gate code`：产品行为、持久化、runtime execution 或 public dependency 缺少 gate 证据。降级为 fixture/harness-only、记录 blocked，或请求人工确认。

## 决策检查

固定名字或依赖前先回答：

1. 这个名字或依赖是否对当前 target 外部可见？
2. 修改它是否会破坏 API、migration、artifact、schema 或外部消费者？
3. 它是否涉及持久化、权限、安全或长期所有权？
4. target-local 层级依赖规则是否已文档化？
5. 是否已有工具、lint、架构测试或 check 能拦住违反规则？

如果 1-3 任一为是，不要在实现中临时发明；先进入 ADR、Contract 或 readiness。

如果 4-5 为否，且该错误容易重复发生，先补 target-local 规则和机械检查，再继续产品代码。

## 输出

汇报时说明：

- 当前 harness 层级。
- 当前可以固定哪些实现细节。
- 必须推迟哪些实现细节。
- target 的层级依赖规则。
- 选用的工具或检查命令。
- 已有代码分类结果。
- 继续实现前还缺什么稳定产物或机械检查。
